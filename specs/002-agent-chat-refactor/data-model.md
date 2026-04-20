# Data Model: Agent 对话式投研助手

**Branch**: `002-agent-chat-refactor` | **Date**: 2026-04-20

## Entity Changes

### ChatSession（已定义，需补充字段）

| Field | Type | Description | Status |
|-------|------|-------------|--------|
| session_id | str(32) | UUID 主键 | 已有 |
| user_id | str(32) | 用户 ID | 已有 |
| title | str(100) | 会话标题（首条消息自动生成） | 已有 |
| event_type | str(20) | 当前分析事件类型（可选） | **新增** |
| messages | List[ChatMessage] | 会话消息列表 | 已有 |
| create_time | datetime | 创建时间 | 已有 |
| update_time | datetime | 更新时间 | 已有 |
| deleted | str | 软删除 | 已有 |

### ChatMessage（已定义，需补充字段）

| Field | Type | Description | Status |
|-------|------|-------------|--------|
| message_id | str(32) | UUID 主键 | 已有 |
| session_id | str(32) | 所属会话 | 已有 |
| role | enum(user/assistant) | 角色 | 已有 |
| content | text | 消息正文（Markdown） | 已有 |
| thinking_steps | JSON | 思维链步骤数组 | **新增** |
| event_type | str(20) | 本条分析的事件类型 | **新增** |
| create_time | datetime | 创建时间 | 已有 |
| deleted | str | 软删除 | 已有 |

### ThinkingStep（嵌入 ChatMessage.thinking_steps，非独立表）

| Field | Type | Description |
|-------|------|-------------|
| step | str | 步骤标识（classify/search/retrieve/reasoning） |
| status | str | running / done / failed |
| message | str | 展示给用户的文字 |

## State Transitions

### ChatSession 生命周期

```
创建 → 活跃（追加消息） → 归档（不删除，可恢复）
```

### ChatMessage 创建时机

```
用户发送 → 立即创建 role=user 的消息（持久化）
AI 回复完成 → 创建 role=assistant 的消息（持久化，含 thinking_steps）
AI 回复中断 → 仍创建 role=assistant 的消息（保留已输出内容）
```

## Validation Rules

- ChatMessage.content: user 消息 ≥ 2 字符，≤ 5000 字符
- ChatMessage.role: 只允许 "user" 或 "assistant"
- ChatSession.title: 自动从首条 user 消息截取前 20 字
- thinking_steps: JSON 数组，每个元素必须有 step + status + message
