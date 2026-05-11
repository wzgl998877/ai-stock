# Tasks: 投资事件影响雷达

**Input**: Design documents from `/specs/007-event-radar/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: 本项目 CLAUDE.md 明确要求单元测试为质量底线，所有核心领域服务包含测试任务。

**Organization**: 任务按用户故事分组，每个故事可独立实现和测试。

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 可并行执行（不同文件，无依赖）
- **[Story]**: 所属用户故事（US1-US7）
- 包含精确文件路径

## Path Conventions

- **后端**: `backend/app/` (Router → Application → Domain → Infrastructure)
- **前端**: `frontend/src/` (Page → Store → Service → API)
- **测试**: `backend/tests/`, `frontend/src/tests/`

---

## Phase 1: Setup (共享基础设施)

**Purpose**: 数据库迁移、目录结构创建

- [ ] T001 创建 Alembic 迁移文件，新增 6 张表（t_impact_event, t_impact_article, t_user_impact, t_user_alert, t_morning_briefing, t_radar_config），DDL 参考 specs/007-event-radar/data-model.md，迁移文件放在 backend/app/infrastructure/db/migrations/versions/
- [ ] T002 [P] 创建后端新增目录结构：backend/app/infrastructure/crawler/ 和 backend/app/infrastructure/scheduler/
- [ ] T003 [P] 创建前端新增目录结构：frontend/src/components/event-radar/

**Checkpoint**: 数据库表已创建，目录结构已就绪

---

## Phase 2: Foundational (阻塞性前置任务)

**Purpose**: 所有用户故事共享的核心基础设施——实体、仓储、领域服务、信息源抽象、调度器集成

**⚠️ CRITICAL**: 所有用户故事任务必须在此阶段完成后才能开始

### 实体与仓储

- [ ] T004 [P] 创建 ImpactEvent 实体在 backend/app/domain/entities/impact_event.py，字段参考 data-model.md
- [ ] T005 [P] 创建 ImpactArticle 实体在 backend/app/domain/entities/impact_article.py
- [ ] T006 [P] 创建 UserImpact 实体在 backend/app/domain/entities/user_impact.py
- [ ] T007 [P] 创建 UserAlert 实体在 backend/app/domain/entities/user_alert.py
- [ ] T008 [P] 创建 MorningBriefing 实体在 backend/app/domain/entities/morning_briefing.py
- [ ] T009 [P] 创建 RadarConfig 实体在 backend/app/domain/entities/radar_config.py
- [ ] T010 [P] 在 backend/app/infrastructure/db/models.py 中新增 6 张表的 SQLAlchemy ORM 映射
- [ ] T011 [P] 创建 ImpactEvent 仓储接口在 backend/app/domain/repositories/impact_event_repo.py
- [ ] T012 [P] 创建 ImpactArticle 仓储接口在 backend/app/domain/repositories/impact_article_repo.py
- [ ] T013 [P] 创建 UserImpact 仓储接口在 backend/app/domain/repositories/user_impact_repo.py
- [ ] T014 [P] 创建 UserAlert 仓储接口在 backend/app/domain/repositories/user_alert_repo.py
- [ ] T015 [P] 创建 MorningBriefing 仓储接口在 backend/app/domain/repositories/morning_briefing_repo.py
- [ ] T016 [P] 创建 RadarConfig 仓储接口在 backend/app/domain/repositories/radar_config_repo.py
- [ ] T017 [P] 创建 ImpactEvent MySQL 仓储实现在 backend/app/infrastructure/repositories/mysql_impact_event_repo.py
- [ ] T018 [P] 创建 ImpactArticle MySQL 仓储实现在 backend/app/infrastructure/repositories/mysql_impact_article_repo.py
- [ ] T019 [P] 创建 UserImpact MySQL 仓储实现在 backend/app/infrastructure/repositories/mysql_user_impact_repo.py
- [ ] T020 [P] 创建 UserAlert MySQL 仓储实现在 backend/app/infrastructure/repositories/mysql_user_alert_repo.py
- [ ] T021 [P] 创建 MorningBriefing MySQL 仓储实现在 backend/app/infrastructure/repositories/mysql_morning_briefing_repo.py
- [ ] T022 [P] 创建 RadarConfig MySQL 仓储实现在 backend/app/infrastructure/repositories/mysql_radar_config_repo.py

### 核心领域服务

- [ ] T023 创建情感规则引擎在 backend/app/domain/services/sentiment_rule_engine.py，实现利好/利空词汇库关键词匹配，输出 sentiment + confidence，参考 research.md 任务 4
- [ ] T024 创建事件去重服务在 backend/app/domain/services/event_dedup.py，实现 URL MD5 精确去重 + Jaccard 标题去重（阈值 0.6），参考 research.md 任务 2
- [ ] T025 创建事件-股票匹配服务在 backend/app/domain/services/event_stock_matcher.py，复用现有 MetadataExtractor 的股票提取逻辑，实现三级匹配（正则→名称→行业关键词）
- [ ] T026 创建影响判断引擎在 backend/app/domain/services/impact_assessment.py，编排 T023/T024/T025，实现完整管线：关联提取→用户匹配→影响判断→优先级计算，输出 UserImpact 记录

### 信息源与调度器

- [ ] T027 创建信息源抽象基类在 backend/app/infrastructure/crawler/base_provider.py，定义 fetch_latest / fetch_by_stock / fetch_by_keyword 异步接口
- [ ] T028 创建财联社信息源实现在 backend/app/infrastructure/crawler/cls_provider.py，实现 BaseEventProvider，调用财联社 API/RSS，异常时记录日志，参考 research.md 任务 1
- [ ] T029 将现有 SearchService（backend/app/domain/services/search_service.py）适配为 EventProvider，包装 fetch_latest 方法（按自选股关键词搜索）
- [ ] T030 创建事件采集调度器在 backend/app/infrastructure/scheduler/event_crawler_scheduler.py，使用 APScheduler AsyncIOScheduler，注册交易时段每10分钟/非交易时段每1小时采集任务 + 每天6:30晨报生成任务
- [ ] T031 在 backend/app/main.py 的 lifespan 函数中集成 APScheduler 启动（scheduler.start()），参考现有 LangGraph 图的初始化模式

### DTO 与依赖注入

- [ ] T032 [P] 创建事件雷达 DTO 在 backend/app/application/dtos/event_radar_dto.py，包含 ImpactEventDTO、UserImpactDTO、AlertDTO、BriefingDTO、RadarConfigDTO、StatsDTO 等 Pydantic 模型
- [ ] T033 在 backend/app/core/deps.py 中注册新增的 6 个仓储依赖注入

### 单元测试（领域服务）

- [ ] T034 [P] 编写情感规则引擎单元测试在 backend/tests/unit/domain/test_sentiment_rule_engine.py，验证利好/利空/中性判断和置信度计算
- [ ] T035 [P] 编写事件去重服务单元测试在 backend/tests/unit/domain/test_event_dedup.py，验证 URL 去重和标题相似度去重
- [ ] T036 [P] 编写事件-股票匹配服务单元测试在 backend/tests/unit/domain/test_event_stock_matcher.py，验证三级匹配逻辑

**Checkpoint**: 基础设施就绪——所有实体、仓储、领域服务、信息源、调度器已实现且测试通过

---

## Phase 3: User Story 1 - 查看影响雷达面板 (Priority: P1) 🎯 MVP

**Goal**: 用户打开「事件雷达」页面，立即看到此刻正在影响自己投资的事件列表，按"正在影响"和"今日已影响"分层展示

**Independent Test**: 手动向数据库插入测试影响事件和用户影响关联记录，打开 /event-radar 页面，验证事件卡片正确展示、操作按钮可用、空状态正常、交易时段自动刷新

### 后端实现

- [ ] T037 [US1] 创建事件雷达用例在 backend/app/application/use_cases/event_radar.py，实现 get_user_impacts（获取活跃+已归档影响事件）、get_impact_stats（获取统计）、get_impact_detail（获取单条详情含关联文章）
- [ ] T038 [US1] 创建事件雷达路由在 backend/app/routers/event_radar.py，实现 GET /api/v1/event-radar/impacts、GET /api/v1/event-radar/impacts/{id}、GET /api/v1/event-radar/stats 三个端点，契约参考 contracts/api-contracts.md
- [ ] T039 [US1] 创建事件采集完整管线用例在 backend/app/application/use_cases/ 下（可复用 event_radar.py 或新建 crawl_events.py），编排：调用 BaseEventProvider 采集 → EventDedup 去重 → EventStockMatcher 提取关联 → ImpactAssessment 判断影响 → 写入 UserImpact

### 前端实现

- [ ] T040 [P] [US1] 创建事件雷达 API 服务在 frontend/src/services/eventRadarService.ts，封装 GET /impacts、GET /impacts/{id}、GET /stats 等接口调用
- [ ] T041 [P] [US1] 创建事件雷达 Zustand Store 在 frontend/src/store/eventRadarStore.ts，管理影响事件列表、统计数据、加载状态、当前详情
- [ ] T042 [US1] 创建影响事件卡片组件在 frontend/src/components/event-radar/ImpactEventCard.tsx，展示事件标题/来源/时间/影响到的自选股（含方向颜色标注）/操作按钮
- [ ] T043 [US1] 创建影响概览统计组件在 frontend/src/components/event-radar/ImpactStatsCard.tsx，展示今日影响事件数、涉及自选股数、本周累计数
- [ ] T044 [US1] 创建事件雷达主页面在 frontend/src/pages/EventRadarPage.tsx，组合 ImpactEventCard + ImpactStatsCard，实现"正在影响"/"今日已影响"分层展示、空状态、交易时段 60 秒自动刷新、自选股为空时引导提示
- [ ] T045 [US1] 在前端路由 App.tsx 中注册 /event-radar 路由指向 EventRadarPage
- [ ] T046 [US1] 在侧边栏菜单（AppLayout 组件）中新增「事件雷达」一级菜单项，位于「事件分析」之前，图标用 RadarChartOutlined

**Checkpoint**: 用户可打开 /event-radar 页面看到影响事件列表（MVP 可交付）

---

## Phase 4: User Story 2 - 一键分析影响事件 (Priority: P1)

**Goal**: 点击事件卡片"一键分析"按钮，跳转模块一事件分析页面并预填内容、自动启动分析

**Independent Test**: 在影响雷达面板点击"一键分析"，验证跳转到 /analysis 页面、输入框已预填事件标题和摘要、事件类型已自动匹配、分析自动启动

### 前端实现（核心联动逻辑）

- [ ] T047 [US2] 修改 ImpactEventCard.tsx 的"一键分析"按钮，点击时携带事件数据（title, summary, event_type）通过 URL 参数跳转到 /analysis 页面
- [ ] T048 [US2] 修改 AnalysisPage.tsx（或其输入组件），检测 URL 参数中是否携带来自事件雷达的预填数据（eventTitle, eventSummary, eventType），如有则自动填入输入框并触发分析
- [ ] T049 [US2] 在事件卡片上增加"已分析"标记逻辑：当知识库中存在与该事件关联的文章时，显示"已分析"标签

**Checkpoint**: 影响雷达 → 模块一事件分析的联动闭环已打通

---

## Phase 5: User Story 3 - 事件详情与 AI 解读 (Priority: P2)

**Goal**: 点击事件的"查看详情"或"AI解读"，弹出三段式 Drawer：原文摘要 + AI 影响解读 + 知识库关联 + 行动按钮

**Independent Test**: 点击事件卡片的"查看详情"，验证 Drawer 弹出、三段式布局正确、AI 解读展示影响原因、知识库关联展示（如有）、各行动按钮可用

### 后端实现

- [ ] T050 [P] [US3] 创建影响判断 Prompt 模板在 backend/app/infrastructure/ai/prompts/impact_assessment.py，模板化输出 JSON（event_nature, affected_industries_detail, stock_impact_reasons）
- [ ] T051 [US3] 在 event_radar.py 用例中实现 generate_ai_insight 方法，调用 AIService 生成 AI 影响解读（幂等：已生成则返回缓存），实现知识库关联查询（基于行业+股票代码交集匹配历史分析文章）
- [ ] T052 [US3] 在 event_radar.py 路由中实现 POST /api/v1/event-radar/impacts/{id}/ai-insight 端点

### 前端实现

- [ ] T053 [US3] 创建事件详情 Drawer 在 frontend/src/components/event-radar/EventDetailDrawer.tsx，三段式布局：原文摘要区（标题+来源+时间+摘要≤200字+查看原文链接）→ AI 影响解读区（事件性质/影响行业/每只自选股的影响原因/知识库关联）→ 行动按钮区（一键分析/查看K线/个股深度分析/查看历史分析）
- [ ] T054 [US3] 在 EventDetailDrawer 的行动按钮中集成全局股票抽屉（stockDrawerStore.open(code)）和模块一个股分析跳转

**Checkpoint**: 用户可查看事件详情和 AI 解读，理解"为什么影响我的投资"

---

## Phase 6: User Story 4 - 接收影响预警推送 (Priority: P2)

**Goal**: P0/P1 级别影响事件主动推送通知，铃铛图标显示未读数量，点击弹出预警 Drawer

**Independent Test**: 手动创建 P0 预警记录，验证铃铛显示未读数字，点击弹出 Drawer，操作按钮可用，标记已读后数字更新，每日 5 条限制生效

### 后端实现

- [ ] T055 [US4] 创建预警管理用例在 backend/app/application/use_cases/event_alert.py，实现 get_unread_alerts、get_unread_count、mark_as_read 方法
- [ ] T056 [US4] 修改 impact_assessment.py 的影响判断管线，当输出 P0/P1 级别时触发预警创建：检查免打扰时段、检查当日预警数≤5、写入 t_user_alert
- [ ] T057 [US4] 在 event_radar.py 路由中实现预警端点：GET /alerts、GET /alerts/unread-count、PUT /alerts/{id}/read

### 前端实现

- [ ] T058 [P] [US4] 创建预警 Drawer 组件在 frontend/src/components/event-radar/AlertDrawer.tsx，展示预警列表（按优先级排序），每条包含标题/影响到的自选股/方向/置信度 + "查看详情"/"一键分析"按钮
- [ ] T059 [US4] 创建/修改铃铛预警图标组件在 frontend/src/components/layout/AlertBell.tsx，使用 Ant Badge + BellOutlined，展示未读数量红点，点击弹出 AlertDrawer，60 秒轮询获取 unread-count
- [ ] T060 [US4] 在 AppLayout 中集成 AlertBell 组件到顶部右侧

**Checkpoint**: 用户可在任何页面通过铃铛收到影响预警推送

---

## Phase 7: User Story 6 - 自选股页面增强影响徽标 (Priority: P2)

**Goal**: 自选股列表每行新增"影响"列，展示影响事件数量和方向颜色点

**Independent Test**: 为测试用户的自选股准备影响事件数据，打开自选股页面，验证新增"影响"列展示正确，点击展开摘要正常

### 后端实现

- [ ] T061 [US6] 在 event_radar.py 路由中实现 GET /api/v1/event-radar/stock-impacts 端点，批量返回自选股影响状态（每只股票的影响事件数量+方向+最近5条摘要）

### 前端实现

- [ ] T062 [US6] 创建自选股影响列组件在 frontend/src/components/event-radar/WatchlistImpactColumn.tsx，使用 Ant Tag 展示影响事件数量和方向颜色点（绿/红/灰），点击展示 Ant Popover 弹出最近 5 条影响事件摘要
- [ ] T063 [US6] 修改 WatchlistPage.tsx，在涨跌幅列之后新增"影响"列，使用 WatchlistImpactColumn 组件渲染，数据来自 eventRadarService.getStockImpacts()

**Checkpoint**: 自选股页面增强完成，用户可同时看到"行情 + 什么在影响行情"

---

## Phase 8: User Story 5 - 查看影响晨报 (Priority: P3)

**Goal**: 每天早上首次登录弹出个性化影响晨报，30 秒扫完核心信息

**Independent Test**: 准备测试晨报数据，用户当日首次登录触发晨报弹窗，验证各板块正确、操作按钮可用、关闭后可在历史页面回溯

### 后端实现

- [ ] T064 [P] [US5] 创建晨报生成 Prompt 模板在 backend/app/infrastructure/ai/prompts/morning_briefing.py
- [ ] T065 [US5] 创建晨报 LangGraph 工作流在 backend/app/infrastructure/workflow/graph/morning_briefing_graph.py，节点：collect_impact_events → collect_portfolio_status → match_knowledge_context → generate_briefing → save_briefing，参考现有 analysis_graph.py 模式
- [ ] T066 [US5] 创建晨报用例在 backend/app/application/use_cases/morning_briefing.py，实现 get_today_briefing、get_briefing_history、mark_briefing_read
- [ ] T067 [US5] 在 event_radar.py 路由中实现晨报端点：GET /briefing/today、GET /briefing/history、PUT /briefing/{id}/read

### 前端实现

- [ ] T068 [P] [US5] 创建晨报弹窗组件在 frontend/src/components/event-radar/MorningBriefingModal.tsx，使用 Ant Modal，卡片化展示 AI 一句话总结 + 影响事件列表 + 自选股概览 + 今日关注，底部"开始今日分析"和"关闭"按钮
- [ ] T069 [US5] 在 AppLayout 或 App.tsx 中添加首次登录检测逻辑：当日首次登录时自动弹出晨报 Modal（调用 GET /briefing/today，如有数据则展示）

**Checkpoint**: 每日首次登录弹出个性化晨报

---

## Phase 9: User Story 7 - 影响范围配置 (Priority: P3)

**Goal**: 用户可自定义监测范围（关注行业、事件类型、预警灵敏度、免打扰时段）

**Independent Test**: 打开设置，修改配置，保存后验证即时生效

### 后端实现

- [ ] T070 [US7] 创建雷达配置用例（可放在 event_radar.py 中），实现 get_config、update_config，默认配置：关注行业从自选股自动推断、灵敏度"中"
- [ ] T071 [US7] 在 event_radar.py 路由中实现配置端点：GET /config、PUT /config

### 前端实现

- [ ] T072 [US7] 创建雷达配置弹窗在 frontend/src/components/event-radar/RadarConfigModal.tsx，使用 Ant Form，包含：关注行业（Checkbox Group，申万 31 行业）、事件类型（Checkbox Group，5 种类型）、预警灵敏度（Radio，高/中/低）、免打扰时段（TimePicker 范围）
- [ ] T073 [US7] 在 EventRadarPage.tsx 顶部添加"设置"按钮，点击弹出 RadarConfigModal

**Checkpoint**: 用户可自定义监测范围和预警灵敏度

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: 跨故事的优化和收尾

- [ ] T074 在所有影响事件展示页面（面板、详情 Drawer、晨报）底部添加"以上为 AI 分析参考，不构成投资建议"声明
- [ ] T075 [P] 编写事件雷达 API 集成测试在 backend/tests/integration/test_event_radar_api.py，覆盖核心端点 CRUD
- [ ] T076 [P] 编写财联社信息源单元测试在 backend/tests/unit/infrastructure/test_cls_provider.py，mock API 响应验证解析逻辑
- [ ] T077 [P] 编写晨报工作流单元测试在 backend/tests/unit/infrastructure/test_morning_briefing_graph.py，验证节点编排和数据流
- [ ] T078 确保所有新增页面具备 loading（骨架屏）、empty（空状态提示）、error（错误提示）三种状态
- [ ] T079 运行 quickstart.md 验证：数据库迁移、后端启动（含 APScheduler）、前端启动、手动触发采集、面板验证

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: 无依赖，立即开始
- **Foundational (Phase 2)**: 依赖 Setup 完成 → 阻塞所有用户故事
- **US1 & US2 (Phase 3-4)**: 依赖 Foundational → MVP 核心，必须先完成
- **US3 (Phase 5)**: 依赖 US1（需要面板和事件卡片组件）
- **US4 (Phase 6)**: 依赖 Foundational + US1（预警需要影响判断管线和前端布局）
- **US6 (Phase 7)**: 依赖 Foundational + US1（需要影响事件数据）
- **US5 (Phase 8)**: 依赖 Foundational + US1（晨报需要影响事件数据积累）
- **US7 (Phase 9)**: 依赖 Foundational（配置相对独立）
- **Polish (Phase 10)**: 依赖所有用户故事完成

### User Story Dependencies

```
Foundational (Phase 2)
    ├── US1 雷达面板 (Phase 3) ─── MVP 🎯
    │       └── US2 一键分析 (Phase 4)
    │       └── US3 AI解读 (Phase 5)
    │       └── US4 预警推送 (Phase 6)
    │       └── US6 自选股徽标 (Phase 7)
    │       └── US5 晨报 (Phase 8)
    └── US7 配置 (Phase 9)
```

### Parallel Opportunities

**Phase 2 内部并行**:
- T004-T009（6 个实体）全部可并行
- T011-T016（6 个仓储接口）全部可并行
- T017-T022（6 个仓储实现）全部可并行
- T034-T036（3 个领域服务测试）全部可并行

**Phase 3 内部并行**:
- T040（Service）和 T041（Store）可并行
- T037（后端用例）和 T040/T041（前端 Service/Store）可并行

**Phase 5-7 可并行**:
- US3（Phase 5）和 US6（Phase 7）无相互依赖，可并行开发
- US4（Phase 6）和 US7（Phase 9）无相互依赖，可并行开发

---

## Parallel Example: Phase 2 (Foundational)

```bash
# 并行创建所有实体（T004-T009）
Task: "创建 ImpactEvent 实体在 backend/app/domain/entities/impact_event.py"
Task: "创建 ImpactArticle 实体在 backend/app/domain/entities/impact_article.py"
Task: "创建 UserImpact 实体在 backend/app/domain/entities/user_impact.py"
Task: "创建 UserAlert 实体在 backend/app/domain/entities/user_alert.py"
Task: "创建 MorningBriefing 实体在 backend/app/domain/entities/morning_briefing.py"
Task: "创建 RadarConfig 实体在 backend/app/domain/entities/radar_config.py"
```

## Parallel Example: Phase 3 (US1)

```bash
# 后端和前端可并行
# 后端线：T037 → T038 → T039
# 前端线：T040 + T041（并行） → T042 → T043 → T044 → T045 + T046
```

---

## Implementation Strategy

### MVP First (User Story 1 + 2 Only)

1. 完成 Phase 1: Setup（数据库迁移 + 目录结构）
2. 完成 Phase 2: Foundational（实体 + 仓储 + 领域服务 + 信息源 + 调度器）
3. 完成 Phase 3: US1（影响雷达面板）
4. 完成 Phase 4: US2（一键分析联动）
5. **STOP and VALIDATE**: 用手动数据测试面板展示和一键分析跳转
6. 可部署/Demo

### Incremental Delivery

1. Setup + Foundational → 基础设施就绪
2. US1 + US2 → 影响面板 + 分析联动（MVP）
3. US3 → AI 解读（增强理解深度）
4. US4 → 预警推送（推模式核心）
5. US6 → 自选股增强（嵌入高频页面）
6. US5 → 晨报（每日启动仪式）
7. US7 → 配置（精细化）
8. Polish → 测试、声明、验证

---

## Notes

- [P] 标记 = 不同文件，无依赖，可并行
- [Story] 标签 = 映射到 spec.md 中的用户故事，便于追踪
- 每个用户故事应可独立完成和测试
- 核心领域服务（T023-T026）包含单元测试（T034-T036）
- 在每个 Checkpoint 处停止并独立验证
- 提交粒度：每完成一个 Task 或逻辑分组后提交
