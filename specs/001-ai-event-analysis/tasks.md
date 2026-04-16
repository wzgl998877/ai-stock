
# Tasks: AI 事件分析 & 行业知识库

**Input**: Design documents from `/specs/001-ai-event-analysis/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Web app**: `backend/app/`, `frontend/src/`
- Backend paths relative to `backend/`
- Frontend paths relative to `frontend/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: 前后端项目初始化，基础设施搭建

- [x] T001 创建后端项目结构，初始化 FastAPI 应用入口 in `backend/app/main.py`，创建 `core/config.py`（环境变量管理）、`core/database.py`（MySQL + Redis 连接）、`core/exceptions.py`（统一异常处理）
- [x] T002 [P] 创建后端 requirements.txt，包含 fastapi、uvicorn、sqlalchemy、aiomysql、redis、httpx、pydantic、alembic、apscheduler、jieba 依赖 in `backend/requirements.txt`
- [x] T003 [P] 创建后端 .env.example 环境变量模板（OPENAI_API_KEY、DATABASE_URL、REDIS_URL 等）in `backend/.env.example`
- [x] T004 [P] 创建前端 React + TypeScript 项目（Vite），安装 antd、zustand、react-markdown、axios 依赖 in `frontend/package.json`
- [x] T005 [P] 创建前端目录结构：pages/、components/、application/、domain/、services/、store/、hooks/、utils/ in `frontend/src/`
- [x] T006 [P] 创建前端 axios 实例（baseURL 从环境变量读取，统一错误处理）in `frontend/src/services/api.ts`
- [x] T007 [P] 创建前端 .env.example（VITE_API_BASE_URL）in `frontend/.env.example`
- [x] T008 [P] 创建前端业务类型定义（EventType 枚举、Article、Reminder、StockReference 接口）in `frontend/src/domain/types.ts`
- [x] T009 [P] 创建前端常量文件（申万31个一级行业列表、5种事件类型、预置示例问题）in `frontend/src/domain/constants.ts`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 核心基础设施，所有 User Story 的前置依赖

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T010 创建 SQLAlchemy ORM 模型（10 张表：t_user、t_industry、t_stock、t_stock_industry、t_analysis_article、t_article_industry、t_article_stock、t_event_reminder、t_chat_session、t_chat_message），所有表含软删除 `deleted` + 审计字段（create_time/update_time/create_user/update_user）in `backend/app/infrastructure/db/models.py`
- [x] T011 创建 Alembic 迁移配置和初始迁移脚本（10 张表 DDL，含 t_analysis_article 上的 FULLTEXT ngram 索引）in `backend/app/infrastructure/db/migrations/`
- [x] T012 [P] 创建 Domain 实体：Article 实体 in `backend/app/domain/entities/article.py`，Reminder 实体 in `backend/app/domain/entities/reminder.py`，User 实体 in `backend/app/domain/entities/user.py`，Industry 实体 in `backend/app/domain/entities/industry.py`，Stock 实体 in `backend/app/domain/entities/stock.py`，ChatSession 实体 in `backend/app/domain/entities/chat_session.py`，ChatMessage 实体 in `backend/app/domain/entities/chat_message.py`
- [x] T013 [P] 创建 Domain 值对象：EventType 枚举 in `backend/app/domain/value_objects/event_type.py`，IndustryTag in `backend/app/domain/value_objects/industry_tag.py`，ReminderStatus（4 状态：pending/reminded_3day/reminded_today/archived）in `backend/app/domain/value_objects/reminder_status.py`
- [x] T014 [P] 创建 Domain Repository 接口定义：ArticleRepository in `backend/app/domain/repositories/article_repo.py`（save 需同步写入 t_article_industry + t_article_stock），SearchRepository in `backend/app/domain/repositories/search_repo.py`，ReminderRepository in `backend/app/domain/repositories/reminder_repo.py`，IndustryRepository in `backend/app/domain/repositories/industry_repo.py`（按层级查询、按 code 查询），StockRepository in `backend/app/domain/repositories/stock_repo.py`（按代码/名称查询），ChatRepository in `backend/app/domain/repositories/chat_repo.py`（session + message CRUD）
- [x] T015 [P] 创建申万行业种子数据 SQL（含一级31个行业 + 二三级预留，INSERT 到 t_industry）in `backend/app/data/seed_industries.sql`
- [x] T016 创建 Infrastructure 层 Repository 实现：MySQLArticleRepository in `backend/app/infrastructure/repositories/mysql_article_repo.py`（save 同步写入 t_article_industry + t_article_stock 关联表、get_by_id、list、软删除 delete、get_by_industry 通过 JOIN t_article_industry、get_by_stock 通过 JOIN t_article_stock）
- [x] T017 [P] 创建 MySQLSearchRepository（FULLTEXT + ngram 搜索 t_analysis_article，支持行业通过 JOIN t_article_industry、股票通过 JOIN t_article_stock 筛选）in `backend/app/infrastructure/repositories/mysql_search_repo.py`
- [x] T018 [P] 创建 MySQLReminderRepository（CRUD + 按状态/日期查询，状态含 4 阶段：pending/reminded_3day/reminded_today/archived）in `backend/app/infrastructure/repositories/mysql_reminder_repo.py`
- [x] T019 [P] 创建 MySQLIndustryRepository（按层级/parent_code 查询，按 industry_code 查询）in `backend/app/infrastructure/repositories/mysql_industry_repo.py`
- [x] T020 [P] 创建 MySQLChatRepository（session CRUD + message CRUD，按 session_id 查消息列表）in `backend/app/infrastructure/repositories/mysql_chat_repo.py`
- [x] T021 [P] 创建 Domain Service：AnalysisParser（六段/七段结构解析、TITLE/SUMMARY 提取、产业链传导表 Markdown 表格解析、行业代码从 t_industry 匹配、股票代码从 t_stock 匹配）in `backend/app/domain/services/analysis_parser.py`
- [x] T022 [P] 创建 Domain Service：SimilarityCalculator（jieba 分词 + Jaccard 相似度计算）in `backend/app/domain/services/similarity.py`
- [x] T023 创建 AI 服务抽象层（AIService，基于 httpx 流式调用 OpenAI 兼容 API）in `backend/app/infrastructure/ai/ai_service.py`
- [x] T024 [P] 创建 5 种 Prompt 模板：地缘政治 in `backend/app/infrastructure/ai/prompts/geopolicy.py`，政策法规 in `backend/app/infrastructure/ai/prompts/policy.py`，财报季报 in `backend/app/infrastructure/ai/prompts/earnings.py`，产业链分析 in `backend/app/infrastructure/ai/prompts/chain.py`，其他通用 in `backend/app/infrastructure/ai/prompts/general.py`（每个模板导出函数，注入申万行业列表，行业使用名称供 LLM 输出，后端解析时匹配 industry_code）
- [x] T025 [P] 创建后端 DTO：AnalysisRequestDTO、AnalysisArticleDTO、SaveArticleDTO（industry_tags 改为 industry_codes: string[]、mentioned_stocks 改为 stock_refs: [{code, name}]）、SimilarityRequestDTO in `backend/app/application/dtos/analysis_dto.py`；ArticleListDTO、ArticleDetailDTO（含关联的 industries: [{code, name}]、stocks: [{code, name}]）in `backend/app/application/dtos/article_dto.py`；ReminderDTO in `backend/app/application/dtos/reminder_dto.py`；IndustryDTO、StockDTO in `backend/app/application/dtos/common_dto.py`

**Checkpoint**: Foundation ready — 10 张表 ORM + 迁移、Domain 实体（含 User/Industry/Stock/Chat）、Repository 接口/实现（含关联表操作）、AI 服务、Prompt 模板全部就位，可开始 User Story 实现

---

## Phase 3: User Story 1 - AI 事件分析（核心流程）(Priority: P1) 🎯 MVP

**Goal**: 用户选择事件类型、输入事件描述，AI 流式生成六段/七段结构化分析

**Independent Test**: 输入任意事件描述（≥10字），选择事件类型，点击分析，3秒内看到流式输出的结构化分析结果

### Implementation for User Story 1

- [ ] T024 [US1] 创建 Application 用例：AnalyzeEventUseCase（接收 event_type + question，调用 AIService 流式生成，使用 AnalysisParser 解析 TITLE/SUMMARY/industries，通过 SSE 推送，含自动重试逻辑）in `backend/app/application/use_cases/analyze_event.py`
- [ ] T025 [US1] 创建 Router：POST /api/analysis/stream（StreamingResponse SSE 格式，参数校验：question 非空且≥10字）in `backend/app/routers/analysis.py`
- [ ] T026 [P] [US1] 创建前端 Service：analysisService（streamAnalysis — fetch + ReadableStream 解析 SSE，saveArticle，checkSimilarity）in `frontend/src/services/analysisService.ts`
- [ ] T027 [P] [US1] 创建前端 Zustand Store：analysisStore（状态：idle/streaming/done/error，存储 taskId、result、title、summary、industries、error）in `frontend/src/store/analysisStore.ts`
- [ ] T028 [P] [US1] 创建前端 SSE Hook：useSSE（封装 fetch + ReadableStream，按 type 分发事件更新 store）in `frontend/src/hooks/useSSE.ts`
- [ ] T029 [P] [US1] 创建前端草稿 Hook：useDraft（localStorage 自动保存/恢复，>20字触发，防抖1秒）in `frontend/src/hooks/useDraft.ts`
- [ ] T030 [US1] 创建前端 Application：useAnalysis（编排分析流程：参数校验→调用 streamAnalysis→更新 store→重试逻辑）in `frontend/src/application/useAnalysis.ts`
- [ ] T031 [P] [US1] 创建 EventTypeSelector 组件（5种类型按钮组，默认选中「其他」）in `frontend/src/components/analysis/EventTypeSelector.tsx`
- [ ] T032 [P] [US1] 创建 AnalysisInput 组件（TextArea + 草稿自动保存 + 输入校验 + 字数提示）in `frontend/src/components/analysis/AnalysisInput.tsx`
- [ ] T033 [P] [US1] 创建 AnalysisResult 组件（Markdown 实时渲染 + 自动滚动 + 产业链传导表格展示 + "AI正在思考中..."骨架屏）in `frontend/src/components/analysis/AnalysisResult.tsx`
- [ ] T034 [P] [US1] 创建 AnalysisStatusBar 组件（全局状态条，"分析进行中..."/"分析完成，点击查看"）in `frontend/src/components/analysis/AnalysisStatusBar.tsx`
- [ ] T035 [US1] 组装 AnalysisPage 页面（集成 EventTypeSelector + AnalysisInput + AnalysisResult + AnalysisStatusBar，"分析"按钮防重复提交）in `frontend/src/pages/AnalysisPage.tsx`

**Checkpoint**: 可输入事件描述 → 选择类型 → 看到流式分析结果 → 切换页面不影响分析 → 全局状态条通知完成

---

## Phase 4: User Story 2 - 保存到行业知识库 (Priority: P1)

**Goal**: 分析完成后可编辑标题/摘要、确认行业标签、保存到知识库或丢弃

**Independent Test**: 分析完成后点击保存，确认行业标签，验证数据库中文章持久化

**Depends on**: Phase 3 (User Story 1) — 需要分析结果才能保存

### Implementation for User Story 2

- [ ] T036 [US2] 创建 Application 用例：SaveArticleUseCase（接收标题、摘要、正文、industry_codes + stock_refs，校验至少1个行业，调用 ArticleRepository.save 同步写入 t_analysis_article + t_article_industry + t_article_stock，含降级逻辑：摘要为空时截取正文前80字）in `backend/app/application/use_cases/manage_article.py`
- [ ] T037 [US2] 在 analysis.py Router 中添加 POST /api/analysis/articles 保存接口（201 Created，接收 industry_codes + stock_refs，校验 industry_codes 非空）in `backend/app/routers/analysis.py`
- [ ] T038 [US2] 更新 AnalysisPage 页面：分析结果顶部显示可编辑的标题和摘要，底部显示「保存到知识库」和「不保存」按钮，点击保存弹出行业标签确认弹窗（产业链分析按传导层级分组显示）in `frontend/src/pages/AnalysisPage.tsx`
- [ ] T039 [P] [US2] 创建 IndustryTag 组件（标签展示 + 增删交互，产业链分析按层级分组）in `frontend/src/components/common/IndustryTag.tsx`
- [ ] T040 [P] [US2] 创建 StockCodeLink 组件（股票代码高亮可点击，预留跳转模块二路由）in `frontend/src/components/common/StockCodeLink.tsx`

**Checkpoint**: 分析完成 → 编辑标题/摘要 → 确认行业标签 → 保存成功提示"已保存，关联了X个行业" / 不保存直接关闭

---

## Phase 5: User Story 3 - 知识库浏览与搜索 (Priority: P1)

**Goal**: 三种视图浏览知识库（行业/时间线/股票），全文搜索，文章详情查看，股票代码跳转

**Independent Test**: 保存若干篇文章后，分别用三种视图浏览和关键词搜索

**Depends on**: Phase 4 (User Story 2) — 需要已保存的文章数据

### Implementation for User Story 3

- [ ] T041 [US3] 创建 Application 用例：ListArticlesUseCase（三视图查询：timeline 按时间倒序、industry 通过 JOIN t_article_industry 按行业代码筛选、stock 通过 JOIN t_article_stock 按股票代码筛选，分页）+ GetArticleDetailUseCase（含关联查询 industries + stocks）+ DeleteArticleUseCase（软删除）in `backend/app/application/use_cases/manage_article.py`
- [ ] T042 [US3] 创建 Application 用例：SearchArticlesUseCase（调用 SearchRepository 执行 MySQL FULLTEXT 搜索 t_analysis_article，行业通过 JOIN t_article_industry、股票通过 JOIN t_article_stock 筛选，返回分页结果+高亮片段）in `backend/app/application/use_cases/search_articles.py`
- [ ] T043 [US3] 创建 Router：GET /api/knowledge/articles（列表，参数用 industry_code/stock_code）、GET /api/knowledge/articles/{id}（详情，返回关联的 industries + stocks）、DELETE /api/knowledge/articles/{id}（软删除）、GET /api/knowledge/industries（从 t_industry 查询有文章的行业列表）、GET /api/knowledge/watchlist-stocks（从 t_article_stock 查询有文章的股票列表预留）、GET /api/knowledge/search（全文搜索）in `backend/app/routers/knowledge.py`
- [ ] T044 [P] [US3] 创建前端 Service：knowledgeService（getArticles、getArticleDetail、deleteArticle、getIndustries、getWatchlistStocks、searchArticles）in `frontend/src/services/knowledgeService.ts`
- [ ] T045 [P] [US3] 创建前端 Zustand Store：knowledgeStore（视图模式、当前行业/股票、搜索关键词、文章列表、分页）in `frontend/src/store/knowledgeStore.ts`
- [ ] T046 [P] [US3] 创建前端 Application：useKnowledge（视图切换、分页加载、搜索触发）in `frontend/src/application/useKnowledge.ts`
- [ ] T047 [P] [US3] 创建 ArticleCard 组件（三层信息：标题加粗→摘要灰色小字≤80字2行截断→行业标签+日期）in `frontend/src/components/knowledge/ArticleCard.tsx`
- [ ] T048 [P] [US3] 创建 IndustryView 组件（左侧行业列表+文章数量，右侧文章列表）in `frontend/src/components/knowledge/IndustryView.tsx`
- [ ] T049 [P] [US3] 创建 TimelineView 组件（文章按日期倒序排列，日期分组标题）in `frontend/src/components/knowledge/TimelineView.tsx`
- [ ] T050 [P] [US3] 创建 StockView 组件（左侧自选股列表，右侧文章列表，自选股为空时提示"去模块二添加"）in `frontend/src/components/knowledge/StockView.tsx`
- [ ] T051 [P] [US3] 创建 SearchBar 组件（搜索输入框+防抖+关键词高亮+搜索结果展示）in `frontend/src/components/knowledge/SearchBar.tsx`
- [ ] T052 [US3] 组装 KnowledgePage 页面（视图切换 Tab + SearchBar + 对应视图组件 + 分页）in `frontend/src/pages/KnowledgePage.tsx`
- [ ] T053 [US3] 创建 ArticleDetailPage 页面（完整 Markdown 渲染，股票代码高亮可点击跳转，行业标签展示）in `frontend/src/pages/ArticleDetailPage.tsx`

**Checkpoint**: 三种视图切换浏览 → 全文搜索 → 查看文章详情 → 股票代码点击跳转 → 删除文章

---

## Phase 6: User Story 4 - 相似问题检测 (Priority: P2)

**Goal**: 用户输入新问题时，自动检测知识库中的相似历史文章并给出非阻断式提示

**Independent Test**: 先保存若干文章，然后输入相似问题触发检测

**Depends on**: Phase 5 (User Story 3) — 需要知识库中有历史文章

### Implementation for User Story 4

- [ ] T054 [US4] 创建 Application 用例：DetectSimilarUseCase（调用 SimilarityCalculator，jieba 分词 + Jaccard 相似度，阈值≥0.3，知识库为空时返回空列表）in `backend/app/application/use_cases/detect_similar.py`
- [ ] T055 [US4] 在 analysis.py Router 中添加 POST /api/analysis/similarity 接口 in `backend/app/routers/analysis.py`
- [ ] T056 [P] [US4] 创建 SimilarPrompt 组件（输入框下方非阻断式提示卡，显示"你X个月前分析过类似问题→《XXX》，要对比吗？"）in `frontend/src/components/analysis/SimilarPrompt.tsx`
- [ ] T057 [US4] 更新 AnalysisInput 组件：集成相似检测（停止输入1秒后调用 similarity API，显示/隐藏 SimilarPrompt）in `frontend/src/components/analysis/AnalysisInput.tsx`

**Checkpoint**: 输入问题 → 1秒后自动检测 → 显示相似文章提示卡 → 点击查看历史文章 → 不影响当前输入

---

## Phase 7: User Story 5 - 大事提醒 (Priority: P2)

**Goal**: 用户手动添加大事提醒，系统提前3天和当天提醒

**Independent Test**: 添加提醒 → 查看提醒列表 → 提醒触发通知 → 一键触发分析

**Depends on**: Phase 3 (User Story 1) — 提醒触发分析依赖分析功能

### Implementation for User Story 5

- [ ] T058 [US5] 创建 Application 用例：ManageReminderUseCase（创建含重复名称检测、更新、删除软删除、按状态列表（pending/reminded_3day/reminded_today/archived）、未读计数、触发分析预填）in `backend/app/application/use_cases/manage_reminder.py`
- [ ] T059 [US5] 创建 Router：GET /api/reminders、POST /api/reminders、PUT /api/reminders/{id}、DELETE /api/reminders/{id}（软删除）、GET /api/reminders/unread-count、POST /api/reminders/{id}/trigger-analysis in `backend/app/routers/reminder.py`
- [ ] T060 [US5] 创建 APScheduler 定时任务（每日8:00检查：事件前3天将 status 从 pending 更新为 reminded_3day，当天更新为 reminded_today，过期更新为 archived）in `backend/app/infrastructure/scheduler.py`（在 main.py 中注册启动）
- [ ] T061 [P] [US5] 创建前端 Service：reminderService（getReminders、createReminder、updateReminder、deleteReminder、getUnreadCount、triggerAnalysis）in `frontend/src/services/reminderService.ts`
- [ ] T062 [P] [US5] 创建前端 Zustand Store：reminderStore（提醒列表、未读数量、表单状态）in `frontend/src/store/reminderStore.ts`
- [ ] T063 [P] [US5] 创建前端 Application：useReminder（CRUD 操作、未读数轮询、触发分析跳转）in `frontend/src/application/useReminder.ts`
- [ ] T064 [P] [US5] 创建 ReminderList 组件（未来事件列表按日期升序 + 已过期归档区 + 未读铃铛红点）in `frontend/src/components/reminder/ReminderList.tsx`
- [ ] T065 [P] [US5] 创建 ReminderForm 组件（事件名称必填、日期必填、关联行业多选）in `frontend/src/components/reminder/ReminderForm.tsx`
- [ ] T066 [US5] 组装 ReminderPage 页面（ReminderList + ReminderForm + 事件当天弹窗提醒+一键触发分析）in `frontend/src/pages/ReminderPage.tsx`

**Checkpoint**: 添加提醒 → 查看列表 → 铃铛红点 → 弹窗提醒 → 一键触发分析 → 过期自动归档

---

## Phase 8: User Story 6 - 新用户引导 (Priority: P3)

**Goal**: 首次使用时展示3个预置示例问题，降低上手门槛

**Independent Test**: 清空知识库文章，进入分析页，看到示例引导，点击后触发分析

**Depends on**: Phase 3 (User Story 1) — 示例触发完整分析流程

### Implementation for User Story 6

- [ ] T067 [US6] 创建 ExamplePrompts 组件（3个示例问题卡片：地缘政治/政策法规/财报季报各一个，从 constants.ts 读取，点击自动填入并触发分析，完成一次分析后隐藏）in `frontend/src/components/onboarding/ExamplePrompts.tsx`
- [ ] T068 [US6] 更新 AnalysisPage：检测知识库文章数为0时显示 ExamplePrompts，放在 AnalysisInput 下方 in `frontend/src/pages/AnalysisPage.tsx`

**Checkpoint**: 首次使用 → 看到3个示例 → 点击示例 → 自动填入+触发分析 → 完成后引导隐藏

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: 收尾工作，确保整体质量

- [ ] T069 [P] 创建 Docker Compose 配置（MySQL + Redis + backend + frontend）in `docker-compose.yml`
- [ ] T070 [P] 创建后端 Dockerfile in `backend/Dockerfile`，创建前端 Dockerfile in `frontend/Dockerfile`
- [ ] T071 [P] 添加前端路由配置（AnalysisPage、KnowledgePage、ArticleDetailPage、ReminderPage）in `frontend/src/App.tsx`
- [ ] T072 [P] 添加前端全局布局（顶部导航栏：分析/知识库/提醒入口 + 铃铛图标 + 分析状态条）in `frontend/src/components/layout/`
- [ ] T073 [P] 添加后端 CORS 中间件配置（允许前端域名）in `backend/app/main.py`
- [ ] T074 [P] 添加后端统一错误处理中间件 in `backend/app/core/exceptions.py`
- [ ] T075 [P] 添加后端日志配置（AI 调用日志、关键业务操作日志，禁止泄露 API Key）in `backend/app/core/logging.py`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Foundational — 核心分析流程
- **US2 (Phase 4)**: Depends on US1 — 保存分析结果
- **US3 (Phase 5)**: Depends on US2 — 浏览已保存文章
- **US4 (Phase 6)**: Depends on US3 — 检测历史文章相似度
- **US5 (Phase 7)**: Depends on US1 only — 提醒功能独立，触发分析依赖 US1
- **US6 (Phase 8)**: Depends on US1 only — 示例引导触发分析
- **Polish (Phase 9)**: Depends on all desired user stories being complete

### User Story Dependencies

- **US1 (P1)**: Foundational → 直接开始
- **US2 (P1)**: US1 完成 → 开始
- **US3 (P1)**: US2 完成 → 开始
- **US4 (P2)**: US3 完成 → 开始
- **US5 (P2)**: US1 完成 → 可与 US2/US3/US4 并行
- **US6 (P3)**: US1 完成 → 可与 US2-US5 并行

### Within Each User Story

- Domain entities before Application use cases
- Application use cases before Routers
- Backend before Frontend (API 先行)
- Frontend: Service → Store → Application → Components → Page

### Parallel Opportunities

- Phase 1: T002-T009 全部可并行（不同文件）
- Phase 2: T012-T015、T017-T023 大部分可并行
- Phase 3: T026-T034 大部分可并行（不同文件）
- Phase 5: T044-T051 大部分可并行
- Phase 7: T061-T065 可并行
- **跨 Story 并行**: US5 和 US6 可与 US2-US4 并行执行

---

## Parallel Example: User Story 1

```bash
# Backend:
Task: "AnalyzeEventUseCase in backend/app/application/use_cases/analyze_event.py"

# Frontend (all parallel):
Task: "analysisService in frontend/src/services/analysisService.ts"
Task: "analysisStore in frontend/src/store/analysisStore.ts"
Task: "useSSE hook in frontend/src/hooks/useSSE.ts"
Task: "useDraft hook in frontend/src/hooks/useDraft.ts"
Task: "EventTypeSelector in frontend/src/components/analysis/EventTypeSelector.tsx"
Task: "AnalysisInput in frontend/src/components/analysis/AnalysisInput.tsx"
Task: "AnalysisResult in frontend/src/components/analysis/AnalysisResult.tsx"
Task: "AnalysisStatusBar in frontend/src/components/analysis/AnalysisStatusBar.tsx"

# Sequential after parallel:
Task: "useAnalysis in frontend/src/application/useAnalysis.ts" (depends on service+store)
Task: "AnalysisPage in frontend/src/pages/AnalysisPage.tsx" (depends on all components)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: 输入事件描述 → 选择类型 → 看到流式分析结果
5. Deploy/demo if ready

### P1 完整闭环 (US1 + US2 + US3)

1. Setup + Foundational → Foundation ready
2. Add US1 → 分析功能可用
3. Add US2 → 保存到知识库
4. Add US3 → 浏览和搜索知识库
5. **完整 P1 闭环**: 选类型 → 分析 → 保存 → 浏览/搜索

### 增量交付

1. P1 闭环 (US1+US2+US3) → 核心价值交付
2. Add US4 → 相似问题检测（增强体验）
3. Add US5 → 大事提醒（时间管理）
4. Add US6 → 新用户引导（降低门槛）
5. Polish → Docker 部署、路由、布局、日志

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence