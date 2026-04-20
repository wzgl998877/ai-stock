# Research: Agent 对话式投研助手

**Branch**: `002-agent-chat-refactor` | **Date**: 2026-04-20

## R1: 前端布局方案

**Decision**: 侧边栏（会话列表） + 主区域消息堆叠（ChatGPT 式）

**Rationale**: 用户明确要求：
1. 四个事件类型按钮保留，仍在底部输入栏
2. 主区域从"单次结果"改为"消息列表"（用户消息 + AI 回复纵向堆叠）
3. 左侧新增侧边栏（会话列表，可折叠）
4. 欢迎屏保留（无消息时显示）

布局结构：
```
┌─────────┬──────────────────────────────────┐
│ 侧边栏   │  欢迎屏（无消息时）               │
│ 会话列表  │  或                               │
│          │  消息列表（用户+AI 交替堆叠）        │
│ [新对话]  │    AI 消息含: 思维链(折叠) + 结果   │
│ 会话 1   │                                   │
│ 会话 2   │  ─────────────────────────────── │
│ ...      │  [输入框] [地缘][政策][财报][产业链] │
└─────────┴──────────────────────────────────┘
```

**Alternatives considered**:
- 完全不动页面 → 无法实现多轮对话堆叠
- 新建 ChatPage → 用户明确说不想大幅改动

## R2: Agent 自主决策方案

**Decision**: LangGraph Tool Calling + Conditional Edge

**Rationale**: 让 LLM 自主决定是否调用搜索工具。用户仍然手动选择事件类型（四个按钮），但 Agent 自主决定是否需要搜索补充信息。两者不冲突：
- 用户选"产业链分析" → 确定分析角度
- Agent 判断输入内容 → 决定是否搜索最新信息

**Alternatives considered**:
- 纯规则判断 → 无法处理时事类文本
- 完全自动判断事件类型 → 用户明确要求保留四个按钮

## R3: 多轮对话消息传递方案

**Decision**: AIService 接受完整 messages 数组

**Rationale**: OpenAI API 原生支持。改造方案：
1. `AIService.stream_chat()` 参数从 `(system_prompt, user_message)` 改为 `(messages: list[dict])`
2. UseCase 从 DB 加载历史消息，拼接 messages 数组
3. 超过 10 轮时截断早期消息

## R4: 思维链事件方案

**Decision**: SSE 新增 `thinking` 事件类型

```json
{"type": "thinking", "data": {"step": "classify", "status": "running", "message": "正在判断输入类型..."}}
{"type": "thinking", "data": {"step": "search", "status": "done", "message": "搜索到 3 篇相关报道"}}
```

前端 ThinkingChain 组件在每条 AI 消息内部展示，分析完成后折叠。

## R5: 外部搜索 API 选型

**Decision**: Tavily Search API

**Rationale**: 专为 AI Agent 设计，返回结构化 JSON，免费 1000 次/月。
