# Tasks: Agent 对话式投研助手

**Input**: Design documents from `/specs/002-agent-chat-refactor/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: 新增依赖、扩展实体和 ORM 模型

- [x] T001 修改 ChatSession 实体，新增 event_type 字段 in `backend/app/domain/entities/chat_session.py`
- [x] T002 [P] 修改 ChatMessage 实体，新增 thinking_steps(JSON) 和 event_type 字段 in `backend/app/domain/entities/chat_message.py`
- [x] T003 [P] 修改 ORM 模型，ChatMessage 增加 thinking_steps(JSON) 和 event_type 列，ChatSession 增加 event_type 列 in `backend/app/infrastructure/db/models.py`
- [x] T004 生成 Alembic 迁移脚本（新增列）并执行 in `backend/`
- [x] T005 [P] 新增 tavily-python 依赖 in `backend/requirements.txt`
- [x] T006 [P] 新增 Chat DTO（CreateSessionRequest, SessionResponse, SendMessageRequest, MessageResponse） in `backend/app/application/dtos/chat_dto.py`
- [x] T007 [P] 前端新增 Chat 相关类型定义（ChatMessageType, ThinkingStep, ChatSessionType, SSE 新增 thinking 事件类型） in `frontend/src/domain/types.ts`

---

## Phase 2: Foundational

**Purpose**: 后端核心基础设施——Repository、AIService 多轮支持、ChatUseCase

**⚠️ CRITICAL**: 所有 User Story 都依赖此阶段完成

- [x] T008 实现 MySQLChatRepository（create_session, get_session, list_sessions_by_user, delete_session, add_message, list_messages） in `backend/app/infrastructure/repositories/mysql_chat_repo.py`
- [x] T009 改造 AIService.stream_chat()：参数从 `(system_prompt, user_message)` 改为 `(messages: list[dict])`，内部拼接 messages 数组发送给 OpenAI API in `backend/app/infrastructure/ai/ai_service.py`
- [x] T010 实现 ChatUseCase：加载历史消息 → 拼接 messages → 调用 LangGraph → yield SSE 事件（含 thinking）→ 持久化消息 in `backend/app/application/use_cases/chat_use_case.py`
- [x] T011 新增 Chat 路由（POST /api/chat/sessions, GET /api/chat/sessions, GET /api/chat/sessions/{id}, DELETE /api/chat/sessions/{id}, POST /api/chat/sessions/{id}/stream） in `backend/app/routers/chat.py`
- [x] T012 注册 chat 路由到 main.py in `backend/app/main.py`

**Checkpoint**: 后端对话 API 就绪，可以用 curl 测试

---

## Phase 3: User Story 1 - 对话式分析交互 (Priority: P1) 🎯 MVP

**Goal**: ChatGPT 式消息堆叠 + 多轮对话 + 保留四个事件类型按钮

**Independent Test**: 输入问题→看到流式回答→追问一个问题→验证上下文不丢失

### 后端实现

- [ ] T013 [US1] 修改 LangGraph analysis_graph.py：在每个节点执行前后通过 callback yield thinking 事件 in `backend/app/infrastructure/workflow/graph/analysis_graph.py`
- [ ] T014 [US1] 确保 ChatUseCase 支持多轮对话：从 DB 加载 session 历史消息，截断超过 10 轮的早期对话，拼接为 messages 数组传给 AIService in `backend/app/application/use_cases/chat_use_case.py`

### 前端实现

- [ ] T015 [P] [US1] 新增 chatStore（Zustand）：管理 messages 数组、currentSessionId、streaming 状态、thinking 步骤；提供 addMessage/appendContent/addThinkingStep/done 等动作 in `frontend/src/store/chatStore.ts`
- [ ] T016 [P] [US1] 新增 chatService：createSession, listSessions, getSession, deleteSession, streamMessage（SSE 流式） in `frontend/src/services/chatService.ts`
- [ ] T017 [P] [US1] 新增 MessageList 组件：渲染消息数组，用户消息右对齐、AI 消息左对齐，自动滚动到底部 in `frontend/src/components/chat/MessageList.tsx`
- [ ] T018 [P] [US1] 新增 MessageBubble 组件：单条消息气泡，用户消息显示文本，AI 消息渲染 Markdown + 显示保存按钮（isDone 时） in `frontend/src/components/chat/MessageBubble.tsx`
- [ ] T019 [US1] 改造 AnalysisPage：外层 flex 布局加侧边栏占位、主区域从单次结果改为 MessageList、保留欢迎屏（无消息时）、保留底部输入栏 + EventTypeSelector + AnalysisInput、用 chatStore 替代 analysisStore in `frontend/src/pages/AnalysisPage.tsx`

**Checkpoint**: 打开页面→输入问题→看到流式回答→追问→验证消息堆叠和上下文

---

## Phase 4: User Story 2 - 思维链实时展示 (Priority: P2)

**Goal**: AI 分析过程中实时展示每个步骤的执行状态

**Independent Test**: 输入问题→观察思维链步骤按序展示→完成后折叠

### 后端实现

- [ ] T020 [P] [US2] 新增 LangGraph thinking 辅助模块：定义 yield_thinking(step, status, message) 工具函数，供各节点调用 in `backend/app/infrastructure/workflow/nodes/thinking.py`
- [ ] T021 [US2] 修改 classify_node、load_node、retrieve_node：在每个节点入口 yield thinking(running) 事件，完成时 yield thinking(done) 事件 in `backend/app/infrastructure/workflow/nodes/classify.py`, `load.py`, `retrieve.py`
- [ ] T022 [US2] ChatUseCase 中将 thinking 事件包装为 SSE 推送，并在 AI 回复完成后将 thinking_steps 持久化到 ChatMessage in `backend/app/application/use_cases/chat_use_case.py`

### 前端实现

- [ ] T023 [P] [US2] 新增 ThinkingChain 组件：步骤列表（running 显示加载动画、done 显示勾、failed 显示叉）、分析完成后折叠只显示摘要 in `frontend/src/components/chat/ThinkingChain.tsx`
- [ ] T024 [US2] chatStore 处理 thinking SSE 事件类型：收到时追加到当前 AI 消息的 thinkingSteps 数组 in `frontend/src/store/chatStore.ts`
- [ ] T025 [US2] MessageBubble 中集成 ThinkingChain：在 AI 消息的 Markdown 内容上方展示思维链 in `frontend/src/components/chat/MessageBubble.tsx`

**Checkpoint**: 输入问题→看到"正在判断..."、"正在搜索..."等步骤→完成后折叠→显示分析结果

---

## Phase 5: User Story 3 - Agent 自主搜索决策 (Priority: P3)

**Goal**: Agent 自主判断是否需要搜索外部信息（LLM tool calling）

**Independent Test**: 输入时事问题→Agent 自动搜索；输入通用问题→跳过搜索

### 后端实现

- [ ] T026 [P] [US3] 新增 web_search tool：封装 Tavily Search API，返回搜索结果摘要 in `backend/app/infrastructure/workflow/tools/web_search.py`
- [ ] T027 [US3] 新增 agent_classify 节点：替代硬编码 classify_node，使用 LLM function calling 自主决定是否调用 web_search tool in `backend/app/infrastructure/workflow/nodes/agent_classify.py`
- [ ] T028 [US3] 修改 analysis_graph.py：将 classify 节点替换为 agent_classify，添加条件边（需要搜索→web_search→load→retrieve；不需要→load→retrieve） in `backend/app/infrastructure/workflow/graph/analysis_graph.py`
- [ ] T029 [US3] 新增 config.py 配置项：TAVILY_API_KEY in `backend/app/core/config.py`

**Checkpoint**: 输入"美国伊朗最新战争情况"→思维链显示搜索过程→输入"新能源汽车产业链"→可能跳过搜索直接分析

---

## Phase 6: User Story 4 - 会话管理 (Priority: P4)

**Goal**: 侧边栏会话列表、新建/切换/删除、刷新后恢复

**Independent Test**: 新建两个会话→分别对话→切换→刷新→验证恢复

### 前端实现

- [ ] T030 [P] [US4] 新增 SessionSidebar 组件：会话列表、新建按钮、选中高亮、删除按钮、可折叠 in `frontend/src/components/chat/SessionSidebar.tsx`
- [ ] T031 [US4] 改造 AnalysisPage：集成 SessionSidebar，切换会话时从 chatService.getSession 加载历史消息 in `frontend/src/pages/AnalysisPage.tsx`
- [ ] T032 [US4] chatStore 增加会话管理：sessions 列表、currentSessionId、switchSession、loadHistory in `frontend/src/store/chatStore.ts`

**Checkpoint**: 侧边栏显示会话列表→新建会话→切换→刷新页面→历史恢复

---

## Phase 7: Polish & Cross-Cutting Concerns

- [ ] T033 清理废弃文件：标记 analysisStore.ts、useSSE.ts、AnalysisResult.tsx 为废弃或删除
- [ ] T034 [P] 确保原有 `/api/analysis/stream` 端点仍可用（向后兼容）
- [ ] T035 [P] 添加 TAVILY_API_KEY 到 .env.example
- [ ] T036 端到端验证：启动后端→打开前端→完整走通「输入→思维链→流式结果→追问→保存到知识库」流程

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: 无依赖，立即开始
- **Foundational (Phase 2)**: 依赖 Phase 1 完成 — 阻塞所有 User Story
- **US1 (Phase 3)**: 依赖 Phase 2 完成
- **US2 (Phase 4)**: 依赖 US1 完成（ThinkingChain 需要在 MessageBubble 内展示）
- **US3 (Phase 5)**: 依赖 US2 完成（搜索过程通过思维链展示）
- **US4 (Phase 6)**: 依赖 US1 完成（侧边栏依赖消息列表）
- **Polish (Phase 7)**: 依赖所有 User Story 完成

### User Story Dependencies

```
Phase 1 (Setup)
    ↓
Phase 2 (Foundational)
    ↓
Phase 3 (US1: 对话交互) ← MVP
    ↓              ↓
Phase 4 (US2: 思维链)  Phase 6 (US4: 会话管理)
    ↓
Phase 5 (US3: Agent 搜索)
    ↓
Phase 7 (Polish)
```

US2 和 US4 可以并行开发（互不依赖，都只依赖 US1）。

### Parallel Opportunities

- Phase 1: T001, T002, T003, T005, T006, T007 可并行
- Phase 3: T015, T016, T017, T018 可并行
- Phase 4: T020, T023 可并行
- Phase 5: T026 可与 T029 并行
- Phase 6: T030 可独立开发

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1: Setup（实体、ORM、依赖）
2. Phase 2: Foundational（Repository、AIService、ChatUseCase、路由）
3. Phase 3: US1（消息列表 + 多轮对话 + 保留四个按钮）
4. **STOP**: 测试对话交互是否完整可用
5. 此时已有可用的 ChatGPT 式对话体验

### Incremental Delivery

1. Setup + Foundational → 后端 API 就绪
2. + US1 → 对话交互可用（MVP!）
3. + US2 → 思维链展示
4. + US3 → Agent 自主搜索
5. + US4 → 会话管理

---

## Notes

- [P] = 不同文件、无依赖，可并行
- [Story] = 任务归属的用户故事
- 每个 User Story 独立可测试
- 每个 checkpoint 后提交代码
- 保留四个事件类型按钮（EventTypeSelector 不动）
- 保留 AnalysisInput 组件（输入框样式不动）
- 保留保存到知识库功能（每条 AI 消息底部）
