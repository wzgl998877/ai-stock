# Research: 个股分析界面展示优化与存档

**Feature Branch**: `005-analysis-ui-archive`
**Created**: 2025-04-25

## 研究决策

### R1: 分析记录存储策略

**Decision**: 扩展现有 `t_analysis_article` 表，启用已存在的 `analysis_data` JSON 字段，新增 `status` 列。

**Rationale**:
- 数据库模型 `AnalysisArticle` 已定义 `analysis_data` (JSON) 和 `article_type` (String) 字段，但 Domain Entity 和 Repository 层未打通
- `article_type` 已支持 `"stock_analysis"` 值，可用于区分分析类型
- 新增 `status` 列（String(20): in_progress/completed/stopped）支持增量存档的三态管理
- 复用现有知识库基础设施（列表查询、详情查询），避免创建新表

**Alternatives considered**:
- 创建独立的 `t_analysis_record` 表 → 过度设计，与现有知识库体系割裂
- 将 status 放入 `analysis_data` JSON → 查询效率低，无法直接 WHERE 过滤

### R2: 增量存档实现机制

**Decision**: 在 `StockAnalysisUseCase` 中，分析流程开始时创建 article 记录（status=in_progress），每个阶段完成时更新 `analysis_data` JSON 字段。

**Rationale**:
- `StockAnalysisUseCase` 已有完整的阶段数据（agent_reports、debates、decision）
- 在 yield SSE 事件的同时写入数据库，不影响 SSE 流
- 利用 `analysis_data` JSON 字段存储完整结构化数据：
  ```json
  {
    "mode": "full",
    "agents": { "market_analyst": { "summary": "...", "completed_at": 1714036800 } },
    "debates": [{ "speaker": "bull_researcher", "round": 1, "content": "..." }],
    "decision": { "action": "买入", "target_price": 0, "confidence": 0.8, "risk_score": 0.3, "reasoning": "..." },
    "title": "...",
    "summary": "...",
    "industries": ["..."]
  }
  ```

**Alternatives considered**:
- 前端触发保存 → 不可靠，页面关闭即丢失；当前前端也未调用保存接口
- 消息队列异步保存 → 过度设计，增加复杂度

### R3: 分析详情页实现方式

**Decision**: 复用 `StockAnalysisPage` 组件，通过路由参数 `/stock-analysis?recordId=xxx` 进入"查看模式"，从 API 加载存档数据填充 Store。

**Rationale**:
- 结构化报告的 UI 组件（AgentReportCard、DebateTimeline、DecisionCard 等）完全可复用
- Store 添加 `viewMode: boolean` 和 `viewRecordId: string` 状态
- 查看模式下：不显示左侧配置/启动区域，直接渲染结构化报告；不显示"停止分析"按钮

**Alternatives considered**:
- 创建独立的 `AnalysisDetailPage` → 组件重复，维护成本高
- 复用知识库文章详情页 → 不支持结构化展示（纯文本渲染）

### R4: 启动配置页实现策略

**Decision**: 重构 `StockAnalysisPage` 的 Idle 态，从单栏居中改为双栏布局（左配置+右预览），不创建新页面。

**Rationale**:
- 当前 Idle 态已有搜索框、模式选择和启动按钮，只需重组布局
- Agent 拓扑图作为新组件 `AgentTopologyPreview` 在右侧预览区渲染
- 系统状态栏作为新组件 `SystemStatusBar` 在页面顶部渲染
- 模式选择器从 `Radio.Group` 改为卡片式（`ModeSelectionCards` 组件）

**Alternatives considered**:
- 创建独立的启动页 → 增加路由和页面跳转，当前设计已是同页状态切换

### R5: 分析记录列表页路由与菜单

**Decision**: 新增路由 `/analysis-records` 指向 `AnalysisRecordsPage`，在侧边栏"个股分析"下方添加"分析记录"菜单项。

**Rationale**:
- 与现有路由风格一致（`/stock-analysis`、`/knowledge`）
- 菜单位置在"个股分析"下方，与核心投研功能同组
- 列表页调用后端 API 按 `article_type="stock_analysis"` 查询

**Alternatives considered**:
- 放在知识库下作为子功能 → 语义不匹配，分析记录≠知识库文章
- 弹窗形式 → 无法承载完整列表体验

### R6: 快速分析与深度分析的统一体验

**Decision**: 两种模式共享相同的执行页面和结果页面组件，通过 `analysisMode` 状态控制 Agent 数量和阶段数。

**Rationale**:
- 现有代码已有 `analysisMode: "quick" | "full"` 的区分逻辑
- `AgentProgressPanel` 根据 `analysisMode` 决定渲染哪些 Agent（quick=2, full=12）
- 右侧内容区根据当前阶段和模式决定显示哪些区块
- 结果页在快速模式下仅渲染概要+决策+2位分析师报告

**Alternatives considered**:
- 快速分析用简化页面 → 维护两套 UI，用户体验不一致

### R7: 文本首句切分与数字高亮

**Decision**: 使用正则按中文句号/英文句号/问号/感叹号切分首句，百分比和价格格式数字自动高亮。已有 `textUtils.tsx` 实现。

**Rationale**:
- 后端 `AgentReportEvent` 只提供 `summary` 字段，前端切分是零后端改动方案
- 大模型输出的摘要通常第一句就是核心结论
- 高亮正则：`[-+]?\s?\d+\.?\d*\s?%` 匹配百分比，`¥?\s?\d+\.\d{2}` 匹配价格

### R8: 辩论分栏与风险角色数据组织

**Decision**: 从 `debates` 数组按 `round` 和 `speaker` 过滤配对，CSS Grid 分栏。风险角色内容从 debates 按speaker 过滤，交易决策官从 decision.reasoning 获取。

**Rationale**:
- 后端辩论事件已包含 round 和 speaker 字段，无需改动
- 研究主管和风险裁决官内容单独提取置顶
- 无内容时显示"暂无输出"
