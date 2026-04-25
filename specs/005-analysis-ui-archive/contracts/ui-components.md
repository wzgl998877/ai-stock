# UI Component Contracts: 个股分析界面展示优化与存档

**Feature Branch**: `005-analysis-ui-archive`
**Created**: 2025-04-25

以下定义各组件的 props 接口契约和行为规范。

## 新增组件

### SystemStatusBar

```
位置: 页面顶部，高度不超过 40px
Props: 无（静态展示）
Behavior:
  - 三项信息用竖线分隔：系统在线（绿色脉冲圆点）| 市场状态（交易中/已收盘）| 数据已同步（灰色芯片+打勾）
  - 市场状态根据 A 股交易时间动态切换（9:30-15:00 交易中，其余已收盘）
  - 初期版本：系统在线和数据同步为静态展示
```

### AgentTopologyPreview

```
位置: 启动配置页右侧预览区
Props:
  analysisMode: "quick" | "full"   // 当前分析模式
Behavior:
  - 4 个节点纵向排列：技术面分析师、基本面分析师、新闻舆情哨兵、风险评估官
  - 节点为圆角矩形卡片，含图标(emoji)和名称
  - 节点间用虚线连接，标注关系词（"交叉辩论"、"数据联动"等）
  - 快速模式：仅前两位亮起，后两位置灰
  - 深度模式：全部亮起，外层蓝色光晕边框
```

### ModeSelectionCards

```
位置: 启动配置页左侧配置区
Props:
  value: "quick" | "full"
  onChange: (mode) => void
Behavior:
  - 两张可点选的模式卡片，上下排列
  - 快速：⚡ 快速分析 · 2位分析师 · 约30-60秒
  - 深度：⚡ 深度分析 · 4位分析师+辩论+风评 · 约3-5分钟
  - 选中卡片：蓝色高亮边框 + 微蓝背景
  - 未选中：灰色边框
```

### HistoryQuickEntry

```
位置: 启动配置页右侧预览区（拓扑图下方）
Props:
  stockCode: string
  onSelect: (recordId: string) => void
Behavior:
  - 展示最近 3 条历史分析记录
  - 每条显示标题 + 日期 + 决策标签
  - 点击跳转到详情页（/stock-analysis?recordId=xxx）
  - 无记录时不渲染
```

### AnalysisRecordsPage

```
位置: /analysis-records 路由页面
Props: 无（独立页面）
Behavior:
  - 所有分析记录按更新时间倒序排列
  - 每条记录卡片展示：标的名称/代码、分析模式标签、微型进度条、状态标识（🟢已完成/🟡进行中/⚪已停止）、最后更新时间、"查看详情"按钮
  - 点击"查看详情"跳转 /stock-analysis?recordId=xxx
  - 无记录时显示空状态："暂无分析记录" + "去分析"引导按钮
```

## 修改组件

### AgentProgressPanel

```
Props: 无（从 store 直接读取）
新增行为:
  - 根据 store.analysisMode 决定渲染哪些 Agent
    - quick: 1 阶段 2 个 Agent（技术面+基本面）
    - full: 4 阶段 12 个 Agent
  - 统一状态图标: 就绪=灰时钟 / 分析中=蓝旋转 / 已完成=绿对勾 / 失败=红叉
  - 节点间 CSS 竖线连接
  - 已完成阶段 opacity 0.65
  - 阶段间渐变分隔线
```

### AgentReportCard

```
Props:
  agent: string
  summary: string
  isRunning?: boolean
  thinkingMessage?: string
  gridMode?: boolean
Behavior:
  - 运行态: 头像呼吸动画 + 思考文案 + 脉冲进度条
  - 完成态: 首句加粗 + 剩余内容折叠（Collapse）+ 数字高亮
  - 角色标识行: 头像图标 + 角色名称 + 状态标签 + 时间戳
  - 查看详细推理: 展开全量文本，独立滚动
```

### DebateTimeline

```
Props:
  debates: DebateEvent[]
  showRiskDebate?: boolean
Behavior:
  - 投资辩论: 研究主管总结置顶，看多/看空按轮次分栏（CSS Grid）
  - 风险辩论: 风险裁决官总结置顶，激进/保守分栏，中立居中
  - 所有文本数字高亮
```

### DecisionCard

```
Props:
  decision: DecisionEvent
Behavior:
  - 风险评分色阶: 0-30绿 / 31-60黄 / 61-80橙 / 81-100红
  - Progress + 数字并行展示
  - 决策依据文本数字高亮
```

### RiskAssessmentSection

```
Props:
  debates: DebateEvent[]
  decision?: DecisionEvent
Behavior:
  - 5 个角色独立卡片（2x2网格）
  - 交易决策官: decision.reasoning 或 agentReports.trader
  - 其余角色: debates 按 speaker 过滤，多轮合并
  - 无内容时显示"暂无输出"
  - 数字高亮
```

### AnalysisHistoryList

```
Props:
  stockCode: string
  onRefresh?: number
Behavior:
  - API pageSize = 3
  - 空状态文案: "暂无历史分析记录"
  - 点击跳转: /stock-analysis?recordId={id}
```

### StockAnalysisPage

```
新增状态:
  viewMode: boolean        // 是否为查看模式
  viewRecordId: string     // 查看的记录 ID

改动行为:
  Idle 态:
    - 双栏布局（左 40-45% + 右 55-60%）
    - 顶部 SystemStatusBar
    - 左侧: StockSearchInput + ModeSelectionCards + 启动按钮 + 合规提示
    - 右侧: AgentTopologyPreview + HistoryQuickEntry
  Running 态:
    - 快速/深度统一布局（左面板+右内容区）
    - AgentProgressPanel 根据 analysisMode 渲染
  Done 态:
    - 快速: 概要→决策→2位分析师报告
    - 深度: 概要→决策→4位分析师→辩论→风险→历史
    - 合规提示 absolute 置底
  ViewMode:
    - 从 recordId 加载存档数据
    - 跳过 idle 态，直接渲染结果
    - 停止按钮置灰/隐藏
  handleReset:
    - Modal.confirm 二次确认
```

## Store Contract (stockAnalysisStore 扩展)

```
New State:
  viewMode: boolean                 // 是否查看模式
  viewRecordId: string              // 查看的记录 ID
  agentCompletedAt: Record<string, number>  // agent -> 完成时间戳(ms)

New Actions:
  loadFromRecord(data: AnalysisRecordData):
    - 从存档数据填充 agentReports, debates, decision, title, summary 等
    - 设置 viewMode = true
    - 设置 analysisState = "done"

Modified Actions:
  updateAgentStatus(event):
    - 当 event.status === "done" 时自动记录 Date.now() 到 agentCompletedAt
  startAnalysis():
    - 重置时清空 agentCompletedAt
    - 重置 viewMode 和 viewRecordId
```

## Service Contract (stockAnalysisService 扩展)

```
New Methods:
  getAnalysisRecord(recordId: string): Promise<AnalysisRecordDetail>
    - GET /api/analysis/records/{recordId}
    - 返回完整 analysis_data

  listAnalysisRecords(params?: { page?: number, pageSize?: number, status?: string }): Promise<AnalysisRecordList>
    - GET /api/analysis/records
    - 返回分页记录列表
```

## 路由变更 (App.tsx)

```
新增路由:
  /analysis-records → AnalysisRecordsPage

修改路由:
  /stock-analysis 支持 ?recordId=xxx 查询参数
```

## 导航变更 (AppLayout.tsx)

```
新增菜单项:
  key: "/analysis-records"
  label: "分析记录"
  icon: FileSearchOutlined 或 UnorderedListOutlined
  位置: "个股分析"下方
```
