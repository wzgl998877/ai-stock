# 模块二：个股深度分析 — Prompt 与调用链深度分析报告

> 生成时间: 2026-04-25
> 分析目标: 个股深度分析的实现方式及发送给大模型的提示词构造逻辑

---

## 一、整体架构

### 工作流图结构 (LangGraph)

```
START → market_analyst → msg_clear → fundamentals_analyst → msg_clear
→ news_analyst → msg_clear → sentiment_analyst → msg_clear
→ 条件路由
    quick模式 → quick_decision → END
    full模式 → bull_researcher ⇄ bear_researcher (辩论循环2轮)
    → research_manager → trader
    → risky_debator ⇄ safe_debator ⇄ neutral_debator (风险辩论循环2轮)
    → risk_judge → signal_extractor → END
```

### 13个 Agent 总览

| 阶段 | Agent | 模型 | temperature | 工具调用 | JSON输出 |
|------|-------|------|-------------|---------|---------|
| 分析师 | market_analyst | 默认模型 | 0.3 | get_stock_quote + get_stock_history | 否 |
| 分析师 | fundamentals_analyst | 默认模型 | 0.3 | get_stock_financial | 否 |
| 分析师 | news_analyst | 默认模型 | 0.3 | get_stock_news | 否 |
| 分析师 | sentiment_analyst | 默认模型 | 0.3 | get_stock_quote | 否 |
| 辩论 | bull_researcher | 默认模型 | 0.5 | 无 | 否 |
| 辩论 | bear_researcher | 默认模型 | 0.5 | 无 | 否 |
| 管理 | research_manager | **深度模型** | 0.3 | 无 | 否 |
| 交易 | trader | 默认模型 | 0.3 | 无 | 是 |
| 风险 | risky_debator | 默认模型 | 0.5 | 无 | 否 |
| 风险 | safe_debator | 默认模型 | 0.5 | 无 | 否 |
| 风险 | neutral_debator | 默认模型 | 0.5 | 无 | 否 |
| 裁决 | risk_judge | **深度模型** | 0.2 | 无 | 是 |
| 提取 | signal_extractor | 默认模型 | 0.1 | 无 | 是 |

---

## 二、完整提示词清单

### 1. 技术面分析师 (market_analyst)

**文件**: `backend/app/infrastructure/workflow/prompts/stock_analysis/market_analyst.py`

**SYSTEM_PROMPT**:
```
你是一位专业的A股技术面分析师。通过K线、均线、MACD、KDJ等技术指标分析股票走势。所有分析内容仅供学习研究参考，不构成任何投资建议。
```

**USER_TEMPLATE**:
```
请分析 {stock_name}({stock_code}) 的技术面情况。分析要点：1)当前K线形态和趋势 2)均线系统排列 3)MACD和KDJ指标信号 4)成交量变化 5)支撑位和压力位。请给出明确的技术面判断。
```

**工具调用**: `tool_call(messages, tools=[get_stock_quote, get_stock_history, get_stock_financial, get_stock_news], tool_choice="auto")`，最多3轮

**最终调用**: `stream_chat(history_messages=messages, temperature=0.3, max_tokens=4096)`

**实际发送到 LLM 的 messages**:
```json
[
  {"role": "system", "content": "你是一位专业的A股技术面分析师..."},
  {"role": "user", "content": "请分析 贵州茅台(600519) 的技术面情况..."},
  {"role": "assistant", "tool_calls": [{"function": {"name": "get_stock_quote", "arguments": "{\"stock_code\": \"600519\"}"}}]},
  {"role": "tool", "tool_call_id": "xxx", "content": "{\"代码\": \"600519\", \"最新价\": \"1680.00\", ...}"},
  {"role": "assistant", "tool_calls": [{"function": {"name": "get_stock_history", "arguments": "{\"stock_code\": \"600519\", \"days\": 60}"}}]},
  {"role": "tool", "tool_call_id": "yyy", "content": "[{\"日期\": \"2026-02-01\", \"开盘\": \"1650.00\", ...}]"}
]
```

---

### 2. 基本面分析师 (fundamentals_analyst)

**文件**: `backend/app/infrastructure/workflow/prompts/stock_analysis/fundamentals_analyst.py`

**SYSTEM_PROMPT**:
```
你是一位专业的A股基本面分析师。通过PE、PB、营收、净利润、ROE等财务指标分析公司价值。所有分析内容仅供学习研究参考，不构成任何投资建议。
```

**USER_TEMPLATE**:
```
请分析 {stock_name}({stock_code}) 的基本面情况。分析要点：1)PE/PB估值水平 2)营收和净利润增长 3)ROE和毛利率 4)负债率 5)行业地位。请给出明确的基本面判断。
```

**工具调用**: 同上4个工具schema，LLM 自主选择 `get_stock_financial`

---

### 3. 新闻分析师 (news_analyst)

**文件**: `backend/app/infrastructure/workflow/prompts/stock_analysis/news_analyst.py`

**SYSTEM_PROMPT**:
```
你是一位专业的A股新闻分析师。通过分析公司最新新闻、公告、行业动态来评估对股价的潜在影响。所有分析内容仅供学习研究参考，不构成任何投资建议。
```

**USER_TEMPLATE**:
```
请分析 {stock_name}({stock_code}) 的最新新闻动态。分析要点：1)近期重要新闻和公告 2)行业政策变化 3)重大事件影响 4)市场情绪导向。请评估新闻面对股价的影响方向。
```

**工具调用**: LLM 自主选择 `get_stock_news`

---

### 4. 情绪分析师 (sentiment_analyst)

**文件**: `backend/app/infrastructure/workflow/prompts/stock_analysis/sentiment_analyst.py`

**SYSTEM_PROMPT**:
```
你是一位专业的A股市场情绪分析师。通过融资融券、北向资金、龙虎榜等数据分析市场情绪。所有分析内容仅供学习研究参考，不构成任何投资建议。
```

**USER_TEMPLATE**:
```
请分析 {stock_name}({stock_code}) 的市场情绪。分析要点：1)融资融券余额变化 2)北向资金流向 3)龙虎榜数据 4)主力资金动向 5)散户情绪指标。请给出当前市场情绪的整体判断。
```

**工具调用**: LLM 自主选择 `get_stock_quote`（含资金流向字段）

---

### 5. 看多研究员 (bull_researcher)

**文件**: `backend/app/infrastructure/workflow/prompts/stock_analysis/bull_researcher.py`

**SYSTEM_PROMPT**:
```
你是一位看多研究员。根据所有分析师的报告，提出看多的投资论据。你的目标是找出所有支持上涨的因素。所有分析内容仅供学习研究参考，不构成任何投资建议。
```

**USER_TEMPLATE**:
```
根据以下分析师报告：{analyst_reports}，请提出看多 {stock_name} 的投资论据。要求：1)至少提出3个核心看多逻辑 2)引用具体数据和指标支撑 3)指出潜在的上涨催化因素 4)给出合理的目标价区间。
```

**变量注入**: `analyst_reports` = 4份报告拼接:
```
【技术面分析报告】
{market_report}

【基本面分析报告】
{fundamentals_report}

【新闻分析报告】
{news_report}

【情绪分析报告】
{sentiment_report}
```

**调用**: `stream_chat(history_messages=messages, temperature=0.5, max_tokens=4096)`

---

### 6. 看空研究员 (bear_researcher)

**文件**: `backend/app/infrastructure/workflow/prompts/stock_analysis/bear_researcher.py`

**SYSTEM_PROMPT**:
```
你是一位看空研究员。根据所有分析师的报告和看多论据，提出看空的投资论据和风险点。所有分析内容仅供学习研究参考，不构成任何投资建议。
```

**USER_TEMPLATE**:
```
根据以下分析师报告：{analyst_reports}

看多论据：{bull_arguments}，请提出看空 {stock_name} 的投资论据。要求：1)至少提出3个核心风险因素 2)反驳看多论据的薄弱环节 3)指出潜在的下跌风险 4)给出合理的安全边际价格。
```

**变量注入**: `analyst_reports`(同上) + `bull_arguments`(看多论据完整文本)

**调用**: `stream_chat(history_messages=messages, temperature=0.5, max_tokens=4096)`

---

### 7. 研究管理器 (research_manager) ⭐深度模型

**文件**: `backend/app/infrastructure/workflow/prompts/stock_analysis/research_manager.py`

**SYSTEM_PROMPT**:
```
你是一位资深研究管理器。你需要综合看多和看空双方的观点，做出客观的投资计划。你必须仔细权衡双方的论据。所有分析内容仅供学习研究参考，不构成任何投资建议。
```

**USER_TEMPLATE**:
```
根据以下辩论记录：{debate_history}

请综合评估并制定投资计划：1)总结看多和看空的核心论据 2)评估各方论据的可靠性 3)给出你的倾向性判断 4)制定详细的投资计划（包括建议仓位、入场时机、止损位）。
```

**变量注入**: `debate_history` = 辩论历史拼接:
```
辩论轮次: {round_count}

【看多论据】
{bull_arguments}

【看空论据】
{bear_arguments}
```

**调用**: `stream_chat(history_messages=messages, model=settings.llm_deep_model, temperature=0.3, max_tokens=4096)`

---

### 8. 交易员 (trader)

**文件**: `backend/app/infrastructure/workflow/prompts/stock_analysis/trader.py`

**SYSTEM_PROMPT**:
```
你是一位经验丰富的A股交易员。根据研究管理器的投资计划，给出具体的交易建议。所有分析内容仅供学习研究参考，不构成任何投资建议。
```

**USER_TEMPLATE**:
```
根据以下投资计划：{investment_plan}

请给出 {stock_name}({stock_code}) 的具体交易建议：1)操作方向（买入/持有/卖出）2)建议入场价格区间 3)目标价格 4)止损价格 5)建议仓位比例。请用以下JSON格式输出决策：
```json
{"action": "买入/持有/卖出", "target_price": 数字, "confidence": 0-100, "reasoning": "决策理由"}
```
```

**变量注入**: `investment_plan` + `stock_name` + `stock_code`

**调用**: `stream_chat(history_messages=messages, temperature=0.3, max_tokens=4096)`

---

### 9. 激进风险分析师 (risky_debator)

**文件**: `backend/app/infrastructure/workflow/prompts/stock_analysis/risky_debator.py`

**SYSTEM_PROMPT**:
```
你是一位激进的风险分析师。你倾向于发现投资机会中的正面因素，对风险持乐观态度。所有分析内容仅供学习研究参考，不构成任何投资建议。
```

**USER_TEMPLATE**:
```
根据以下交易建议：{trader_plan}

请从激进角度评估这笔交易的风险收益比。重点阐述：1)为什么这笔交易值得冒险 2)潜在的巨大收益空间 3)风险被高估的可能性 4)最佳的激进入场策略。
```

**变量注入**: `trader_plan`(交易员完整输出)

**调用**: `stream_chat(history_messages=messages, temperature=0.5, max_tokens=4096)`

---

### 10. 保守风险分析师 (safe_debator)

**文件**: `backend/app/infrastructure/workflow/prompts/stock_analysis/safe_debator.py`

**SYSTEM_PROMPT**:
```
你是一位保守的风险分析师。你倾向于强调风险和不确定性，对投资建议持谨慎态度。所有分析内容仅供学习研究参考，不构成任何投资建议。
```

**USER_TEMPLATE**:
```
根据以下交易建议：{trader_plan}

请从保守角度评估这笔交易的风险。重点阐述：1)可能出错的地方 2)最大的下行风险 3)被忽略的危险信号 4)保守的安全策略建议。
```

**调用**: `stream_chat(history_messages=messages, temperature=0.5, max_tokens=4096)`

---

### 11. 中立风险分析师 (neutral_debator)

**文件**: `backend/app/infrastructure/workflow/prompts/stock_analysis/neutral_debator.py`

**SYSTEM_PROMPT**:
```
你是一位中立的风险分析师。你平衡看待风险和收益，追求客观公正的评估。所有分析内容仅供学习研究参考，不构成任何投资建议。
```

**USER_TEMPLATE**:
```
根据以下激进观点：{risky_view}

和保守观点：{safe_view}

请从中立角度综合评估：1)激进和保守观点各自的可取之处 2)实际风险可能在哪里 3)最合理的风险应对策略 4)给投资者的平衡建议。
```

**调用**: `stream_chat(history_messages=messages, temperature=0.5, max_tokens=4096)`

---

### 12. 风险裁决 (risk_judge) ⭐深度模型

**文件**: `backend/app/infrastructure/workflow/prompts/stock_analysis/risk_judge.py`

**SYSTEM_PROMPT**:
```
你是一位最终风险裁决者。你需要综合所有风险观点，给出最终的风险评估和裁决。你必须非常谨慎和客观。所有分析内容仅供学习研究参考，不构成任何投资建议。
```

**USER_TEMPLATE**:
```
根据以下所有分析：

激进观点：{risky_view}

保守观点：{safe_view}

中立观点：{neutral_view}

请给出最终风险裁决：1)综合风险等级（低/中/高）2)最大风险点 3)风险收益比评分(0-100) 4)最终投资建议 5)关键监控指标。请用以下JSON格式输出：
```json
{"action": "买入/持有/卖出", "target_price": 数字, "confidence": 0-100, "risk_score": 0-100, "reasoning": "最终决策理由"}
```
```

**调用**: `stream_chat(history_messages=messages, model=settings.llm_deep_model, temperature=0.2, max_tokens=4096)`

---

### 13. 信号提取 (signal_extractor)

**文件**: `backend/app/infrastructure/workflow/prompts/stock_analysis/signal_extractor.py`

**SYSTEM_PROMPT**:
```
你是一位数据提取专家。从风险裁决中提取结构化的交易信号。所有分析内容仅供学习研究参考，不构成任何投资建议。
```

**USER_TEMPLATE**:
```
请从以下文本中提取结构化交易信号：{risk_judgment_text}

请用以下JSON格式输出：
```json
{"action": "买入/持有/卖出", "target_price": 数字, "confidence": 0-100, "risk_score": 0-100, "reasoning": "简短决策理由"}
```
```

**调用**: `stream_chat(history_messages=messages, temperature=0.1, max_tokens=1024)`

---

### 附加: 快速决策 (quick_decision, quick模式专用)

**文件**: `backend/app/infrastructure/workflow/nodes/quick_decision_node.py`

**SYSTEM_PROMPT**: 复用 `signal_extractor.py` 的 SYSTEM_PROMPT

**USER_TEMPLATE** (内联定义):
```
根据以下分析报告，快速给出简要投资决策：

【技术面分析报告】
{market_report}

【基本面分析报告】
{fundamentals_report}

请直接给出决策，用以下JSON格式输出：
```json
{"action": "买入/持有/卖出", "target_price": 数字, "confidence": 0-100, "risk_score": 0-100, "reasoning": "简短决策理由"}
```
```

**调用**: `stream_chat(history_messages=messages, temperature=0.1, max_tokens=1024)`

---

## 三、数据获取工具集

### 4个 LangChain Tool

| 工具名 | 功能 | 数据源降级链 |
|--------|------|-------------|
| `get_stock_quote` | 实时行情 | MySQL → AKShare全市场缓存(5min) → BaoStock |
| `get_stock_history` | 历史K线 | MySQL → AKShare |
| `get_stock_financial` | 财务指标 | MySQL → AKShare |
| `get_stock_news` | 个股新闻 | AKShare(无降级) |

### 工具调用流程 (以 market_analyst 为例)

```
1. 组装 messages = [system, user]
2. tool_call(messages, tools=4个工具schema, tool_choice="auto")
3. LLM 返回 tool_calls → 执行对应 Python 函数
4. 追加 {role: assistant, tool_calls} + {role: tool, content: JSON结果} 到 messages
5. 重复步骤2-4，最多3次
6. stream_chat(history_messages=messages) → LLM 基于所有上下文生成最终报告
```

---

## 四、LLM API 调用统计

### Full 模式 (一次完整分析)

| 阶段 | API调用次数 | 方法 |
|------|-----------|------|
| 4个分析师 | 4 × (tool_call × 1~3 + stream_chat × 1) = 8~16次 | `tool_call` + `stream_chat` |
| 投资辩论(2轮) | 2 × 2 = 4次 | `stream_chat` |
| 研究管理器 | 1次 | `stream_chat` (deep_model) |
| 交易员 | 1次 | `stream_chat` |
| 风险辩论(2轮) | 2 × 3 = 6次 | `stream_chat` |
| 风险裁决 | 1次 | `stream_chat` (deep_model) |
| 信号提取 | 1次 | `stream_chat` |
| **合计** | **约 19~31 次** | |

### Quick 模式 (快速分析)

| 阶段 | API调用次数 |
|------|-----------|
| 2个分析师(技术+基本面) | 2~6次 tool_call + 2次 stream_chat |
| 快速决策 | 1次 stream_chat |
| **合计** | **约 5~9 次** |

---

## 五、Prompt 组装与发送机制

### 统一模式

所有 Agent 采用相同的 Prompt 组装模式:

```python
# 1. 模板实例化
user_content = USER_TEMPLATE.format(**kwargs)

# 2. 构建消息列表
messages = [
    {"role": "system", "content": SYSTEM_PROMPT},
    {"role": "user", "content": user_content},
]

# 3. 调用 LLM (所有节点统一通过 history_messages 传入)
async for chunk in ai_service.stream_chat(
    system_prompt="",        # 不用（已放入 history_messages）
    user_message="",         # 不用（已放入 history_messages）
    history_messages=messages,
    temperature=X,
    max_tokens=Y,
    model=deep_model_or_none,
):
    if chunk.type == "content":
        full_text += chunk.text
```

### AIService.stream_chat 实际发送的 HTTP 请求

```json
POST {base_url}/chat/completions
{
  "model": "deepseek-chat" 或 settings.llm_deep_model,
  "messages": [
    {"role": "system", "content": "你是一位专业的A股技术面分析师..."},
    {"role": "user", "content": "请分析 贵州茅台(600519)..."},
    ...工具调用中间消息(仅分析师)...
  ],
  "stream": true,
  "temperature": 0.3,
  "max_tokens": 4096
}
```

### JSON 输出解析降级链

```
LLM 响应文本
  → 正则提取 ```json {...} ```
    → json.loads() 成功 → 返回结构化数据
      → 失败 → 正则逐字段提取 (action/target_price/confidence/risk_score)
        → 失败 → 返回默认值 {action:"持有", confidence:0, risk_score:50}
```

---

## 六、SSE 事件类型汇总

| 事件类型 | 数据 | 触发时机 |
|---------|------|---------|
| `agent_status` | {agent, phase, status} | 每个Agent开始/完成 |
| `thinking` | {step, status, message} | 每个Agent开始/完成 |
| `agent_report` | {agent, summary} | 分析师报告生成后 |
| `decision` | {action, target_price, confidence, risk_score, reasoning} | 最终决策 |
| `title` | 标题文本 | AnalysisParser 生成 |
| `summary` | 摘要文本 | AnalysisParser 生成 |
| `industries` | 行业列表 | AnalysisParser 生成 |
| `error` | 错误信息 | 异常/超时 |
| `done` | 空 | 分析完成 |

---

## 七、配置参数

| 参数 | 默认值 | 说明 |
|------|-------|------|
| `llm_model` | 从 .env 读取 | 默认 LLM 模型 |
| `llm_deep_model` | 从 .env 读取 | 深度思考模型(research_manager/risk_judge) |
| `stock_analysis_timeout` | 300s | 个股分析超时 |
| `debate_rounds` | 2 | 投资辩论轮次(实际4次调用) |
| `risk_debate_rounds` | 2 | 风险辩论轮次(实际6次调用) |
| `max_tool_calls` | 3 | 分析师最大工具调用次数 |
| `stock_cache_ttl` | 300s | 股票数据缓存时间 |

---

## 八、持久化状态

| 数据 | 存储位置 | 持久化方式 |
|------|---------|-----------|
| 用户消息 | `t_chat_message` | 自动 |
| AI 完整回复 | `t_chat_message.content` | 自动 |
| 思维链步骤 | `t_chat_message.thinking_steps` (JSON) | 自动 |
| Agent 中间数据 | `t_chat_message.agent_data` (JSON) | 自动 |
| 分析结果文章 | `t_analysis_article` | **需手动保存** |
| 分析结果行业 | `t_article_industry` | 跟随文章保存 |
| 分析结果股票 | `t_article_stock` | 跟随文章保存 |

---

## 九、关键文件索引

| 层次 | 文件路径 | 用途 |
|------|---------|------|
| **Prompt模板** | `backend/app/infrastructure/workflow/prompts/stock_analysis/` | 13个Agent的SYSTEM_PROMPT+USER_TEMPLATE |
| **工作流Graph** | `backend/app/infrastructure/workflow/graph/stock_analysis_graph.py` | LangGraph 图编排 |
| **State定义** | `backend/app/infrastructure/workflow/state/stock_analysis_state.py` | 三层状态(Input/Working/Output) |
| **节点实现** | `backend/app/infrastructure/workflow/nodes/` | 14个节点(含msg_clear) |
| **工具集** | `backend/app/infrastructure/workflow/tools/stock_data_toolkit.py` | 4个数据获取工具 |
| **AI服务** | `backend/app/infrastructure/ai/ai_service.py` | LLM调用封装(httpx) |
| **用例编排** | `backend/app/application/use_cases/stock_analysis_use_case.py` | SSE流式输出+持久化 |
| **DTO** | `backend/app/application/dtos/stock_analysis_dto.py` | 数据传输对象 |
| **解析器** | `backend/app/domain/services/analysis_parser.py` | 标题/摘要/行业提取 |
| **信号提取** | `backend/app/domain/services/signal_extractor.py` | 4层降级信号提取 |
| **Agent类型** | `backend/app/domain/value_objects/agent_type.py` | Agent枚举+显示名+阶段映射 |
| **路由** | `backend/app/routers/chat.py` | SSE入口 |
| **配置** | `backend/app/core/config.py` | 超时/轮次/模型配置 |
