# Research: 个股多Agent深度分析

**Feature Branch**: `003-stock-analysis`
**Date**: 2026-04-22

---

## 1. 现有 AIService 扩展性评估

### 决策：扩展 AIService 支持多模型参数，而非引入 langchain_openai

**现状**：
- `AIService` 基于 httpx 直接调用 OpenAI 兼容 API，支持流式输出
- 单模型绑定 (`self.model = settings.llm_model`)，无 model/temperature/max_tokens 参数覆盖
- `StreamChunk` 只有 `type`（content/reasoning）和 `text`，无 agent 维度

**方案**：
- 为 `stream_chat` 和 `tool_call` 增加 `model`、`temperature`、`max_tokens` 可选参数
- 在 `StreamChunk` 中增加 `agent_id` 可选字段
- 新增 `stream_chat_with_tools` 方法，支持 function calling + 流式输出

**替代方案（已否决）**：
- 直接引入 `langchain_openai.ChatOpenAI` — 违反 constitution "MUST NOT 在业务层散落直连 SDK"
- 在 Workflow 中直接使用 `llm.invoke()` — 违反 `rules/langgraph.md` "Node → AIService → LLM"

---

## 2. LangGraph 工作流设计

### 决策：构建独立的 StockAnalysisGraph，与现有 AnalysisGraph 并存

**理由**：
- 现有 `AnalysisGraph` 是事件分析的预处理流程（classify → search → load → retrieve），不做实际推理
- 多Agent分析需要全新的图结构：分析师序列 → 辩论 → 风险辩论 → 信号提取
- 两者职责不同，不应混合。后续可通过 Application 层选择调用哪个 Graph

**State 设计（遵循 rules/langgraph.md 三层结构）**：

```python
class StockAnalysisInput(TypedDict):
    stock_code: str          # 股票代码
    stock_name: str          # 股票名称
    analysis_mode: str       # "quick" / "full"

class StockAnalysisWorking(TypedDict):
    # 分析师阶段
    market_report: str
    fundamentals_report: str
    news_report: str
    sentiment_report: str
    # 各分析师工具调用计数（防死循环）
    market_tool_call_count: int
    fundamentals_tool_call_count: int
    news_tool_call_count: int
    sentiment_tool_call_count: int
    # 辩论阶段
    investment_debate_state: dict
    investment_plan: str
    trader_investment_plan: str
    # 风险辩论阶段
    risk_debate_state: dict
    # 进度追踪
    current_agent: str
    current_phase: str       # "analysts" / "debate" / "risk" / "done"

class StockAnalysisOutput(TypedDict):
    title: str
    summary: str
    industries: list[str]
    final_decision: str      # Risk Judge 最终决策文本
    action: str              # 买入/持有/卖出
    target_price: float
    confidence: float
    risk_score: float
    reasoning: str
    error: Optional[str]
```

**图结构**：

```
START → Market Analyst → [条件边] → tools_market → Market Analyst (循环)
     → Msg Clear Market
     → Fundamentals Analyst → [条件边] → tools_fundamentals → ... → Msg Clear Fundamentals
     → News Analyst → [条件边] → tools_news → ... → Msg Clear News
     → Sentiment Analyst → [条件边] → tools_sentiment → ... → Msg Clear Sentiment
     → Bull Researcher ⇄ Bear Researcher (辩论循环)
     → Research Manager
     → Trader
     → Risky Analyst ⇄ Safe Analyst ⇄ Neutral Analyst (风险辩论循环)
     → Risk Judge
     → Signal Extractor
     → END

快速模式（quick）：
START → Market Analyst → ... → Fundamentals Analyst → ... → Quick Decision → END
```

**替代方案（已否决）**：
- 将多Agent节点加入现有 AnalysisGraph — 职责混合，违反单一职责
- 使用 LangGraph 子图封装每个 Agent — 过度设计，当前阶段不需要

---

## 3. Agent Prompt 管理方式

### 决策：所有 Prompt 集中到 `infrastructure/workflow/prompts/` 目录

**理由**：
- `rules/langgraph.md` 明确规定"不允许 Node 内拼 Prompt"
- `rules/backend.md` 要求"Prompt 模板化管理，禁止硬编码"
- TradingAgents-CN 的 Agent 在 Node 内直接拼接 Prompt，违反目标项目规则

**目录结构**：
```
app/infrastructure/workflow/prompts/
 ├── stock_analysis/              # 新增：个股分析 Prompt
 │   ├── market_analyst.py        # 技术面分析师 system prompt + user template
 │   ├── fundamentals_analyst.py  # 基本面分析师
 │   ├── news_analyst.py          # 新闻分析师
 │   ├── sentiment_analyst.py     # 情绪分析师
 │   ├── bull_researcher.py       # 看多研究员
 │   ├── bear_researcher.py       # 看空研究员
 │   ├── research_manager.py      # 研究管理器
 │   ├── trader.py                # 交易员
 │   ├── risky_debator.py         # 激进风险分析师
 │   ├── safe_debator.py          # 保守风险分析师
 │   ├── neutral_debator.py       # 中立风险分析师
 │   ├── risk_judge.py            # 风险裁决
 │   └── signal_extractor.py      # 信号提取
```

---

## 4. 金融数据工具适配

### 决策：构建 StockDataToolkit，基于 AKShare + DataSourceManager 故障转移

**数据获取策略**：
- 主数据源：AKShare（与现有项目一致）
- 故障转移：AKShare → BaoStock → 错误提示
- 缓存层：Redis 缓存行情数据（5分钟TTL）

**工具定义（使用 @tool 装饰器）**：
```python
class StockDataToolkit:
    @staticmethod
    @tool
    def get_stock_market_data(stock_code: str, trade_date: str) -> str:
        """获取A股技术面数据：K线、均线、成交量、MACD、KDJ"""

    @staticmethod
    @tool
    def get_stock_fundamentals(stock_code: str) -> str:
        """获取A股基本面数据：PE、PB、营收、净利润、ROE"""

    @staticmethod
    @tool
    def get_stock_news(stock_code: str) -> str:
        """获取A股相关新闻资讯"""

    @staticmethod
    @tool
    def get_stock_sentiment(stock_code: str) -> str:
        """获取A股投资者情绪数据：融资融券、北向资金、龙虎榜"""
```

**适配注意**：
- TradingAgents-CN 的 `DataSourceManager` 使用 MongoDB 存储配置和缓存，需改为 MySQL + Redis
- `StockUtils.get_market_info()` 的股票类型识别逻辑可直接复用
- `interface.py` 中 AKShare 的具体调用代码可参考，但需要剥离 `langchain-community` 依赖

---

## 5. 信号提取（SignalProcessor）适配

### 决策：适配 TradingAgents-CN 的 SignalProcessor，替换 LLM 调用为 AIService

**保留的逻辑**：
- JSON 提取正则 + action 容错映射
- 14种中文价格模式正则
- `_smart_price_estimation()` 智能推算
- 多层降级链：JSON → 正则 → 智能推算 → 默认持有

**替换的部分**：
- `ChatOpenAI` 直接调用 → `AIService.tool_call()`
- `StockUtils` 依赖 → 通过 State 传入市场信息
- `interface` 层数据获取 → 通过 AIService 统一调用

---

## 6. SSE 流式输出设计

### 决策：扩展现有 SSE 事件体系，增加 Agent 维度

**新增事件类型**：

| 事件 type | data 内容 | 说明 |
|-----------|----------|------|
| `agent_status` | `{agent, phase, status}` | Agent 开始/完成状态 |
| `agent_report` | `{agent, content}` | Agent 分析结果摘要 |
| `debate` | `{speaker, round, content}` | 辩论过程 |
| `decision` | `{action, target_price, confidence, risk_score}` | 结构化决策 |

**保留的事件**：`content`、`reasoning`、`error`、`title`、`summary`、`industries`、`done`

**流程**：
```
yield agent_status(market, analysts, running)
yield thinking + content (市场分析师流式输出)
yield agent_status(market, analysts, done)
yield agent_report(market, "技术面摘要...")

... (依次各 Agent)

yield agent_status(bull, debate, running)
yield debate(bull, 1, "看多论据...")
yield agent_status(bear, debate, running)
yield debate(bear, 1, "看空论据...")

...

yield decision({action, target_price, ...})
yield title / summary / industries / done
```

---

## 7. 数据模型扩展

### 决策：复用现有模型，最小化扩展

**复用**：
- `AnalysisArticle` — 直接复用，新增 `article_type` 字段区分"事件分析"和"个股深度分析"
- `ArticleStock` — 直接复用
- `ArticleIndustry` — 直接复用
- `ChatSession` — 直接复用
- `ChatMessage` — 直接复用，`thinking_steps` JSON 扩展 schema

**新增字段**：
- `AnalysisArticle.article_type`: 'event' | 'stock_analysis' — 区分文章类型
- `AnalysisArticle.analysis_data`: JSON — 存储多Agent分析的结构化数据（各Agent报告、辩论记录、最终决策）

**新增表（可选）**：
- 暂不新增表，使用 `analysis_data` JSON 字段存储多Agent结构化数据，避免过度设计

---

## 8. 前端设计

### 决策：新增 StockAnalysisPage，复用现有 SSE 流式接收和对话组件

**新增页面/组件**：
- `StockAnalysisPage` — 个股深度分析主页面
- `AgentProgressPanel` — 多Agent工作进度面板（显示各Agent状态）
- `AgentReportCard` — 单个Agent分析结果卡片
- `DebateTimeline` — 辩论过程时间线
- `DecisionCard` — 最终决策卡片（买入/持有/卖出 + 目标价 + 置信度 + 风险评分）

**复用**：
- `AnalysisInput` — 输入框（扩展支持股票代码输入）
- `MessageBubble` / `ThinkingChain` — 思维链展示
- `IndustryTag` — 行业标签
- `StockCodeLink` — 股票代码链接

**路由**：
- `/stock-analysis` — 个股深度分析页

---

## 9. 辩论轮次配置化

### 决策：通过配置文件 + API 参数控制

- 默认值：投资辩论 2 轮，风险辩论 2 轮
- 配置来源：`app/core/config.py` 的 Settings 类
- 可通过前端下拉选择"分析深度"：快速（0轮辩论）/ 标准（2轮）/ 深度（4轮）

---

## 10. 快速分析 vs 完整分析

### 决策：同一个 Graph，通过 `analysis_mode` 参数条件路由

- `quick` 模式：Market Analyst → Fundamentals Analyst → Quick Decision Node → END
- `full` 模式：4 Analysts → 辩论 → 风险辩论 → 信号提取 → END
- 在 `GraphSetup` 中通过条件边实现分支：
  ```python
  def _route_after_analysts(state):
      if state["analysis_mode"] == "quick":
          return "Quick Decision"
      return "Bull Researcher"
  ```
