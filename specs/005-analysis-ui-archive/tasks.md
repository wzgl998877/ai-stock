# Tasks: 个股分析界面展示优化与存档

**Input**: Design documents from `/specs/005-analysis-ui-archive/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: 本功能为纯前端 UI 优化，未明确要求测试任务。通过 `tsc --noEmit` 编译检查和视觉验证。

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Web app**: `frontend/src/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: 创建共享工具函数和 Store 扩展，为所有 User Story 提供基础

- [x] T001 新建文本工具模块 `frontend/src/utils/textUtils.tsx`：实现 `extractFirstSentence`（首句切分）、`extractRemainingText`（剩余文本）、`highlightNumbers`（财务数字高亮，匹配百分比和价格格式）
- [x] T002 扩展 Zustand Store `frontend/src/store/stockAnalysisStore.ts`：新增 `agentCompletedAt: Record<string, number>` 字段，修改 `updateAgentStatus` 方法在 `status === "done"` 时记录 `Date.now()` 时间戳，确保 `startAnalysis` 重置时清空 `agentCompletedAt`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 无独立阻塞性任务。Phase 1 完成后即可开始 User Story 实施。

**Checkpoint**: `textUtils.tsx` 工具函数就绪，Store `agentCompletedAt` 字段就绪

---

## Phase 3: User Story 1 - 分析过程实时可视化 (Priority: P1) 🎯 MVP

**Goal**: 左侧 Agent 进度面板以统一图标、连接线、阶段联动的方式实时展示 12 个 Agent 的运行状态，让用户感受到"投研会议正在召开"

**Independent Test**: 选择一只股票发起深度分析，观察 12 个 Agent 从"就绪"逐一进入"分析中"再到"已完成"的全过程，验证左侧状态图标统一、连接线清晰、顶部步骤条平滑联动

### Implementation for User Story 1

- [x] T003 [P] [US1] 重构 `frontend/src/components/stock-analysis/AgentProgressPanel.tsx`：引入统一状态图标（ClockCircleOutlined=就绪/LoadingOutlined=分析中/CheckCircleFilled=已完成/CloseCircleFilled=失败），每个 Agent 行显示对应图标+状态文字+时间戳（从 `agentCompletedAt` 读取）
- [x] T004 [P] [US1] 在 `AgentProgressPanel.tsx` 中添加节点间 CSS 竖线连接：同一阶段内非最后一个 Agent 下方添加绝对定位 `div`（`width: 1px`），颜色按状态动态变化（done=绿/running=蓝/pending=灰）
- [x] T005 [US1] 在 `AgentProgressPanel.tsx` 中添加阶段间渐变分隔线：每个阶段（非最后一个）底部添加 `linear-gradient(to right, transparent, #e5edf5, transparent)` 水平线
- [x] T006 [P] [US1] 修改 `frontend/src/pages/StockAnalysisPage.tsx` 顶部步骤条联动：确认 Steps 组件 `className="analysis-phase-steps"` + CSS transition `0.3s ease`，当前阶段呼吸动画 `agentBreath`，已完成阶段 `opacity: 0.5`，未开始阶段置灰

**Checkpoint**: 左侧面板 12 个 Agent 统一状态图标+连接线+阶段分隔线就绪，顶部步骤条与左侧联动

---

## Phase 4: User Story 2 - 分析结果结构化呈现 (Priority: P2)

**Goal**: 分析完成后右侧面板展示结构化投研报告：摘要前置+折叠、辩论分栏对比、数字高亮、色阶条、风险角色卡片化

**Independent Test**: 完成一次深度分析后，验证右侧面板信息架构完整性：概要→决策→分析师报告（摘要加粗+折叠）→辩论分栏→风险卡片→历史

### Implementation for User Story 2

- [x] T007 [P] [US2] 重构 `frontend/src/components/stock-analysis/AgentReportCard.tsx`：使用 `extractFirstSentence` 提取首句加粗展示为"核心结论"，使用 `extractRemainingText` 获取剩余内容默认折叠（Collapse），所有文本经 `highlightNumbers` 处理，底部显示统一状态图标+时间戳
- [x] T008 [P] [US2] 重写 `frontend/src/components/stock-analysis/DebateTimeline.tsx`：投资辩论区按轮次配对分栏（CSS Grid `1fr auto 1fr`），看多绿色主题左栏+看空红色主题右栏+渐变中线，研究主管总结置顶于辩论区上方（蓝色卡片+加粗）；风险辩论区同理（激进黄左+保守蓝右+中立居中通栏），风险裁决官总结置顶（靛蓝卡片+加粗）；所有文本数字高亮
- [x] T009 [P] [US2] 修改 `frontend/src/components/stock-analysis/DecisionCard.tsx`：风险评分色阶条改为 4 级（0-30 绿/31-60 黄/61-80 橙/81-100 红），Progress 组件 `showInfo=false` + 数字并行展示（右侧带颜色的数值），决策依据文本经 `highlightNumbers` 处理
- [x] T010 [P] [US2] 新建 `frontend/src/components/stock-analysis/RiskAssessmentSection.tsx`：5 个风险角色（交易决策官/激进派/保守派/中立派/风险裁决官）各自独立卡片，2x2 网格布局，每张卡片含角色头像+名称+状态时间戳+内容，交易决策官内容取自 `decision.reasoning` 或 `agentReports.trader`，其余角色从 `debates` 按 `speaker` 过滤合并多轮内容，无内容显示"暂无输出"，文本数字高亮
- [x] T011 [US2] 修改 `frontend/src/pages/StockAnalysisPage.tsx` Done 态信息架构：在辩论时间线之后、历史分析之前插入 `RiskAssessmentSection` 组件（仅 full 模式），确认完整阅读流：概要→决策→分析师报告→辩论→风险评估→历史

**Checkpoint**: 右侧面板结构化呈现完整，摘要前置+折叠+辩论分栏+色阶条+风险卡片全部就绪

---

## Phase 5: User Story 3 - 分析记录与详情查看 (Priority: P3)

**Goal**: 历史分析区域显示最近 3 条记录可跳转详情页，"重新分析"二次确认，合规提示恒常置底

**Independent Test**: 分析完成后查看历史区域（3 条+空状态），点击记录跳转详情页，点击"重新分析"弹出确认弹窗，合规提示始终可见

### Implementation for User Story 3

- [x] T012 [P] [US3] 修改 `frontend/src/components/stock-analysis/AnalysisHistoryList.tsx`：API 请求 `page_size` 从 10 改为 3，空状态文案改为"暂无历史分析记录"
- [x] T013 [P] [US3] 修改 `frontend/src/pages/StockAnalysisPage.tsx`：`handleReset` 改为 `Modal.confirm` 二次确认（标题"确认重新分析？"，内容"当前结果将保留在历史记录中。"），需要从 antd 引入 Modal
- [x] T014 [US3] 确认 `frontend/src/pages/StockAnalysisPage.tsx` 合规提示置底：`position: absolute; bottom: 0` + `pointerEvents: none` + `background: linear-gradient(transparent, #ffffff 30%)` + `z-index: 10` + 字色 `#c0c6cf` + 字号 `11px`，`left` 值根据 `showSidebar` 动态偏移

**Checkpoint**: 历史记录3条限制、重新分析确认弹窗、合规提示置底全部就绪

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: 编译验证和一致性检查

- [x] T015 运行 `./node_modules/.bin/tsc --noEmit` 确认所有修改文件零编译错误
- [x] T016 全局 CSS 动画一致性检查：确认 `agentBreath`、`agentPulse`、`pulseProgress`、`thinkingDots`、`blink` 所有 keyframes 定义在 `StockAnalysisPage.tsx` 的 `<style>` 标签中且无冲突
- [ ] T017 视觉验证：启动前端 `npm run dev`，完整走一遍深度分析流程，确认左侧进度+右侧内容+底部合规提示的端到端体验

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: No blocking tasks - Phase 1 completion suffices
- **User Story 1 (Phase 3)**: Depends on Phase 1 (textUtils + Store extension)
- **User Story 2 (Phase 4)**: Depends on Phase 1 (textUtils + Store extension). US2 tasks are independent of US1 but can proceed in parallel
- **User Story 3 (Phase 5)**: Depends on Phase 1. US3 tasks are independent of US1/US2
- **Polish (Phase 6)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Depends on T001 (textUtils for formatTime) + T002 (Store agentCompletedAt)
- **User Story 2 (P2)**: Depends on T001 (textUtils for extractFirstSentence/extractRemainingText/highlightNumbers) + T002 (Store agentCompletedAt)
- **User Story 3 (P3)**: Depends on T002 (Store). Minimal overlap with US1/US2

### Within Each User Story

- US1: T003/T004/T006 are independent [P], T005 can follow T004
- US2: T007/T008/T009/T010 are all independent [P], T011 depends on T010 (imports RiskAssessmentSection)
- US3: T012/T013/T014 are all independent [P]

### Parallel Opportunities

- **Phase 1**: T001 + T002 can run in parallel
- **Phase 3 (US1)**: T003 + T004 + T006 can run in parallel (different concerns in same file — coordinate carefully)
- **Phase 4 (US2)**: T007 + T008 + T009 + T010 can run in parallel (4 different files)
- **Phase 5 (US3)**: T012 + T013 + T014 can run in parallel (2 different files + 1 verification)
- **Cross-story**: US1 + US2 + US3 can theoretically run in parallel after Phase 1

---

## Parallel Example: User Story 2 (最大并行批次)

```bash
# Launch all 4 implementation tasks together (different files):
Task: "T007 重构 AgentReportCard.tsx (摘要前置+折叠+高亮)"
Task: "T008 重写 DebateTimeline.tsx (分栏对比+置顶)"
Task: "T009 修改 DecisionCard.tsx (色阶条+数字并行)"
Task: "T010 新建 RiskAssessmentSection.tsx (风险角色卡片化)"

# Then sequentially:
Task: "T011 修改 StockAnalysisPage.tsx (整合 RiskAssessmentSection)"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001 + T002)
2. Complete Phase 3: User Story 1 (T003-T006)
3. **STOP and VALIDATE**: 发起一次深度分析，验证左侧 Agent 进度面板的实时可视化效果
4. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup → 工具函数和 Store 就绪
2. Add User Story 1 → 左侧进度可视化 → Deploy/Demo (MVP!)
3. Add User Story 2 → 右侧结构化呈现 → Deploy/Demo
4. Add User Story 3 → 历史记录+合规+确认弹窗 → Deploy/Demo
5. Polish → 编译验证+动画一致性+端到端体验

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup together (T001 + T002)
2. Once Setup is done:
   - Developer A: User Story 1 (T003-T006) — AgentProgressPanel + Steps
   - Developer B: User Story 2 (T007-T011) — ReportCard + Debate + Decision + Risk
   - Developer C: User Story 3 (T012-T014) — History + Confirm + Disclaimer
3. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- All modifications are pure frontend — no backend changes required
