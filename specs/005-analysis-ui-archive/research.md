# Research: 个股分析界面展示优化与存档

**Feature Branch**: `005-analysis-ui-archive`
**Date**: 2025-04-25

## R1: 文本首句切分策略

**Decision**: 前端使用正则按中文句号、英文句号、问号、感叹号切分，取第一句作为摘要，其余作为折叠详情。

**Rationale**:
- 后端 `AgentReportEvent` 只提供 `summary` 字段，没有独立的 `full_report`
- 前端切分是零后端改动的方案，符合宪法"最小变更原则"
- 大模型输出的摘要通常第一句就是核心结论，切分效果可靠

**Alternatives considered**:
- 等后端扩展字段：需要后端改动，违反"后端无需改动"的假设
- 用 NLP 模型提取：过度工程，违反 KISS 原则

## R2: 数字高亮正则模式

**Decision**: 使用 `[-+]?\s?\d+\.?\d*\s?%` 匹配百分比（含正负），`¥?\s?\d+\.\d{2}` 匹配价格格式（精确到小数点后两位）。

**Rationale**:
- 价格和百分比是最常见的财务数字，误匹配风险最低
- "3月"、"第4轮"等不含百分号或小数点后两位格式，不会被匹配
- 高亮使用主题色 `#533afd` + `fontWeight: 600`，视觉突出但不突兀

**Alternatives considered**:
- 匹配所有数字：误匹配率太高（"3月"等）
- 使用 NER 模型：过度工程

## R3: 辩论分栏数据组织

**Decision**: 从 `debates` 数组中按 `round` 和 `speaker` 过滤配对，使用 CSS Grid（`grid-template-columns: 1fr auto 1fr`）实现左右分栏 + 中线。

**Rationale**:
- 后端辩论事件已包含 `round` 和 `speaker` 字段，数据层面无需改动
- CSS Grid 是最轻量的分栏实现，不需要引入新组件库
- 研究主管（`research_manager`）和风险裁决官（`risk_judge`）的内容单独提取置顶

**Alternatives considered**:
- 使用 Ant Design Timeline：无法实现分栏效果
- 使用第三方表格组件：过度工程

## R4: 风险角色区块化数据来源

**Decision**: 风险角色的内容从 `store.debates` 数组按 `speaker` 过滤，交易决策官内容从 `store.decision.reasoning` 获取。当某角色无内容时显示"暂无输出"。

**Rationale**:
- 当前后端风险阶段的辩论内容通过 `debate` 事件推送，按 `speaker` 区分角色
- 交易决策官有独立的 `decision` 事件，`reasoning` 字段包含决策依据
- 无需新增数据结构，完全复用现有 store

**Alternatives considered**:
- 后端新增风险评估独立事件类型：需后端改动
- 将风险内容存入 agentReports：语义不准确

## R5: Agent 状态图标与连接线方案

**Decision**: 使用 Ant Design Icons（CheckCircleFilled/CloseCircleFilled/LoadingOutlined/ClockCircleOutlined）作为统一状态图标，CSS 绝对定位实现节点间竖线连接。

**Rationale**:
- Ant Design Icons 已在项目中使用，无需引入新图标库
- CSS 竖线实现：每个 Agent 行左侧加绝对定位的 `div`（`width: 1px`），颜色按状态动态变化
- 符合宪法"复用 Ant Design"要求

**Alternatives considered**:
- 使用 Ant Design Timeline 组件：布局控制不够灵活，难以实现自定义头像和状态
- SVG 绘制连接线：过度工程

## R6: 历史记录限制与存档机制

**Decision**: 前端 `page_size` 改为 3（仅请求最近 3 条），存档复用现有知识库 API（`knowledgeService.getArticles`）。

**Rationale**:
- 知识库 API 已支持按 `article_type: "stock_analysis"` 和 `stock_code` 过滤
- 无需新建存档服务，完全复用现有基础设施
- 3 条是"最近分析"区域的信息密度最优值，多了会占用页面空间

**Alternatives considered**:
- 新建独立的存档 API：过度工程，违反 KISS
- 前端缓存所有历史记录：违反数据源真实性的设计原则
