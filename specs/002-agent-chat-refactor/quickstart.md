# Quickstart: Agent 对话式投研助手

**Branch**: `002-agent-chat-refactor` | **Date**: 2026-04-20

## 页面布局（最终确认）

```
┌───────────┬───────────────────────────────────────┐
│  侧边栏    │  欢迎屏（无消息时居中，保留原样式）      │
│  会话列表   │  或                                    │
│            │  消息列表（用户 + AI 交替堆叠，像 ChatGPT）│
│  [新对话]   │    AI 消息含: 思维链(可折叠) + Markdown  │
│  会话 1 ←  │    + [保存到知识库] 按钮                  │
│  会话 2    │                                       │
│  会话 3    │  ───────────────────────────────────── │
│            │  [输入框]                               │
│            │  [地缘政治] [政策法规] [财报季报] [产业链] │
└───────────┴───────────────────────────────────────┘
```

**保留不变的组件**：
- EventTypeSelector（四个事件类型按钮）
- AnalysisInput 样式（底部输入框外观）
- 保存到知识库功能（每条 AI 消息底部）
- 欢迎屏标题和布局

**需要改造的组件**：
- AnalysisResult → 消息列表（多条消息纵向堆叠）
- analysisStore → chatStore（管理消息数组而非单个结果）

## 开发顺序

### Phase 1: 后端对话基础设施（P1）

1. 实现 `MySQLChatRepository`（已有接口定义，只写实现）
2. 修改 `ChatMessage` 实体和 ORM 模型（新增 thinking_steps, event_type）
3. 新增 `routers/chat.py`（会话 CRUD + 流式对话）
4. 改造 `AIService.stream_chat()` 支持 messages 数组
5. 新增 `ChatUseCase`（加载历史消息 + 调用 LangGraph + 流式输出）

### Phase 2: 前端消息列表（P1）

6. 新增 `chatStore`（替代 analysisStore，管理消息数组）
7. 新增 `chatService`（API 调用层）
8. 改造 AnalysisPage：
   - 外层包侧边栏（SessionSidebar 组件）
   - 主区域改为消息列表（MessageList + MessageBubble）
   - 保留底部输入栏 + 四个按钮
   - 欢迎屏保留（无消息时显示）

### Phase 3: 思维链展示（P2）

9. 后端：LangGraph 节点 yield thinking 事件
10. 前端：ThinkingChain 组件（在每条 AI 消息内展示）

### Phase 4: Agent 自主搜索（P3）

11. 集成 Tavily Search API
12. LangGraph classify 节点改为 LLM tool calling
13. 新增 web_search tool

### Phase 5: 会话管理 UI（P4）

14. SessionSidebar 组件（会话列表、新建、切换、删除）
15. 刷新页面后会话恢复

## 关键文件变更地图

### 后端新建
```
infrastructure/repositories/mysql_chat_repo.py
routers/chat.py
application/dtos/chat_dto.py
application/use_cases/chat_use_case.py
workflow/nodes/agent_classify.py
workflow/tools/web_search.py
```

### 后端修改
```
infrastructure/ai/ai_service.py        → 支持 messages 数组
infrastructure/db/models.py            → ChatMessage 增加字段
domain/entities/chat_session.py        → 新增 event_type
domain/entities/chat_message.py        → 新增 thinking_steps, event_type
main.py                                → 注册 chat 路由
requirements.txt                       → 新增 tavily-python
```

### 前端新建
```
store/chatStore.ts                      → 消息数组状态管理
services/chatService.ts                 → Chat API 调用
components/chat/MessageList.tsx         → 消息列表
components/chat/MessageBubble.tsx       → 单条消息气泡
components/chat/ThinkingChain.tsx       → 思维链折叠展示
components/chat/SessionSidebar.tsx      → 侧边栏会话列表
```

### 前端修改
```
pages/AnalysisPage.tsx                  → 包侧边栏 + 主区域改消息列表
domain/types.ts                         → 新增 thinking 事件类型、消息类型
```

### 前端可能废弃
```
components/analysis/AnalysisResult.tsx  → 被 MessageBubble 替代
store/analysisStore.ts                  → 被 chatStore 替代
hooks/useSSE.ts                         → 逻辑合并到 chatStore
```

## 新增依赖

```
# 后端
tavily-python>=0.5,<1.0

# 前端（无新增）
```
