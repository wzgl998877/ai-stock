# Tasks: 投资事件影响雷达（补齐任务）

**Input**: 基于代码审查发现的联动缺失 + specs/007-event-radar/ 设计文档
**Scope**: 仅包含尚未完成或实现不完整的任务，已验证通过的任务不重复列出
**Date**: 2026-05-13

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 可并行执行（不同文件，无依赖）
- **[Story]**: 所属用户故事（US1-US7）
- 包含精确文件路径

## Path Conventions

- **后端**: `backend/app/` (Router → Application → Domain → Infrastructure)
- **前端**: `frontend/src/` (Page → Store → Service → API)
- **测试**: `backend/tests/`, `frontend/src/tests/`

---

## Phase 1: 采集管线修复（阻塞性）

**Purpose**: 修复采集器 API 地址、补充启动时股票名称映射注入、用 compute_user_impact 替代简单交集匹配

**⚠️ CRITICAL**: 当前采集管线能工作但匹配质量低，必须先修复才能让后续联动有意义

- [x] T001 修复财联社 API 地址：将 `backend/app/infrastructure/crawler/cls_provider.py` 中 `CLS_ROLL_URL` 从 `cls.cn/api/sw` 改为 `cls.cn/nodeapi/updateTelegraphList`，URL 字段取 `shareurl`，添加 User-Agent/Referer 请求头
- [x] T002 在应用启动时注入股票名称映射：修改 `backend/app/main.py` 的 lifespan，从 `t_stock` 表加载 `{name: code}` 字典，调用 `backend/app/domain/services/event_stock_matcher.py` 的 `set_stock_name_map()`，使第二级名称匹配生效
- [x] T003 用 compute_user_impact 替代简单交集匹配：重构 `backend/app/application/use_cases/event_radar.py` 的 `_match_users_for_events()` 方法，调用 `backend/app/domain/services/impact_assessment.py` 的 `compute_user_impact()` 进行双维度匹配（股票+行业）和加权优先级评分，替代当前仅做 stock_code 交集的内联逻辑
- [x] T004 同步修复调度器中的匹配逻辑：将 `backend/app/infrastructure/scheduler/event_crawler_scheduler.py` 的 `crawl_and_process()` 中内联的用户匹配逻辑替换为调用 EventRadarUseCase.crawl_and_process()，避免两处维护不一致

**Checkpoint**: 采集→匹配→入库链路完整，名称匹配和行业匹配均生效

---

## Phase 2: User Story 6 - 自选股页面集成影响列 (Priority: P2)

**Goal**: 自选股列表表格新增"影响"列，展示每只股票最近 24h 的影响事件数量和方向颜色点

**Independent Test**: 打开 /market/watchlist 页面，验证涨跌幅列之后新增"影响"列，显示 Tag + 方向颜色点，点击 Popover 展示最近 5 条影响事件摘要

- [x] T005 [US6] 在 `frontend/src/pages/WatchlistPage.tsx` 中引入 WatchlistImpactColumn 组件，在表格列定义的涨跌幅列之后新增"影响"列，并在页面加载时调用 `eventRadarStore.getStockImpacts()` 获取数据，将 stockImpacts map 传给每行的 WatchlistImpactColumn

**Checkpoint**: 自选股页面同时展示"行情 + 什么在影响行情"

---

## Phase 3: User Story 3 - 知识库联动（事件详情 Drawer） (Priority: P2)

**Goal**: 事件详情 Drawer 中展示知识库关联区域——与当前事件相关的历史分析文章列表（标题+日期+结论摘要）

**Independent Test**: 对一条有历史分析的事件点击"查看详情"，验证 Drawer 中出现"知识库关联"区域，展示相关文章链接

### 后端实现

- [x] T006 [P] [US3] 新增知识库关联查询方法在 `backend/app/application/use_cases/event_radar.py`，实现 `_find_related_analyses(event)`：根据事件的 `affected_stocks` 中的 stock_code 和 `affected_industries` 中的行业名，在 `t_analysis_article`（或对应的知识库表）中检索匹配的历史分析文章，返回 `[{article_id, title, analyzed_at, summary}]`，限制最多 5 条
- [x] T007 [US3] 修改 `backend/app/routers/event_radar.py` 的 `GET /impacts/{impact_id}` 端点（约第 94-142 行），将 `related_analyses` 硬编码空列表替换为调用 `_find_related_analyses(event)` 的结果；同时修改 `GET /impacts` 端点的 `_impact_to_dict` helper（约第 48 行），将 `has_related_analysis` 从硬编码 `False` 改为动态计算

### 前端实现

- [x] T008 [US3] 修改 `frontend/src/components/event-radar/EventDetailDrawer.tsx`，在 AI 影响解读区和行动按钮区之间新增"知识库关联"区域：当 `related_analyses` 非空时展示列表，每条包含文章标题（蓝色可点击）、分析日期、结论摘要；为空时不展示该区域（遵循 spec Edge Case）

**Checkpoint**: 事件详情中可查看关联的历史分析文章，完成"发现影响 → 回溯历史分析"闭环

---

## Phase 4: User Story 2 - "已分析"标记 (Priority: P1)

**Goal**: 用户从事件雷达跳转分析后返回，事件卡片上显示"已分析"标记

**Independent Test**: 点击"一键分析"完成分析后返回雷达面板，验证对应事件卡片显示"已分析"标签

- [x] T009 [US2] 后端：修改 `backend/app/routers/event_radar.py` 的 `GET /impacts` 和 `_impact_to_dict` helper，为每条 UserImpact 检查知识库中是否存在与该事件的 affected_stocks 有关联的分析文章，设置 `has_related_analysis` 字段（可复用 Phase 3 的 `_find_related_analyses`）
- [x] T010 [US2] 前端：修改 `frontend/src/components/event-radar/ImpactEventCard.tsx`，当 impact 对象的 `has_related_analysis` 为 true 时，在卡片右上角展示"已分析" Tag 标签（Ant Tag，颜色 blue）

**Checkpoint**: 分析过的事件在雷达面板有视觉标记

---

## Phase 5: User Story 5 - 晨报生成后端实现 (Priority: P3)

**Goal**: 每天 6:30 自动为有自选股的用户生成个性化影响晨报，用户首次登录弹出晨报

**Independent Test**: 手动触发晨报生成，调用 GET /briefing/today 返回完整晨报数据（AI 总结 + 影响事件 + 自选股概览 + 今日关注）

### 后端实现

- [x] T011 [US5] 实现 `backend/app/infrastructure/scheduler/event_crawler_scheduler.py` 中 `generate_morning_briefing()` 函数体（当前是 `pass` + TODO）：查询所有有自选股的用户，对每个用户获取昨日影响事件和自选股状态，调用 LLM 生成 AI 总结，组装 content JSON（impact_events + portfolio_overview + today_focus），写入 `t_morning_briefing`
- [x] T012 [P] [US5] 编写晨报生成辅助方法在 `backend/app/application/use_cases/morning_briefing.py`，实现 `generate_for_user(user_id)` 方法：从 UserImpact 获取昨日影响事件、从 watchlist 获取自选股列表和昨收价、调用 AIService 生成 AI 一句话总结（Prompt 模板已在 `infrastructure/ai/prompts/morning_briefing.py`）、组装 content 并通过 MorningBriefingRepository 写入

### 前端实现

- [x] T013 [US5] 在 `frontend/src/components/layout/AppLayout.tsx` 中添加首次登录检测逻辑：组件 mount 时检查 localStorage 当日标记，如未标记则调用 GET /briefing/today，有数据则弹出 MorningBriefingModal，关闭后写入 localStorage 标记

**Checkpoint**: 用户每日首次登录弹出个性化晨报

---

## Phase 6: 预警逻辑完善

**Purpose**: 补齐每日 5 条预警上限和免打扰时段检查

- [x] T014 修改 `backend/app/application/use_cases/event_radar.py` 的 `_match_users_for_events()` 方法，在创建 UserImpact 后增加预警创建逻辑：当 priority 为 P0/P1 时，查询当日已推送预警数量，若 < 5 则创建 UserAlert 记录；检查用户 RadarConfig 的 quiet_hours 判断是否在免打扰时段内

**Checkpoint**: 预警推送符合每日上限和免打扰约束

---

## Phase 7: 单元测试与集成测试

**Purpose**: 补齐缺失的测试文件，保障代码质量

- [ ] T015 [P] 编写影响判断引擎单元测试在 `backend/tests/unit/domain/test_impact_assessment.py`，覆盖 assess_event 完整管线：利好/利空/中性判断、重要性分级、股票/行业提取、去重逻辑、compute_user_impact 双维度匹配和优先级计算
- [ ] T016 [P] 编写事件雷达 API 集成测试在 `backend/tests/integration/test_event_radar_api.py`，使用 ASGI TestClient + mock 认证，覆盖核心端点：GET /impacts、GET /impacts/{id}、GET /alerts/unread-count、POST /impacts/{id}/ai-insight、GET /config、PUT /config
- [ ] T017 [P] 编写财联社信息源单元测试在 `backend/tests/unit/infrastructure/test_cls_provider.py`，mock httpx 响应验证 fetch_latest 解析逻辑（标题提取、HTML 清洗、时间解析、URL 回退）

**Checkpoint**: 核心代码测试覆盖达标

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1（采集修复）**: 无前置依赖，但阻塞所有联动功能
- **Phase 2（自选股影响列）**: 依赖 Phase 1
- **Phase 3（知识库联动）**: 依赖 Phase 1
- **Phase 4（已分析标记）**: 依赖 Phase 3（复用知识库查询）
- **Phase 5（晨报）**: 依赖 Phase 1
- **Phase 6（预警完善）**: 依赖 Phase 1
- **Phase 7（测试）**: 可在 Phase 1 完成后任意时间并行执行

### User Story Dependencies

```
Phase 1: 采集管线修复 (阻塞一切)
    ├── Phase 2: US6 自选股影响列
    ├── Phase 3: US3 知识库联动 ──→ Phase 4: US2 已分析标记
    ├── Phase 5: US5 晨报生成
    ├── Phase 6: 预警逻辑完善
    └── Phase 7: 测试 (可并行)
```

### Parallel Opportunities

- Phase 2、3、5、6、7 在 Phase 1 完成后可全部并行
- T006 和 T007 可在 Phase 3 内并行（后端查询 + 路由修改不同文件区域）
- T015、T016、T017 可在 Phase 7 内全部并行（不同测试文件）

---

## Implementation Strategy

### 优先顺序

1. **Phase 1** → 修复采集匹配质量（所有联动的基础）
2. **Phase 2** → 自选股影响列（改动最小，价值最高）
3. **Phase 3** → 知识库联动（核心差异化功能）
4. **Phase 4** → 已分析标记（依赖 Phase 3 的查询逻辑）
5. **Phase 5** → 晨报生成（增强体验）
6. **Phase 6** → 预警完善（约束逻辑）
7. **Phase 7** → 测试保障（可穿插进行）

### MVP 建议

最小可交付增量 = Phase 1 + Phase 2，让用户在自选股页面看到实时影响数据。

---

## Notes

- 原始 tasks.md 中标 `[x]` 的任务已验证通过的不重复列出
- 原始 tasks.md 中标 `[x]` 但实际未完成的任务已在本文件中重新拆分
- 每个任务包含足够上下文供 LLM 直接实现，无需额外查找
