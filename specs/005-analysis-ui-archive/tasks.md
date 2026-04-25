# Tasks: 个股分析界面展示优化与存档

**Input**: Design documents from `/specs/005-analysis-ui-archive/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: 后端存档功能需单元测试（pytest）；前端通过 `tsc --noEmit` 编译检查和视觉验证。

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Frontend**: `frontend/src/`
- **Backend**: `backend/app/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: 打通后端数据通路（Domain Entity → Repository → DB Migration）和前端共享工具/Store 扩展

- [x] T001 在 `backend/app/domain/entities/article.py` 中为 Article dataclass 添加 `analysis_data: Optional[dict]`、`article_type: str = "event"`、`status: str = "completed"` 三个字段
- [x] T002 在 `backend/app/infrastructure/db/models.py` 中为 AnalysisArticle 模型添加 `status: Mapped[str] = mapped_column(String(20), nullable=False, default="completed")` 列
- [x] T003 [P] 创建 Alembic 迁移脚本 `backend/app/infrastructure/db/migrations/versions/xxx_add_status_to_article.py`：为 `t_analysis_article` 表新增 `status` VARCHAR(20) NOT NULL DEFAULT "completed" 列
- [x] T004 在 `backend/app/infrastructure/repositories/mysql_article_repo.py` 中：修改 `save()` 方法映射 `analysis_data`、`article_type`、`status` 字段；修改 `_to_entity()` 方法读取这三个字段
- [x] T005 [P] 在 `backend/app/application/dtos/article_dto.py` 中为 `ArticleListItemDTO` 和 `ArticleDetailDTO` 添加 `status: Optional[str]` 和 `analysis_mode: Optional[str]`（从 analysis_data.mode 读取）字段
- [x] T006 [P] 扩展 `frontend/src/store/stockAnalysisStore.ts`：新增 `viewMode: boolean`（默认 false）、`viewRecordId: string`（默认 ""）、`agentCompletedAt: Record<string, number>`（默认 {}）；新增 `loadFromRecord(data)` action 从存档数据填充 store；修改 `updateAgentStatus` 在 status="done" 时记录 `Date.now()`；修改 `startAnalysis` 重置新增字段
- [x] T007 [P] 确认 `frontend/src/utils/textUtils.tsx` 工具函数就绪（extractFirstSentence、extractRemainingText、highlightNumbers），如有问题修复

**Checkpoint**: 后端 Domain/Repository 数据通路打通，Alembic 迁移就绪，前端 Store 扩展就绪

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 后端存档用例和前端 Service/API 类型定义，为所有 User Story 提供后端支撑

- [x] T008 在 `backend/app/application/use_cases/stock_analysis_use_case.py` 中实现增量存档逻辑：注入 ArticleRepository；分析开始时创建 article 记录（article_type="stock_analysis", status="in_progress", raw_input=股票信息）；每个阶段完成时更新 analysis_data JSON；全流程完成时设置 title/summary/industries，status="completed"；错误或中断时 status="stopped"
- [x] T009 在 `backend/app/domain/repositories/article_repo.py` 抽象接口中添加 `update_analysis_data(article_id: str, analysis_data: dict, status: str)` 方法签名
- [x] T010 在 `backend/app/infrastructure/repositories/mysql_article_repo.py` 中实现 `update_analysis_data()` 方法：按 article_id 查找记录并更新 analysis_data JSON、status、update_time
- [x] T011 在 `backend/app/routers/analysis.py` 中新增两个端点：`GET /api/analysis/records`（分页列表，支持 status 过滤）和 `GET /api/analysis/records/{record_id}`（详情，返回完整 analysis_data）
- [x] T012 [P] 在 `frontend/src/domain/types.ts` 中新增 `AnalysisRecordDetail` 和 `AnalysisRecordListItem` 类型定义（对应后端返回的 analysis_data 结构）
- [x] T013 [P] 在 `frontend/src/services/stockAnalysisService.ts` 中新增 `getAnalysisRecord(recordId)` 和 `listAnalysisRecords(params)` 两个 API 方法
- [x] T014 [P] 在 `backend/tests/unit/test_analysis_archive.py` 中编写存档相关单元测试：验证创建记录、增量更新 analysis_data、状态转换（in_progress→completed/stopped）

**Checkpoint**: 后端存档 API 和前端 Service 就绪，增量存档逻辑可工作

---

## Phase 3: User Story 1 - 分析启动配置页 (Priority: P0) 🎯 MVP

**Goal**: 入口页重构为双栏布局（左配置+右预览），包含系统状态栏、Agent拓扑图、模式卡片选择器、历史快捷入口

**Independent Test**: 进入个股分析页面，验证双栏布局渲染正确，切换分析模式时拓扑图联动变化，点击启动后过渡到执行页

### Implementation for User Story 1

- [x] T015 [P] [US1] 新建 `frontend/src/components/stock-analysis/SystemStatusBar.tsx`：高度不超过40px，展示三项信息（系统在线=绿色脉冲圆点+文字 | 市场状态=根据A股交易时间动态切换交易中/已收盘 | 数据已同步=灰色芯片+打勾图标），竖线分隔
- [x] T016 [P] [US1] 新建 `frontend/src/components/stock-analysis/AgentTopologyPreview.tsx`：4个节点纵向排列（技术面分析师📊、基本面分析师📈、新闻舆情哨兵📰、风险评估官🛡️），圆角矩形卡片含图标+名称，节点间虚线连接标注关系词；接收 `analysisMode` prop，快速模式仅前两位亮起后两位置灰，深度模式全部亮起+蓝色光晕边框
- [x] T017 [P] [US1] 新建 `frontend/src/components/stock-analysis/ModeSelectionCards.tsx`：两张可点选模式卡片（快速⚡·2位·约30-60秒 / 深度⚡·4位+辩论+风评·约3-5分钟），选中卡片蓝色高亮边框+微蓝背景，未选中灰色边框；props: `value`, `onChange`
- [x] T018 [P] [US1] 新建 `frontend/src/components/stock-analysis/HistoryQuickEntry.tsx`：调用 `stockAnalysisService.listAnalysisRecords` 获取最近3条记录，每条展示标题+日期+决策标签，点击跳转 `/stock-analysis?recordId=xxx`；无记录时不渲染；props: `stockCode`, `onSelect`
- [x] T019 [US1] 重构 `frontend/src/pages/StockAnalysisPage.tsx` 的 Idle 态：从单栏居中改为双栏布局（左40-45%配置区+右55-60%预览区）；页面顶部渲染 SystemStatusBar；左侧放置 StockSearchInput + ModeSelectionCards + "开始分析"按钮（点击后文字变为"正在调动分析师..."300ms后进入执行态）+ 合规提示；右侧放置 AgentTopologyPreview（根据 analysisMode 联动）+ HistoryQuickEntry

**Checkpoint**: 启动配置页双栏布局就绪，系统状态栏、拓扑图、模式卡片、历史入口全部可交互

---

## Phase 4: User Story 2 - 分析过程实时可视化 (Priority: P1)

**Goal**: 左侧 Agent 进度面板统一图标+连接线，右侧内容区随阶段自动切换，快速/深度模式统一体验，已完成阶段可折叠回看，详细推理全量展示

**Independent Test**: 分别发起快速/深度分析，验证左侧面板 Agent 状态图标统一、右侧内容随阶段切换、已完成阶段可折叠、"查看详细推理"展示全量文本

### Implementation for User Story 2

- [x] T020 [US2] 修改 `frontend/src/components/stock-analysis/AgentProgressPanel.tsx`：支持 `analysisMode` 区分渲染（quick=1阶段2个Agent, full=4阶段12个Agent）；统一状态图标（ClockCircleOutlined/LoadingOutlined/CheckCircleFilled/CloseCircleFilled）；节点间CSS竖线连接（颜色按状态变化）；已完成阶段opacity 0.65；阶段间渐变分隔线
- [x] T021 [US2] 修改 `frontend/src/pages/StockAnalysisPage.tsx` Running 态：右侧展示区根据 `currentPhase` 自动切换内容（analysts→辩论→决策→风险），由 SSE agent_status 事件中的 phase 字段驱动；快速模式仅展示 analysts 阶段内容；深度分析中已完成阶段折叠为一行"XX阶段已完成 ✓ · 点击回看"
- [x] T022 [P] [US2] 修改 `frontend/src/components/stock-analysis/AgentReportCard.tsx`：统一卡片结构——角色标识行（头像图标+角色名称+状态标签+时间戳from store.agentCompletedAt）、结论摘要行（extractFirstSentence 加粗）、详情入口"查看详细推理"（默认折叠 Collapse）、展开详情区（全量文本+独立滚动 max-height）；运行态显示头像呼吸动画+思考文案+脉冲进度条；所有文本经 highlightNumbers 处理
- [x] T023 [P] [US2] 修改 `frontend/src/pages/StockAnalysisPage.tsx` 顶部步骤条：深度分析4步骤（分析师→辩论→决策→风险）、快速分析1步骤（分析师）；当前阶段呼吸光效+CSS transition 0.3s，已完成打勾，未开始置灰
- [x] T024 [P] [US2] 修改 `frontend/src/pages/StockAnalysisPage.tsx` "停止分析"按钮：点击后 Modal.confirm 二次确认（标题"确认停止当前分析？"，内容"已生成部分将保留在分析记录中。"）；确认后停止 SSE 流

**Checkpoint**: 分析执行界面快速/深度统一体验就绪，阶段联动+折叠回看+全量推理+停止确认全部可工作

---

## Phase 5: User Story 3 - 分析结果结构化呈现 (Priority: P2)

**Goal**: 分析完成后右侧面板展示结构化投研报告：概要→决策→分析师报告（独立卡片）→辩论分栏→风险卡片，数字高亮，合规提示恒常置底

**Independent Test**: 完成深度分析后验证完整信息架构（5个区域），完成快速分析后验证精简架构（概要+决策+2位分析师），卡片样式一致

### Implementation for User Story 3

- [x] T025 [US3] 修改 `frontend/src/pages/StockAnalysisPage.tsx` Done 态信息架构：深度分析按顺序渲染 SummaryCard → DecisionCard → AgentReportCard×4（网格布局）→ DebateTimeline → RiskAssessmentSection → AnalysisHistoryList；快速分析渲染 SummaryCard → DecisionCard → AgentReportCard×2；合规提示 absolute 置底（position: absolute; bottom: 0; pointerEvents: none; 渐变背景; z-index: 10）
- [x] T026 [P] [US3] 修改 `frontend/src/components/stock-analysis/DecisionCard.tsx`：风险评分色阶改为4级（0-30绿/31-60黄/61-80橙/81-100红），Progress showInfo=false + 数字并行展示（右侧带颜色数值），决策依据文本经 highlightNumbers 处理
- [x] T027 [P] [US3] 修改 `frontend/src/components/stock-analysis/DebateTimeline.tsx`：投资辩论区按轮次配对 CSS Grid 分栏（`1fr auto 1fr`），看多绿色主题左栏+看空红色主题右栏+渐变中线，研究主管总结置顶（蓝色卡片+加粗）；风险辩论区同理（激进黄左+保守蓝右+中立居中通栏），风险裁决官总结置顶（靛蓝卡片）；所有文本数字高亮
- [x] T028 [P] [US3] 修改 `frontend/src/components/stock-analysis/RiskAssessmentSection.tsx`：5个风险角色独立卡片（2x2网格），每张含角色头像+名称+状态时间戳+内容；交易决策官内容取自 decision.reasoning；其余角色从 debates 按 speaker 过滤合并多轮内容；无内容显示"暂无输出"；文本数字高亮
- [x] T029 [US3] 修改 `frontend/src/pages/StockAnalysisPage.tsx` "重新分析"按钮：改为 Modal.confirm 二次确认（标题"确认重新分析？"，内容"当前结果将保留在分析记录中。"）

**Checkpoint**: 结构化报告呈现完整，深度/快速两种模式的结果展示就绪

---

## Phase 6: User Story 4 - 分析增量存档 (Priority: P3)

**Goal**: 后端每阶段完成时自动保存分析数据到数据库，支持 in_progress/completed/stopped 三态

**Independent Test**: 发起分析后在数据库中检查记录创建和增量更新；停止分析后检查状态为 stopped 且已完成阶段数据保留

### Implementation for User Story 4

- [x] T030 [US4] 在 `backend/app/application/use_cases/stock_analysis_use_case.py` 中完善增量存档逻辑：分析师阶段完成后更新 analysis_data.agents；辩论阶段完成后更新 analysis_data.debates；决策产出后更新 analysis_data.decision；全流程完成后设置 title/summary/industries 并 status="completed"；确保 StockAnalysisGraph 流式 yield 和数据库更新不互相阻塞
- [x] T031 [P] [US4] 在 `backend/app/routers/analysis.py` 中修改 `/api/analysis/stock-recent` 端点：将直接 SQL 查询改为通过 ArticleRepository 查询，增加 status 字段返回，遵循分层架构
- [x] T032 [US4] 运行并验证后端单元测试 `pytest backend/tests/unit/test_analysis_archive.py -v`：覆盖创建记录（status=in_progress）、增量更新 analysis_data、完整流程完成（status=completed）、中途停止（status=stopped）

**Checkpoint**: 后端增量存档完整工作，单元测试通过

---

## Phase 7: User Story 5 - 分析记录列表页与详情回看 (Priority: P4)

**Goal**: 新增"分析记录"菜单和列表页，点击"查看详情"复用分析页展示完整存档报告，进行中的记录可接续流式输出

**Independent Test**: 通过侧边栏进入分析记录列表，验证列表排序和状态标识，点击"查看详情"跳转并完整还原结构化报告

### Implementation for User Story 5

- [x] T033 [P] [US5] 新建 `frontend/src/pages/AnalysisRecordsPage.tsx`：页面标题"分析记录"；调用 `stockAnalysisService.listAnalysisRecords` 获取所有记录；按更新时间倒序排列；每条记录卡片展示：标的名称/代码（从 stocks[0] 获取）、分析模式标签（快速/深度，从 analysis_data.mode 读取）、微型进度条（计算已完成阶段数/总阶段数）、状态标识（🟢已完成/🟡进行中/⚪已停止）、最后更新时间、"查看详情"按钮；点击跳转 `/stock-analysis?recordId=xxx`；无记录时显示 Empty（"暂无分析记录" + "开始你的第一次个股深度分析" + "去分析" Link 按钮）
- [x] T034 [P] [US5] 修改 `frontend/src/App.tsx`：新增路由 `path="/analysis-records"` 指向 `AnalysisRecordsPage`
- [x] T035 [P] [US5] 修改 `frontend/src/components/layout/AppLayout.tsx`：在 menuItems 数组中"个股分析"（key="/stock-analysis"）下方新增菜单项 `{ key: "/analysis-records", icon: FileSearchOutlined, label: "分析记录" }`
- [x] T036 [US5] 修改 `frontend/src/pages/StockAnalysisPage.tsx` 实现查看模式：在组件初始化时检查 URL 参数 `recordId`；若存在 recordId，调用 `stockAnalysisService.getAnalysisRecord(recordId)` 获取存档数据；调用 `store.loadFromRecord(data)` 填充 store（设置 viewMode=true, analysisState="done", 填充 agentReports/debates/decision/title/summary 等）；查看模式下不渲染"停止分析"按钮（或置灰）；若 record 的 status 为 in_progress，建立 SSE 连接接续接收
- [x] T037 [P] [US5] 修改 `frontend/src/components/stock-analysis/AnalysisHistoryList.tsx`：点击记录跳转改为 `/stock-analysis?recordId=${item.id}`（而非原来的 `/knowledge/articles/${item.id}`）；保持 pageSize=3 和空状态文案"暂无历史分析记录"

**Checkpoint**: 分析记录列表页和详情回看功能完整，"分析→存档→回看"闭环打通

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: 编译验证、动画一致性和端到端验证

- [x] T038 运行 `cd frontend && npx tsc --noEmit` 确认所有修改文件零编译错误
- [x] T039 全局 CSS 动画一致性检查：确认 `agentBreath`、`agentPulse`、`pulseProgress`、`thinkingDots`、`blink` 所有 keyframes 定义在 `StockAnalysisPage.tsx` 的 `<style>` 标签中且无冲突
- [x] T040 运行 `cd backend && python -m pytest tests/unit/test_analysis_archive.py -v` 确认后端测试通过
- [x] T041 视觉验证：启动前后端，完整走一遍深度分析流程（启动页→分析执行→结果呈现→记录列表→详情回看），确认端到端体验

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 (Entity/Repo/Store ready)
- **US1 启动配置页 (Phase 3)**: Depends on Phase 1 (Store + textUtils)
- **US2 实时可视化 (Phase 4)**: Depends on Phase 1. Independent of US1 but US1 provides the entry page
- **US3 结构化呈现 (Phase 5)**: Depends on Phase 1. Independent of US1/US2 but builds on US2's running state
- **US4 增量存档 (Phase 6)**: Depends on Phase 1 + Phase 2 (Repo + UseCase ready)
- **US5 记录列表与详情 (Phase 7)**: Depends on Phase 1 + Phase 2 (API + Service ready) + Phase 5 (UI components reuse)
- **Polish (Phase 8)**: Depends on all user stories being complete

### User Story Dependencies

- **US1 (P0)**: Depends on T006 (Store) + T007 (textUtils)
- **US2 (P1)**: Depends on T006 (Store) + T020-T024
- **US3 (P2)**: Depends on T006 (Store) + T007 (textUtils). Reuses US2 components
- **US4 (P3)**: Depends on T001-T005 (Backend data path) + T008-T010 (Repository)
- **US5 (P4)**: Depends on T012-T013 (Frontend types + service) + T033-T037

### Within Each User Story

- US1: T015/T016/T017/T018 are independent [P], T019 depends on all of them
- US2: T020/T022/T023/T024 are independent [P], T021 follows T020
- US3: T026/T027/T028 are independent [P], T025 depends on them, T029 is independent
- US4: T030 is the core, T031 independent, T032 follows T030
- US5: T033/T034/T035/T037 are independent [P], T036 depends on T033

### Parallel Opportunities

- **Phase 1**: T001+T002 → T003 (after models), T004+T005+T006+T007 can run in parallel
- **Phase 2**: T009+T010 sequential, T011 depends on T010, T012+T013+T014 parallel with backend
- **Phase 3 (US1)**: T015+T016+T017+T018 can run in parallel (4 different new files)
- **Phase 4 (US2)**: T020 → T021, T022+T023+T024 parallel
- **Phase 5 (US3)**: T026+T027+T028 parallel, then T025, T029 parallel
- **Phase 6 (US4)**: T030 → T032, T031 parallel
- **Phase 7 (US5)**: T033+T034+T035+T037 parallel, then T036
- **Cross-story**: US1+US2+US3 can partially parallel (different UI areas); US4 (backend) can run parallel with US1-US3 (frontend)

---

## Parallel Example: Phase 1 + Phase 2 (最大并行批次)

```bash
# Phase 1 - sequential chain:
Task: "T001 添加 Article Entity 字段"
Task: "T002 添加 AnalysisArticle Model status 列"
Task: "T003 创建 Alembic 迁移"
# Then in parallel:
Task: "T004 修改 mysql_article_repo save/_to_entity"
Task: "T005 修改 article_dto"
Task: "T006 扩展 stockAnalysisStore"
Task: "T007 确认 textUtils"

# Phase 2 - backend chain + frontend parallel:
Task: "T009-T010 实现 update_analysis_data"
Task: "T008 StockAnalysisUseCase 增量存档"
Task: "T011 新增记录列表/详情端点"
# Parallel:
Task: "T012 前端类型定义"
Task: "T013 前端 Service API"
Task: "T014 后端单元测试"
```

---

## Implementation Strategy

### MVP First (User Story 1 + 2 Only)

1. Complete Phase 1: Setup (T001-T007)
2. Complete Phase 2: Foundational (T008-T014)
3. Complete Phase 3: US1 启动配置页 (T015-T019)
4. Complete Phase 4: US2 实时可视化 (T020-T024)
5. **STOP and VALIDATE**: 完整走一遍快速/深度分析流程，验证启动页→执行页→结果展示
6. Deploy/demo if ready

### Incremental Delivery

1. Setup + Foundational → 后端数据通路+前端基础设施就绪
2. Add US1 → 启动配置页双栏布局 → Deploy/Demo
3. Add US2 → 实时可视化+阶段联动 → Deploy/Demo
4. Add US3 → 结构化报告呈现 → Deploy/Demo
5. Add US4 → 后端增量存档 → Deploy/Demo
6. Add US5 → 记录列表+详情回看 → Deploy/Demo
7. Polish → 编译验证+测试+端到端体验

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup (Phase 1) together
2. Once Setup done, split:
   - Developer A (Backend): Phase 2 (T008-T014) → Phase 6 (US4, T030-T032)
   - Developer B (Frontend US1+US2): Phase 3 (T015-T019) → Phase 4 (T020-T024)
   - Developer C (Frontend US3+US5): Phase 5 (T025-T029) → Phase 7 (T033-T037)
3. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Backend changes follow Router → Application → Domain → Infrastructure layering
- Frontend changes follow Page → Component → Service → Store layering
