# Tasks: AI 事件分析 & 行业知识库

**Input**: Design documents from `/specs/001-ai-event-analysis/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: 本规格未要求测试驱动开发，因此不生成测试任务。如需测试，可后续补充。

**Organization**: 任务按 User Story 分组，支持独立实现和独立测试。

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 可并行执行（不同文件，无依赖）
- **[Story]**: 任务所属用户故事（US1, US2, US3 等）
- 描述中包含精确文件路径

## Path Conventions

- **后端**: `backend/app/` (DDD 分层: routers → application → domain → infrastructure)
- **前端**: `frontend/src/` (分层: pages → application → services)
- 路径基于 plan.md 中的项目结构

---

## Phase 1: Setup (项目初始化)

**Purpose**: 创建项目骨架、安装依赖、配置基础设施

- [ ] T001 Create project directory structure per plan.md (backend/app/ with routers, application, domain, infrastructure, schemas, core; frontend/src/ with pages, application, domain, services, store, components, utils)
- [ ] T002 [P] Initialize backend Python project with FastAPI dependencies and create requirements.txt in backend/
- [ ] T003 [P] Initialize frontend React + TypeScript project with Ant Design 5, Zustand, ECharts, react-markdown in frontend/
- [ ] T004 [P] Create Docker Compose configuration for MySQL 8 + Redis 7 in docker-compose.yml
- [ ] T005 [P] Create .env.example with all required environment variables in backend/.env.example

**Checkpoint**: 项目骨架就绪，`docker compose up` 可启动 MySQL 和 Redis

---

## Phase 2: Foundational (阻塞性前置条件)

**Purpose**: 所有 User Story 共享的核心基础设施，必须在任何 US 工作开始前完成

**⚠️ CRITICAL**: 此阶段未完成前，任何 User Story 工作不能开始

- [ ] T006 Implement core configuration module with Pydantic Settings in backend/app/core/config.py
- [ ] T007 [P] Implement dependency injection wiring in backend/app/core/deps.py (DB session, Redis, LLM service)
- [ ] T008 [P] Create FastAPI main app with CORS middleware and router registration in backend/app/main.py
- [ ] T009 [P] Define EventType enum (geopolitical/policy/earnings/supply_chain/other) in backend/app/domain/value_objects/event_type.py
- [ ] T010 [P] Define IndustryTag value object with Shenwan 31 industries data in backend/app/domain/value_objects/industry_tag.py
- [ ] T011 [P] Define AnalysisArticle domain entity with all fields per data-model.md in backend/app/domain/entities/article.py
- [ ] T012 [P] Create SQLAlchemy ORM models for AnalysisArticle, ArticleIndustry, EventReminder with indexes per data-model.md in backend/app/infrastructure/db/models.py
- [ ] T013 Create Alembic configuration and initial migration for all tables in backend/alembic/
- [ ] T014 [P] Define article repository interface in backend/app/domain/repositories/article_repo.py
- [ ] T015 [P] Define search repository interface in backend/app/domain/repositories/search_repo.py
- [ ] T016 [P] Implement LLM service abstraction layer with streaming support in backend/app/infrastructure/ai/llm_service.py
- [ ] T017 [P] Create 5 prompt template modules (geopolitical.py, policy.py, earnings.py, supply_chain.py, general.py) in backend/app/infrastructure/ai/prompts/
- [ ] T018 [P] Create frontend domain types (AnalysisArticle, EventType, IndustryTag, StockReference, etc.) in frontend/src/domain/types.ts
- [ ] T019 [P] Create frontend constants (event type labels, Shenwan 31 industry list, preset example questions) in frontend/src/domain/constants.ts
- [ ] T020 [P] Create frontend HTTP request utility with error handling and SSE parsing in frontend/src/services/request.ts

**Checkpoint**: 基础设施就绪 — 后端可启动（无路由报错），数据库可迁移，前端可编译

---

## Phase 3: User Story 1 - AI 事件分析（核心流程）(Priority: P1) 🎯 MVP

**Goal**: 用户选择事件类型、输入事件描述，系统以 SSE 流式返回结构化 AI 分析结果，3秒内显示首段文字

**Independent Test**: 输入任意事件描述，获取并展示完整的结构化流式分析结果

### Implementation for User Story 1

- [ ] T021 [P] [US1] Define analysis request/response Pydantic schemas (StreamRequest, ArticleMeta, StreamChunk) in backend/app/schemas/analysis.py
- [ ] T022 [US1] Implement SSE streaming analysis use case with retry logic (max 2 retries, 5s interval) in backend/app/application/analysis_app.py
- [ ] T023 [US1] Implement analysis router with POST /api/analysis/stream SSE endpoint in backend/app/routers/analysis.py
- [ ] T024 [P] [US1] Create analysis API service with fetch+ReadableStream SSE parsing in frontend/src/services/analysisService.ts
- [ ] T025 [P] [US1] Create analysis Zustand store managing analysis state (idle/streaming/complete/error), task persistence across page switches in frontend/src/store/analysisStore.ts
- [ ] T026 [P] [US1] Create analysis application use case orchestrating service calls and store updates in frontend/src/application/analysisApp.ts
- [ ] T027 [US1] Build analysis page layout with event type selector (5 buttons) and input area in frontend/src/pages/Analysis/index.tsx
- [ ] T028 [US1] Build streaming result display component with Markdown rendering, 6/7 section structure, loading spinner in frontend/src/pages/Analysis/components/StreamResult.tsx
- [ ] T029 [US1] Implement draft auto-save to localStorage (≥20 chars trigger) with page refresh recovery in frontend/src/pages/Analysis/components/DraftInput.tsx

**Checkpoint**: 用户可完成「选类型 → 输入 → 实时查看流式分析结果」，切换页面后分析不中断，草稿自动保存

---

## Phase 4: User Story 2 - 保存到行业知识库 (Priority: P1)

**Goal**: 用户可查看 AI 生成的标题/摘要，确认行业标签后保存到知识库，或选择不保存

**Independent Test**: 对已有分析结果执行保存/丢弃操作，验证标题、摘要、正文、行业标签一并持久化

### Implementation for User Story 2

- [ ] T030 [P] [US2] Implement article repository with MySQL CRUD operations in backend/app/infrastructure/repositories/article_repo_impl.py
- [ ] T031 [US2] Add save article use case (extract tags, validate ≥1 industry, persist article + associations) to backend/app/application/analysis_app.py
- [ ] T032 [US2] Add POST /api/analysis/articles endpoint with 400 error handling (NO_INDUSTRY_TAG, EMPTY_CONTENT) to backend/app/routers/analysis.py
- [ ] T033 [US2] Build save confirmation panel showing editable AI-generated title (≤15 chars) and summary (≤80 chars) in frontend/src/pages/Analysis/components/SavePanel.tsx
- [ ] T034 [US2] Build industry tag editor component with add/delete functionality, minimum 1 tag validation, "未分类" fallback in frontend/src/pages/Analysis/components/TagEditor.tsx
- [ ] T035 [US2] Add save/discard action flow with success toast "已保存，关联了X个行业" to frontend/src/application/analysisApp.ts

**Checkpoint**: 分析完成后可编辑标题/摘要、确认行业标签、保存到知识库；US1+US2 形成完整的分析→保存闭环

---

## Phase 5: User Story 3 - 知识库浏览与搜索 (Priority: P1)

**Goal**: 用户以行业、时间线、股票三种视图浏览知识库，支持全文搜索和文章详情查看

**Independent Test**: 保存若干篇文章后，分别用三种视图浏览和关键词搜索来完整验证

### Implementation for User Story 3

- [ ] T036 [P] [US3] Define knowledge DTOs (ArticleListItem, ArticleDetail, IndustryInfo, StockInfo, SearchResult) in backend/app/schemas/knowledge.py
- [ ] T037 [P] [US3] Implement MySQL fulltext search with ngram parser and highlight extraction in backend/app/infrastructure/search/fulltext_search.py
- [ ] T038 [P] [US3] Implement search repository with fulltext query, industry filter, stock filter in backend/app/infrastructure/repositories/search_repo_impl.py
- [ ] T039 [US3] Implement knowledge application use cases (list articles, get detail, delete, search, get industries, get watchlist stocks) in backend/app/application/knowledge_app.py
- [ ] T040 [US3] Implement knowledge router with GET/DELETE articles, GET industries, GET watchlist-stocks, GET search endpoints in backend/app/routers/knowledge.py
- [ ] T041 [P] [US3] Create knowledge API service in frontend/src/services/knowledgeService.ts
- [ ] T042 [P] [US3] Create knowledge Zustand store managing view mode, filters, pagination, search state in frontend/src/store/knowledgeStore.ts
- [ ] T043 [P] [US3] Create knowledge application use case in frontend/src/application/knowledgeApp.ts
- [ ] T044 [US3] Build knowledge page with three-view tab switcher (行业/时间线/股票) and search bar in frontend/src/pages/Knowledge/index.tsx
- [ ] T045 [US3] Build industry view component: left panel with industry list + article counts, right panel with article cards in frontend/src/pages/Knowledge/components/IndustryView.tsx
- [ ] T046 [US3] Build timeline view component: date-sorted article card list with pagination in frontend/src/pages/Knowledge/components/TimelineView.tsx
- [ ] T047 [US3] Build stock view component: left panel with watchlist stocks + article counts, right panel with filtered articles in frontend/src/pages/Knowledge/components/StockView.tsx
- [ ] T048 [US3] Build search result component with keyword highlighting in frontend/src/pages/Knowledge/components/SearchResults.tsx
- [ ] T049 [US3] Build article detail drawer/modal with full Markdown content and clickable stock codes in frontend/src/pages/Knowledge/components/ArticleDetail.tsx

**Checkpoint**: US1+US2+US3 形成完整的「分析→保存→浏览→搜索」核心闭环，P1 功能全部可用

---

## Phase 6: User Story 4 - 相似问题检测 (Priority: P2)

**Goal**: 用户输入新问题时，系统自动检测知识库中的相似历史文章并给出非阻断式提示

**Independent Test**: 先保存若干文章，然后输入相似问题触发检测验证

### Implementation for User Story 4

- [ ] T050 [P] [US4] Implement Jaccard similarity detection domain service based on title+summary+tags keyword overlap in backend/app/domain/services/similarity.py
- [ ] T051 [US4] Add POST /api/analysis/similarity endpoint returning top_k similar articles with similarity scores to backend/app/routers/analysis.py
- [ ] T052 [US4] Implement debounced input watcher (1s delay) triggering similarity check via analysis service in frontend/src/application/analysisApp.ts
- [ ] T053 [US4] Build similar articles suggestion card component showing "X个月前分析过类似问题 →《XXX》，要对比吗？" in frontend/src/pages/Analysis/components/SimilarCard.tsx

**Checkpoint**: 用户输入问题时自动检测相似文章，点击提示卡可查看历史文章且不影响当前输入

---

## Phase 7: User Story 5 - 大事提醒 (Priority: P2)

**Goal**: 用户手动录入未来重要事件日期，系统在3天前和当天提醒，支持一键触发 AI 分析

**Independent Test**: 添加提醒、等待提醒触发、一键分析来独立验证

### Implementation for User Story 5

- [ ] T054 [P] [US5] Define ReminderStatus enum and EventReminder domain entity per data-model.md in backend/app/domain/entities/reminder.py
- [ ] T055 [P] [US5] Define reminder Pydantic schemas (CreateReminderRequest, ReminderResponse, UnreadCount) in backend/app/schemas/reminder.py
- [ ] T056 [P] [US5] Define reminder repository interface in backend/app/domain/repositories/reminder_repo.py
- [ ] T057 [P] [US5] Implement reminder repository with MySQL CRUD, status filtering, and date-range queries in backend/app/infrastructure/repositories/reminder_repo_impl.py
- [ ] T058 [US5] Implement reminder application use cases (create with duplicate check, list, update, delete, trigger-analysis) in backend/app/application/reminder_app.py
- [ ] T059 [US5] Implement APScheduler daily job to check 3-day-ahead and today reminders, update status, cache unread count to Redis in backend/app/application/reminder_app.py (extend) + register in backend/app/main.py
- [ ] T060 [US5] Implement reminder router with GET/POST/PUT/DELETE reminders, GET unread-count, POST trigger-analysis endpoints in backend/app/routers/reminder.py
- [ ] T061 [P] [US5] Create reminder API service in frontend/src/services/reminderService.ts
- [ ] T062 [P] [US5] Create reminder application use case in frontend/src/application/reminderApp.ts
- [ ] T063 [US5] Build reminder management page with future events list (date ascending) and archived section in frontend/src/pages/Reminder/index.tsx
- [ ] T064 [US5] Add reminder notification badge (bell icon with red dot count) in global header component in frontend/src/components/Header.tsx

**Checkpoint**: 用户可添加/编辑/删除提醒，铃铛显示未读数，到期自动提醒，可一键触发分析

---

## Phase 8: User Story 6 - 新用户引导 (Priority: P3)

**Goal**: 首次使用用户看到3个预置示例问题，点击即可体验完整分析流程

**Independent Test**: 清空用户数据模拟首次登录，验证引导流程显示和隐藏

### Implementation for User Story 6

- [ ] T065 [US6] Build onboarding preset examples component showing 3 example questions (geopolitical/policy/earnings) below input area, auto-filling on click in frontend/src/pages/Analysis/components/OnboardingGuide.tsx
- [ ] T066 [US6] Add guide visibility state management (show when articles=0, hide after first analysis complete) to frontend/src/store/analysisStore.ts

**Checkpoint**: 首次登录用户看到示例引导，完成一次分析后引导永久隐藏

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: 影响多个 User Story 的收尾工作

- [ ] T067 [P] Add "不构成投资建议" disclaimer banner to analysis result and article detail pages
- [ ] T068 [P] Add cross-module stock code click navigation (knowledge → module 2 stock detail) in frontend/src/pages/Knowledge/components/ArticleDetail.tsx
- [ ] T069 Handle edge cases: AI format anomaly graceful degradation, search no-results state, network error toast, 120s timeout with cancel option in backend and frontend
- [ ] T070 Run quickstart.md validation: verify backend startup, frontend startup, database migration, Docker Compose end-to-end

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: 无依赖 — 立即开始
- **Foundational (Phase 2)**: 依赖 Phase 1 完成 — 阻塞所有 User Story
- **US1 (Phase 3)**: 依赖 Phase 2 完成 — MVP 核心
- **US2 (Phase 4)**: 依赖 Phase 3 完成（需要分析结果才能保存）
- **US3 (Phase 5)**: 依赖 Phase 4 完成（需要有保存的文章才能浏览搜索）
- **US4 (Phase 6)**: 依赖 Phase 3 完成（需要分析输入框）；最好 Phase 5 完成后（需要知识库数据）
- **US5 (Phase 7)**: 依赖 Phase 2 完成 — 独立于 US1-US4，可并行开发
- **US6 (Phase 8)**: 依赖 Phase 3 完成（需要分析页面）
- **Polish (Phase 9)**: 所有期望的 US 完成后执行

### User Story Dependencies

- **US1 (P1)**: Phase 2 后可开始 — 无其他 Story 依赖
- **US2 (P1)**: 依赖 US1（分析结果展示）
- **US3 (P1)**: 依赖 US2（需要知识库有数据）
- **US4 (P2)**: 依赖 US1（输入框）+ 建议依赖 US3（知识库数据）
- **US5 (P2)**: 仅依赖 Phase 2 — 完全独立，可与 US1-US4 并行
- **US6 (P3)**: 依赖 US1（分析页面）

### Within Each User Story

- Domain entities/value objects 先于 services
- Repository implementations 先于 application use cases
- Application use cases 先于 routers (后端) / pages (前端)
- Core implementation 先于 integration

### Parallel Opportunities

- Phase 1: T002, T003, T004, T005 可并行
- Phase 2: T007-T020 大部分可并行（除 T006 和 T013 有顺序依赖）
- Phase 5 (US3): T036-T038 后端搜索相关可并行；T041-T043 前端服务层可并行
- Phase 7 (US5): T054-T057 后端领域层可并行；T061-T062 前端服务层可并行
- US5 整个 Phase 可与 US1-US4 并行开发

---

## Parallel Example: Phase 2 (Foundational)

```bash
# 串行前置:
Task: "T006 Implement core configuration module"
Task: "T008 Create FastAPI main app"

# 可并行启动:
Task: "T009 Define EventType enum"
Task: "T010 Define IndustryTag value object"
Task: "T011 Define AnalysisArticle entity"
Task: "T012 Create ORM models"
Task: "T014 Define article repository interface"
Task: "T015 Define search repository interface"
Task: "T016 Implement LLM service abstraction"
Task: "T017 Create prompt templates"
Task: "T018 Create frontend domain types"
Task: "T019 Create frontend constants"
Task: "T020 Create frontend HTTP utility"
```

## Parallel Example: User Story 1

```bash
# 串行前置 (后端):
Task: "T021 Define analysis DTOs"
Task: "T022 Implement SSE streaming analysis use case"
Task: "T023 Implement analysis router"

# 可并行启动 (前端):
Task: "T024 Create analysis API service"
Task: "T025 Create analysis Zustand store"
Task: "T026 Create analysis application use case"
```

## Parallel Example: User Story 3 (后端 + 前端并行)

```bash
# 后端可并行:
Task: "T036 Define knowledge DTOs"
Task: "T037 Implement fulltext search"
Task: "T038 Implement search repository"

# 前端可并行:
Task: "T041 Create knowledge API service"
Task: "T042 Create knowledge Zustand store"
Task: "T043 Create knowledge application use case"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — 阻塞所有 Story)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: 测试 US1 独立运行 — 用户可完成完整的流式分析体验
5. 可部署/演示

### Core Loop (P1 Stories)

1. Setup + Foundational → 基础就绪
2. US1 → 流式分析 ✅ (MVP!)
3. US2 → 分析+保存闭环 ✅
4. US3 → 分析+保存+浏览搜索闭环 ✅ (P1 全部完成)
5. 每个 Story 增量交付，不破坏已有功能

### Full Feature

1. Core Loop (P1)
2. US4 → 相似检测 ✅
3. US5 → 大事提醒 ✅ (可与 P1 并行)
4. US6 → 新用户引导 ✅
5. Polish → 收尾

### Parallel Team Strategy

多个开发者时:

1. 团队共同完成 Setup + Foundational
2. Foundational 完成后:
   - Developer A: US1 → US2 → US3 (P1 核心链路，串行)
   - Developer B: US5 (完全独立，可并行)
3. P1 完成后:
   - Developer A: US4 → US6
   - Developer B: Polish
4. 各 Story 独立完成和集成

---

## Notes

- [P] 标记 = 不同文件，无依赖，可并行执行
- [Story] 标签将任务映射到特定 User Story，便于追踪
- 每个 User Story 应可独立完成和测试
- 每个任务或逻辑组完成后提交 commit
- 在任何 Checkpoint 处停下来验证独立 Story 的完整性
- 避免：模糊任务、同文件冲突、破坏独立性的跨 Story 依赖
- 后端严格遵循 DDD 分层: Router → Application → Domain → Infrastructure
- 前端严格遵循: Page → Application → Service，页面不直连 API
- 大模型调用通过统一抽象层，业务层不直连
