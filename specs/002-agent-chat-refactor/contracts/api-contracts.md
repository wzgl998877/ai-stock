# API Contracts: Agent 对话式投研助手

**Branch**: `002-agent-chat-refactor` | **Date**: 2026-04-20

## SSE 事件协议（扩展）

现有 SSE 事件类型保持不变，新增 `thinking` 类型：

| Event Type | Data Type | Description | Status |
|------------|-----------|-------------|--------|
| `thinking` | `{step, status, message}` | 思维链步骤 | **新增** |
| `content` | `str` | 流式文本块 | 已有 |
| `title` | `str` | 分析标题 | 已有 |
| `summary` | `str` | 分析摘要 | 已有 |
| `industries` | `str[]` | 行业列表 | 已有 |
| `error` | `str` | 错误信息 | 已有 |
| `done` | `str` | 完成标记 | 已有 |

### thinking 事件示例

```
data: {"type": "thinking", "data": {"step": "classify", "status": "running", "message": "正在判断输入类型..."}}

data: {"type": "thinking", "data": {"step": "classify", "status": "done", "message": "检测到纯文本输入"}}

data: {"type": "thinking", "data": {"step": "search", "status": "running", "message": "正在搜索相关资讯..."}}

data: {"type": "thinking", "data": {"step": "search", "status": "done", "message": "搜索到 3 篇相关报道"}}
```

## REST API 端点

### 会话管理

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/chat/sessions` | 创建新会话 |
| GET | `/api/chat/sessions` | 列出用户的所有会话 |
| GET | `/api/chat/sessions/{id}` | 获取会话详情（含消息列表） |
| DELETE | `/api/chat/sessions/{id}` | 删除会话 |

### 对话流式分析

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/chat/sessions/{id}/stream` | 在指定会话中发送消息，SSE 流式返回 |

**请求体**:
```json
{
  "content": "美国制裁伊朗对哪些行业有影响",
  "event_type": "supply_chain"
}
```

`event_type` 为可选字段，来自四个按钮的选择。不传时由 Agent 辅助判断。

### 保留的端点（不变）

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/analysis/articles` | 保存分析到知识库 |
| POST | `/api/analysis/similarity` | 相似检测 |
| GET | `/api/analysis/stream` | 保留但标记为 legacy（新流程走 /api/chat/） |

## Request/Response DTOs

### CreateSessionRequest
```python
class CreateSessionRequest(BaseModel):
    title: Optional[str] = None
```

### SessionResponse
```python
class SessionResponse(BaseModel):
    id: str
    title: str
    event_type: Optional[str]
    created_at: str
    updated_at: str
```

### SendMessageRequest
```python
class SendMessageRequest(BaseModel):
    content: str = Field(..., min_length=2, max_length=5000)
    event_type: Optional[str] = None  # 四个按钮选择的值
```

### MessageResponse
```python
class MessageResponse(BaseModel):
    id: str
    role: str  # user / assistant
    content: str
    thinking_steps: Optional[list[dict]] = None
    event_type: Optional[str] = None
    created_at: str
```
