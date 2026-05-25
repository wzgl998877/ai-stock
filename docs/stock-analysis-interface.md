# 个股分析接口深度解析

> 本文档详细解析 `/api/chat/sessions/{sessionId}/stream` 接口在个股分析场景下的完整调用链路，包括 Agent 协作机制、数据查询策略、状态流转与 SSE 流式推送。适合后端开发者快速理解系统设计。

---

## 一、接口总览

### 1.1 入口：统一 SSE 流式网关

```
POST /api/chat/sessions/{sessionId}/stream
Content-Type: application/json
```

**请求体**：

```json
{
  "content": "请对贵州茅台(600519)进行深度分析",
  "event_type": "stock_analysis",
  "config": {
    "stock_code": "600519",
    "stock_name": "贵州茅台",
    "analysis_mode": "full"
  },
  "use_knowledge_base": true
}
```

通过 `event_type` 字段做策略分发：

| event_type | 分析类型 | 前端调用方 | 后端执行路径 |
|------------|---------|-----------|-------------|
| `"stock_analysis"` | 个股分析 | `stockAnalysisService.ts` | `StockAnalysisUseCase` + 多 Agent 工作流 |
| `"geopolitical"` / `"policy"` 等 | 事件分析 | `chatService.ts` | `ChatUseCase` + 单轮 LLM 对话 |

### 1.2 响应格式

响应为 SSE（Server-Sent Events）流，每个事件格式为：

```
data: {"type": "agent_status", "data": {"agent": "market_analyst", "phase": "analysts", "status": "done"}}

data: {"type": "content", "data": "当前股价1850元，MACD指标显示..."}

data: {"type": "decision", "data": {"action": "买入", "target_price": 1850, "confidence": 72.5}}
```

### 1.3 SSE 事件类型一览

| SSE 事件 | 事件分析 | 个股分析 | 说明 |
|----------|:-----------:|:-----------:|------|
| `thinking` | ✓ | ✓ | 思维链步骤 |
| `content` | ✓ | ✓ | LLM 逐字输出 |
| `agent_status` | ✗ | ✓ | Agent 完成状态 |
| `agent_report` | ✗ | ✓ | Agent 报告摘要 |
| `debate` | ✗ | ✓ | 辩论论据 |
| `decision` | ✗ | ✓ | 结构化决策结果 |
| `analysis_id` | ✗ | ✓ | 分析记录 ID |
| `title/summary/industries` | ✓ | ✓ | 元数据 |
| `done` | ✓ | ✓ | 流程结束标记 |
| `error` | ✓ | ✓ | 错误信息 |

---

## 二、后端分层架构

### 2.1 分层调用链

```
Router (chat.py)
  │  解析请求，创建 StreamingResponse
  ▼
Application UseCase (stock_analysis_use_case.py)
  │  双队列生产者-消费者模式，编排 LangGraph 工作流
  ▼
LangGraph StateGraph (stock_analysis_graph.py)
  │  状态机定义，控制 Agent 节点执行顺序和条件跳转
  ▼
Agent Nodes (nodes/*.py)
  │  各 Agent 的处理逻辑：工具调用 + LLM 生成报告
  ▼
Tools (tools/stock_data_toolkit.py)
  │  Function Calling 工具：查行情/K线/财务/新闻
  ▼
Infrastructure (repositories / market clients)
     数据库查询 + 外部 API 降级
```

### 2.2 关键文件索引

| 层次 | 文件路径 | 职责 |
|------|----------|------|
| Router | `app/routers/chat.py` | SSE 路由入口，`event_type` 分发 |
| Application DTO | `app/application/dtos/stock_analysis_dto.py` | 请求/响应数据结构 |
| Application | `app/application/use_cases/stock_analysis_use_case.py` | 编排 + 双队列 + 持久化 |
| State Machine | `app/infrastructure/workflow/graph/stock_analysis_graph.py` | 工作流图定义 |
| State | `app/infrastructure/workflow/state/stock_analysis_state.py` | 共享状态 DTO |
| Agent Nodes | `app/infrastructure/workflow/nodes/*.py` | 各 Agent 处理逻辑 |
| Tools | `app/infrastructure/workflow/tools/stock_data_toolkit.py` | LLM Function Calling 工具集 |
| AI Service | `app/infrastructure/ai/ai_service.py` | LLM 流式调用封装 |
| Prompts | `app/infrastructure/workflow/prompts/stock_analysis/*.py` | 各 Agent 的 Prompt 模板 |
| Repository | `app/infrastructure/repositories/mysql_stock_data_repo.py` | 数据库查询实现 |

---

## 三、LangGraph 工作流详解

### 3.1 FULL 模式完整流程图

```
START
  │
  ▼
┌──────────────────┐     ┌──────────────────────┐
│  market_analyst   │────→│  msg_clear_market     │  ← 清理工具调用消息
│  (技术面分析师)    │     └──────────┬───────────┘    防止上下文膨胀
└──────────────────┘                │
                                    ▼
┌──────────────────┐     ┌──────────────────────────┐
│ fundamentals_     │────→│ msg_clear_fundamentals    │
│ analyst (基本面)  │     └──────────┬───────────────┘
└──────────────────┘                │
                                    ▼
┌──────────────────┐     ┌───────────────────┐
│  news_analyst     │────→│ msg_clear_news     │
│  (新闻分析师)     │     └───────┬───────────┘
└──────────────────┘                │
                                    ▼
┌──────────────────┐     ┌────────────────────────┐
│ sentiment_analyst │────→│ msg_clear_sentiment     │
│ (情绪分析师)      │     └───────┬────────────────┘
└──────────────────┘                │
                                    ▼
                         ┌──── 条件路由 ────┐
                         │                  │
                    quick 模式          full 模式
                         │                  │
                         ▼                  ▼
                  ┌─────────────┐    ┌───────────────┐
                  │quick_decision│    │bull_researcher│←──┐ 看多
                  │ (快速决策)    │    │  (看多研究员)  │   │
                  └──────┬──────┘    └───────┬───────┘   │
                         │                   │            │
                         │                   ▼            │
                         │           ┌───────────────┐   │
                         │           │bear_researcher │   │ 看空
                         │           │  (看空研究员)   │───┘
                         │           └───────┬───────┘
                         │                   │ (达到最大轮次)
                         │                   ▼
                         │           ┌─────────────────┐
                         │           │research_manager  │
                         │           │ (研究经理/总结)   │
                         │           └───────┬─────────┘
                         │                   ▼
                         │           ┌─────────────────┐
                         │           │    trader        │
                         │           │   (交易员)       │
                         │           └───────┬─────────┘
                         │                   ▼
                         │        ┌──────────────────────┐
                         │        │  risky_debator        │←──┐ 激进
                         │        │  (激进风险辩手)       │   │
                         │        └──────────┬───────────┘   │
                         │                   ▼               │
                         │        ┌──────────────────────┐   │
                         │        │  safe_debator         │   │ 保守
                         │        │  (保守风险辩手)       │───┤
                         │        └──────────┬───────────┘   │
                         │                   ▼               │
                         │        ┌──────────────────────┐   │
                         │        │  neutral_debator      │   │ 中立
                         │        │  (中立风险辩手)       │───┘
                         │        └──────────┬───────────┘
                         │                   │ (达到最大轮次)
                         │                   ▼
                         │           ┌─────────────────┐
                         │           │   risk_judge     │
                         │           │  (风险裁决官)     │
                         │           └───────┬─────────┘
                         │                   ▼
                         │           ┌─────────────────┐
                         │           │signal_extractor  │
                         │           │ (信号提取/结构化) │
                         │           └───────┬─────────┘
                         │                   │
                         ▼                   ▼
                        END                 END
```

### 3.2 条件路由函数

工作流中有三个关键的条件路由：

#### `_route_after_analysts` — 分析师阶段完成后

```python
def _route_after_analysts(state: dict) -> str:
    analysis_mode = state.get("analysis_mode", "full")
    if analysis_mode == "quick":
        return "quick_decision"      # quick 模式 → 快速决策 → END
    return "bull_researcher"         # full 模式 → 进入辩论流程
```

#### `_should_continue_investment_debate` — 投资辩论循环控制

```python
def _should_continue_investment_debate(state: dict) -> str:
    debate_state = state.get("investment_debate_state", {})
    round_count = debate_state.get("round", 0)
    max_rounds = settings.debate_rounds * 2  # 每轮包含 bull+bear 各一次

    if round_count >= max_rounds:
        return "research_manager"    # 达到最大轮次 → 研究经理总结

    current_agent = state.get("current_agent", "")
    if current_agent == "bull_researcher":
        return "bear_researcher"     # 看多说完 → 看空反驳
    else:
        return "bull_researcher"     # 看空说完 → 看多反驳
```

#### `_should_continue_risk_debate` — 风险辩论循环控制

```python
def _should_continue_risk_debate(state: dict) -> str:
    risk_state = state.get("risk_debate_state", {})
    round_count = risk_state.get("round", 0)
    max_rounds = settings.risk_debate_rounds * 3  # 每轮 risky+safe+neutral 各一次

    if round_count >= max_rounds:
        return "risk_judge"          # 达到最大轮次 → 风险裁决

    current_agent = state.get("current_agent", "")
    if current_agent == "risky_debator":
        return "safe_debator"
    elif current_agent == "safe_debator":
        return "neutral_debator"
    else:
        return "risky_debator"
```

---

## 四、Agent 协作机制：状态传递

### 4.1 共享状态定义

LangGraph 的核心是共享状态对象（`StockAnalysisState`），所有 Agent 节点读写同一个状态：

```python
# 合并三层 TypedDict
class StockAnalysisState(StockAnalysisInput, StockAnalysisWorking, StockAnalysisOutput, total=False):
    pass

class StockAnalysisInput(TypedDict, total=False):
    """输入层：发起分析时的参数"""
    stock_code: str
    stock_name: str
    analysis_mode: str          # "quick" | "full"

class StockAnalysisWorking(TypedDict, total=False):
    """中间态：分析过程中的工作数据"""
    # 分析师阶段
    market_report: str          # market_analyst 写入
    fundamentals_report: str    # fundamentals_analyst 写入
    news_report: str            # news_analyst 写入
    sentiment_report: str       # sentiment_analyst 写入
    # 辩论阶段
    investment_debate_state: dict   # bull/bear 轮流写入
    investment_plan: str            # research_manager 写入
    trader_investment_plan: str     # trader 写入
    # 风险辩论阶段
    risk_debate_state: dict         # risky/safe/neutral 轮流写入
    # 进度追踪
    current_agent: str
    current_phase: str              # "analysts" | "debate" | "trader" | "risk" | "done"
    messages: list[dict]

class StockAnalysisOutput(TypedDict, total=False):
    """输出层：最终结果"""
    action: str                # 买入/持有/卖出
    target_price: float
    stop_loss_price: float
    expected_return: float
    confidence: float          # 0-100
    risk_score: float          # 0-100
    reasoning: str
```

### 4.2 数据流转完整过程

```
state = { stock_code: "600519", stock_name: "贵州茅台", analysis_mode: "full" }
  │
  ▼
┌─ market_analyst ─────────────────────────────────────────────────────┐
│  读取: state.stock_code, state.stock_name                            │
│  动作: LLM 自主调用 get_stock_quote + get_stock_history 工具         │
│  写入: state.market_report = "当前股价1850，MACD金叉..."             │
│  SSE:  thinking → agent_report(summary)                              │
└──────────────────────────────────────────────────────────────────────┘
  │  ← msg_clear（清理工具调用消息，控制上下文长度）
  ▼
┌─ fundamentals_analyst ───────────────────────────────────────────────┐
│  读取: state.stock_code, state.stock_name                            │
│  动作: LLM 自主调用 get_stock_financial + get_stock_quote            │
│  写入: state.fundamentals_report = "PE=35x，ROE=30%..."              │
│  SSE:  agent_report(summary)                                         │
└──────────────────────────────────────────────────────────────────────┘
  │
  ▼ (news_analyst / sentiment_analyst 同理，各写 state.news_report /
  │  state.sentiment_report)
  ▼
┌─ bull_researcher ────────────────────────────────────────────────────┐
│  读取: state.market_report + fundamentals_report + news_report       │
│        + sentiment_report（通过 _build_analyst_reports 拼接）        │
│  动作: 不调用工具，LLM 基于所有分析师报告生成看多论据                  │
│  写入: state.investment_debate_state.bull_arguments = "..."          │
│        state.investment_debate_state.round += 1                      │
│  SSE:  debate(speaker="bull_researcher", content=...)                │
└──────────────────────────────────────────────────────────────────────┘
  │
  ▼
┌─ bear_researcher ────────────────────────────────────────────────────┐
│  读取: 所有分析师报告 + bull 的看多论据                               │
│  动作: LLM 生成看空论据，反驳看多观点                                 │
│  写入: state.investment_debate_state.bear_arguments = "..."          │
│  SSE:  debate(speaker="bear_researcher", content=...)                │
└──────────────────────────────────────────────────────────────────────┘
  │
  │  (bull ⇄ bear 循环，达到 max_rounds 后退出)
  ▼
┌─ research_manager ───────────────────────────────────────────────────┐
│  读取: 所有分析师报告 + 全部辩论记录                                  │
│  动作: LLM 综合看多/看空论据，生成投资计划                            │
│  写入: state.investment_plan = "建议谨慎买入，目标价XXXX..."          │
│  SSE:  agent_report(summary)                                         │
└──────────────────────────────────────────────────────────────────────┘
  │
  ▼
┌─ trader ─────────────────────────────────────────────────────────────┐
│  读取: state.investment_plan                                         │
│  动作: LLM 根据投资计划生成具体交易建议（含结构化 JSON）              │
│  写入: state.trader_action = "买入"                                  │
│        state.trader_target_price = 1850.0                            │
│        state.trader_stop_loss_price = 1750.0                         │
│        state.trader_confidence = 72.5                                │
│  SSE:  agent_report(summary)                                         │
└──────────────────────────────────────────────────────────────────────┘
  │
  ▼
┌─ risky/safe/neutral_debator (风险辩论循环) ──────────────────────────┐
│  读取: trader 交易建议 + 所有分析报告                                 │
│  动作: 从激进/保守/中立三个角度辩论交易风险                           │
│  写入: state.risk_debate_state.risky_view / safe_view / neutral_view │
│  SSE:  debate(speaker="risky/safe/neutral", content=...)             │
└──────────────────────────────────────────────────────────────────────┘
  │
  ▼
┌─ risk_judge ─────────────────────────────────────────────────────────┐
│  读取: risky_view + safe_view + neutral_view（三方观点）             │
│  动作: 使用深度思考模型(llm_deep_model)综合裁决                      │
│  写入: state.risk_judge_action / risk_judge_risk_score / ...         │
│  SSE:  agent_report(summary)                                         │
└──────────────────────────────────────────────────────────────────────┘
  │
  ▼
┌─ signal_extractor ───────────────────────────────────────────────────┐
│  读取: risk_judge / trader 写入的结构化字段（优先直接取值）           │
│  降级: AI 文本提取（JSON 解析失败时）                                 │
│  写入: state.action = "买入"                                         │
│        state.target_price = 1850.0                                   │
│        state.confidence = 72.5                                       │
│        state.risk_score = 35.0                                       │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 五、数据查询：Function Calling 工具机制

### 5.1 Agent 不直接查数据库

分析师节点通过 **LLM Function Calling** 自主决定要查什么数据。系统注册了 4 个工具给 LLM：

| 工具名 | 用途 | 参数 |
|--------|------|------|
| `get_stock_quote` | 获取实时行情 | `stock_code` |
| `get_stock_history` | 获取历史 K 线 | `stock_code`, `period`, `days` |
| `get_stock_financial` | 获取财务指标 | `stock_code` |
| `get_stock_news` | 获取最新新闻 | `stock_code` |

### 5.2 单个 Agent 的工具调用流程（以技术面分析师为例）

```python
# market_analyst 节点核心逻辑

messages = [
    {"role": "system", "content": "你是一位专业的A股技术面分析师..."},
    {"role": "user", "content": "请分析贵州茅台(600519)的技术面情况"},
]

tools_schema = get_stock_tools_schema()  # 4个工具的 OpenAI JSON Schema

# 循环调用工具，最多 3 次（max_tool_calls=3）
for _ in range(3):
    # 1. 把 messages + tools 发给 LLM，让 LLM 决定是否调用工具
    response = await ai_service.tool_call(messages=messages, tools=tools_schema)

    tool_calls = response.get("tool_calls", [])
    if not tool_calls:
        break  # LLM 说"我不需要更多数据了"

    # 2. 执行 LLM 选择的工具
    for tc in tool_calls:
        tool_result = await execute_tool(tc.function.name, tc.function.arguments)
        messages.append({"role": "tool", "content": str(tool_result)})

# 3. 基于所有工具数据，流式生成完整分析报告
async for chunk in ai_service.stream_chat(history_messages=messages):
    full_text += chunk.text
    content_queue.put(chunk.text)  # 实时推给前端
```

**实际执行过程示例**：

```
第1轮 LLM 调用:
  LLM → tool_call: get_stock_quote(600519)           ← LLM 自己决定要查行情
  系统 → 返回: {price: 1850, change_pct: +1.2%, ...}

第2轮 LLM 调用:
  LLM → tool_call: get_stock_history(600519, daily, 60)  ← LLM 还要看 K 线
  系统 → 返回: [{date: "2026-05-01", open: 1820, ...}, ...]

第3轮 LLM 调用 (达到 max_tool_calls 上限):
  LLM → 直接输出完整分析报告（不再调用工具）
  → "当前股价1850元，5日均线上穿20日均线形成金叉，MACD柱状图由绿转红..."
```

### 5.3 各 Agent 使用的工具差异

| Agent | 可用工具 | 工具调用 | 说明 |
|-------|---------|---------|------|
| `market_analyst` | 全部 4 个 | 通常调 `get_stock_quote` + `get_stock_history` | LLM 自主选择 |
| `fundamentals_analyst` | 全部 4 个 | 通常调 `get_stock_financial` + `get_stock_quote` | LLM 自主选择 |
| `news_analyst` | 全部 4 个 + RAG | 通常调 `get_stock_news` + 知识库检索 | 额外支持 RAG |
| `sentiment_analyst` | 全部 4 个 | 通常调 `get_stock_news` | LLM 自主选择 |
| `bull/bear_researcher` | 无 | 不调用工具 | 读上游报告 |
| `research_manager` | 无 | 不调用工具 | 读辩论记录 |
| `trader` | 无 | 不调用工具 | 读投资计划 |
| `risky/safe/neutral` | 无 | 不调用工具 | 读交易建议 |
| `risk_judge` | 无 | 不调用工具 | 读三方观点 |
| `signal_extractor` | 无 | 不调用工具 | 读结构化字段 |

### 5.4 数据查询的多级降级策略

每个工具函数都有"**数据库优先 + 外部 API 降级**"机制：

```
get_stock_quote (实时行情):
  第1级: MySQL MarketQuote 表 ──失败──→ 第2级: Tushare pro.rt_k() ──失败──→ 第3级: BaoStock

get_stock_history (历史K线):
  第1级: MySQL StockDailyQuote 表 ──失败──→ 第2级: 新浪财经 JSONP 接口

get_stock_financial (财务指标):
  第1级: MySQL StockFinancial 表 ──失败──→ 第2级: Tushare fina_indicator()

get_stock_news (新闻):
  唯一来源: AKShare stock_news_em()（东方财富个股新闻）
```

### 5.5 msg_clear 节点的作用

每个分析师节点后都有一个 `msg_clear` 节点，用于**清理工具调用的消息历史**：

```python
# msg_clear 节点：清理上游 Agent 的工具调用消息，只保留分析报告
def create_msg_clear_node(agent_name: str):
    async def msg_clear_node(state: dict) -> dict:
        return {"messages": []}  # 清空 messages，防止上下文膨胀
    return msg_clear_node
```

**为什么需要清理**：分析师节点的 `messages` 列表中包含了多轮工具调用（`tool_call` + `tool` 消息），如果不清理，传给下游辩论节点时上下文会非常大，既浪费 token 又影响 LLM 性能。

---

## 六、双队列流式推送机制

### 6.1 设计目标

LangGraph 以节点为单位执行（`stream_mode="updates"`），每个节点完成后才产出一次更新。但 LLM 的流式输出是逐字产生的。为了让前端**既能看到结构化事件（如 Agent 完成），又能实时看到 LLM 的逐字输出**，设计了双队列机制。

### 6.2 架构图

```
                    LangGraph 各 Agent 节点
                    ┌──────────────────┐
                    │  节点内部执行：    │
                    │  1. tool_call 查数据│
                    │  2. stream_chat   │
                    │     生成报告       │
                    └───────┬─────┬────┘
                            │     │
            ┌───────────────┘     └───────────────┐
            │ LLM token chunks                    │ 结构化事件
            │ (逐字输出)                            │ (agent_status 等)
            ▼                                     ▼
    ┌──────────────┐                    ┌──────────────┐
    │content_queue │                    │  sse_queue   │
    │              │                    │              │
    │ "当前"       │                    │ {type:       │
    │ "股价"       │                    │  "agent_     │
    │ "1850"       │                    │  report",    │
    │ "元"         │                    │  data: ...}  │
    └──────┬───────┘                    └──────┬───────┘
           │     ┌──────────────┐              │
           └────→│  主循环消费者  │←─────────────┘
                 │              │
                 │  while True:  │
                 │   1.先消费     │
                 │    sse_queue  │     ← 优先！确保结构化事件及时到达
                 │   2.再消费     │
                 │    content_q  │     ← 每轮最多 5 个 chunk，限流
                 │   3.都空则等   │
                 │    100ms      │
                 └──────┬───────┘
                        │
                        ▼
                 yield SSE event → StreamingResponse → 前端
```

### 6.3 生产者：`_run_graph_task`

```python
async def _run_graph_task():
    # 启动 LangGraph 工作流
    async for update in stock_analysis_graph.astream(
        {"stock_code": ..., "stock_name": ..., "analysis_mode": ..., "_content_queue": content_queue},
        stream_mode="updates",  # 每个节点完成后 yield 一次
    ):
        for node_name, state_update in update.items():
            # === 转换为 SSE 事件 ===

            if node_name == "market_analyst":
                report = state_update.get("market_report", "")
                await sse_queue.put({"type": "agent_status", "data": {"agent": "market_analyst", "status": "done"}})
                await sse_queue.put({"type": "agent_report", "data": {"agent": "market_analyst", "summary": report[:500]}})

            elif node_name in ("bull_researcher", "bear_researcher"):
                debate = state_update.get("investment_debate_state", {})
                await sse_queue.put({"type": "debate", "data": {"speaker": node_name, "content": debate.get(...), "round": ...}})

            # ... 其他节点类似

    await sse_queue.put({"type": "graph_done"})  # 结束信号
```

### 6.4 消费者：主循环

```python
async def execute(...):
    sse_queue = asyncio.Queue()     # 结构化事件队列
    content_queue = asyncio.Queue() # LLM 文本 chunk 队列

    asyncio.create_task(_run_graph_task())  # 后台启动生产者

    while not graph_finished:
        # 1. 优先消费 sse_queue
        while not sse_queue.empty():
            event = sse_queue.get_nowait()
            if event["type"] == "graph_done":
                graph_finished = True; break
            yield event

        # 2. 再消费 content_queue（每轮最多 5 个 chunk，限流）
        for _ in range(5):
            try:
                chunk = content_queue.get_nowait()
                yield {"type": "content", "data": chunk}
            except asyncio.QueueEmpty:
                break

        # 3. 两个队列都空时，等 100ms
        if sse_queue.empty() and content_queue.empty():
            event = await asyncio.wait_for(sse_queue.get(), timeout=0.1)
```

**设计要点**：
- **sse_queue 优先**：确保 `agent_status`、`decision` 等结构化事件及时到达前端
- **content_queue 限流**：每轮最多 5 个 chunk，避免大量文本阻塞结构化事件
- **100ms 超时等待**：避免忙等待消耗 CPU

---

## 七、数据持久化

### 7.1 增量写入策略

分析过程中采用**增量写入**，而非等全部完成后一次性写入：

| 时机 | 操作 | 数据表 |
|------|------|--------|
| 开始分析前 | 创建 `in_progress` 记录 | `t_stock_analysis` |
| 每个 Agent 完成时 | 更新该 Agent 的 detail | `t_stock_analysis_detail` |
| 阶段切换时 | 更新 `current_phase` | `t_stock_analysis` |
| 全部完成后 | 更新最终结果 + 同步知识库 | `t_stock_analysis` + `t_article` |

### 7.2 保存点详解

```python
# 保存点1：创建分析记录（LangGraph 执行前）
sa = StockAnalysis(
    analysis_id=analysis_id,
    stock_code=stock_code, stock_name=stock_name,
    status="in_progress", current_phase="analysts",
)
await stock_analysis_repo.create(sa)

# 保存点2：每个 Agent 完成时增量更新
await stock_analysis_repo.update_detail_by_agent(
    analysis_id, "market_analyst",
    status="done",
    summary=report[:500],          # 摘要（SSE 推送给前端的）
    full_report=full_text,         # 完整报告
)

# 保存点3：保存 AI 消息到聊天记录
ai_msg = ChatMessage(
    role="assistant",
    content=full_content[:60000],  # 截断为 60000 字符
    thinking_steps=thinking_steps,
    event_type="stock_analysis",
)
await chat_repo.add_message(ai_msg)

# 保存点4：更新最终结果 + 同步知识库
await stock_analysis_repo.update_result(
    analysis_id,
    title=title, summary=summary, full_content=full_content,
    decision_action="买入", target_price=1850.0,
    confidence=72.5, risk_score=35.0,
)
await stock_analysis_repo.sync_to_article(analysis_id)  # 同步到知识库，供 RAG 检索
```

### 7.3 异常处理

超时 / 异常 / 取消时，已生成的部分结果会被保留：

```python
except (TimeoutError, Exception, asyncio.CancelledError):
    await chat_repo.session.rollback()
    await stock_analysis_repo.update_status(analysis_id, "stopped")
    await chat_repo.session.commit()
```

---

## 八、Prompt 模板

### 8.1 分析师 Prompt 示例

**技术面分析师** (`prompts/stock_analysis/market_analyst.py`)：

```python
SYSTEM_PROMPT = """你是一位专业的A股技术面分析师。通过K线、均线、MACD、KDJ等技术指标分析股票走势。
所有分析内容仅供学习研究参考，不构成任何投资建议。"""

USER_TEMPLATE = """请分析 {stock_name}({stock_code}) 的技术面情况。
分析要点：
1) 当前K线形态和趋势
2) 均线系统排列
3) MACD和KDJ指标信号
4) 成交量变化
5) 支撑位和压力位
请给出明确的技术面判断。"""
```

**基本面分析师** (`prompts/stock_analysis/fundamentals_analyst.py`)：

```python
SYSTEM_PROMPT = """你是一位专业的A股基本面分析师。通过PE、PB、营收、净利润、ROE等财务指标分析公司价值。
所有分析内容仅供学习研究参考，不构成任何投资建议。"""

USER_TEMPLATE = """请分析 {stock_name}({stock_code}) 的基本面情况。
分析要点：
1) PE/PB估值水平
2) 营收和净利润增长
3) ROE和毛利率
4) 负债率
5) 行业地位
请给出明确的基本面判断。"""
```

### 8.2 辩论节点 Prompt 特点

看多/看空研究员不调用工具，而是**读取上游所有分析师的报告**，基于这些数据生成论据：

```python
# bull_researcher 读取上游报告
def _build_analyst_reports(state: dict) -> str:
    parts = []
    if state.get("market_report"):
        parts.append(f"【技术面分析报告】\n{state['market_report']}")
    if state.get("fundamentals_report"):
        parts.append(f"【基本面分析报告】\n{state['fundamentals_report']}")
    if state.get("news_report"):
        parts.append(f"【新闻分析报告】\n{state['news_report']}")
    if state.get("sentiment_report"):
        parts.append(f"【情绪分析报告】\n{state['sentiment_report']}")
    return "\n\n".join(parts)
```

### 8.3 结构化输出节点

`trader`、`risk_judge`、`signal_extractor` 节点要求 LLM 输出 JSON 格式的结构化数据：

```json
{
  "action": "买入",
  "target_price": 1850.0,
  "stop_loss_price": 1750.0,
  "confidence": 72.5,
  "risk_score": 35.0,
  "reasoning": "技术面MACD金叉确认，基本面PE低于行业均值..."
}
```

系统会尝试解析 JSON，解析失败时降级为正则提取关键字段。

---

## 九、Java 对比速查表

适合熟悉 Java 的开发者快速对照理解：

| Python (本项目) | Java 等价 |
|----------------|----------|
| `FastAPI Router` | `@RestController` |
| `StreamingResponse` + `AsyncGenerator` | `Flux<ServerSentEvent<String>>` (WebFlux) |
| `Pydantic BaseModel` | `@Data` + `@RequestBody` DTO |
| `LangGraph StateGraph` | Spring Statemachine / 自定义状态机 |
| `asyncio.Queue` (双队列) | `Sinks.Many<T>` (Reactor) |
| `asyncio.create_task` | `CompletableFuture.runAsync` |
| `event_type` if-else 分发 | 策略模式 `Map<String, UseCase>` |
| `AIService.stream_chat()` | OpenAI Java SDK `streamChatCompletion()` |
| `@tool` (LangChain) | OpenAI Function Calling `ToolDefinition` |
| `TypedDict` (State) | `@Data` Context DTO |
| `async for update in graph.astream()` | `stateMachine.start(listener)` |
| `await asyncio.to_thread(sync_func)` | `CompletableFuture.supplyAsync(syncFunc)` |
| DB 优先 + API 降级 | 责任链模式 / Spring Retry |

### Router 层 Java 对比

```java
// Python (FastAPI)
@router.post("/sessions/{session_id}/stream")
async def stream_message(session_id: str, body: SendMessageRequest, ...):
    return StreamingResponse(_sse_stream(use_case.stream_chat(...)), media_type="text/event-stream")

// Java (Spring WebFlux) 等价
@RestController
@RequestMapping("/api/chat/sessions")
public class ChatController {
    @PostMapping(value = "/{sessionId}/stream", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public Flux<ServerSentEvent<String>> streamMessage(
            @PathVariable String sessionId, @RequestBody SendMessageRequest body) {
        return chatUseCase.streamChat(sessionId, body.getContent(), body.getEventType())
                .map(event -> ServerSentEvent.<String>builder().data(toJson(event)).build());
    }
}
```

### 状态机 Java 对比

```java
// Python (LangGraph)
graph = StateGraph(StockAnalysisState)
graph.add_node("market_analyst", market_analyst_node)
graph.add_conditional_edges("msg_clear_sentiment", _route_after_analysts, {...})

// Java (Spring Statemachine) 等价
builder.configureStates().withStates()
    .initial(START).states(EnumSet.allOf(States.class));
builder.configureTransitions()
    .withExternal().source(START).target(MARKET_ANALYST)
    .and()
    .withChoice().in(MSG_CLEAR_SENTIMENT)
        .first(QUICK_DECISION, ctx -> isQuickMode())
        .last(BULL_RESEARCHER);
```

### Function Calling Java 对比

```java
// Python
tool_result = await asyncio.to_thread(tool_func, **func_args)
messages.append({"role": "tool", "content": str(tool_result)})

// Java 等价
ToolCall tc = response.getToolCalls().get(0);
String result = toolExecutor.execute(tc.getName(), tc.getArguments());
messages.add(new ToolMessage(tc.getId(), result));
```

---

## 十、DTO 定义

### 请求 DTO

```python
class SendMessageRequest(BaseModel):
    content: str = Field(..., min_length=2, max_length=5000)
    event_type: Optional[str] = None          # "stock_analysis" | "geopolitical" | ...
    config: Optional[dict] = None             # 个股分析: {stock_code, stock_name, analysis_mode}
    use_knowledge_base: bool = True

@dataclass
class StockAnalysisConfigDTO:
    stock_code: str = ""
    stock_name: str = ""
    analysis_mode: str = "full"               # "quick" | "full"
    debate_rounds: int = 2
    risk_debate_rounds: int = 2
```

### 响应/事件 DTO

```python
@dataclass
class AgentStatusDTO:
    agent: str = ""          # "market_analyst" | "bull_researcher" | ...
    phase: str = ""          # "analysts" | "debate" | "trader" | "risk"
    status: str = ""         # "running" | "done" | "failed"

@dataclass
class DebateDTO:
    speaker: str = ""        # "bull_researcher" | "bear_researcher" | "risky_debator" | ...
    round: int = 1
    content: str = ""

@dataclass
class DecisionDTO:
    action: str = ""         # "买入" | "持有" | "卖出"
    target_price: float = 0.0
    stop_loss_price: float = 0.0
    confidence: float = 0.0  # 0-100
    risk_score: float = 0.0  # 0-100
    reasoning: str = ""
```

---

## 附录：配置参数

| 参数 | 配置位置 | 默认值 | 说明 |
|------|---------|--------|------|
| `max_tool_calls` | `stock_analysis_graph.py` | 3 | 每个 Agent 最大工具调用次数 |
| `debate_rounds` | `settings.debate_rounds` | 2 | 投资辩论轮次（每轮 bull+bear） |
| `risk_debate_rounds` | `settings.risk_debate_rounds` | 2 | 风险辩论轮次（每轮 risky+safe+neutral） |
| `analysis_timeout` | `settings.analysis_timeout` | 3600 | 分析超时时间（秒） |
| `llm_deep_model` | `settings.llm_deep_model` | 可选 | risk_judge 使用的深度思考模型 |
| `llm_model` | `settings.llm_model` | 必填 | 默认 LLM 模型 |
