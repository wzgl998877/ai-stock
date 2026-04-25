# UI Component Contracts: 个股分析界面展示优化与存档

**Feature Branch**: `005-analysis-ui-archive`
**Date**: 2025-04-25

本功能为纯前端 UI 优化，不涉及新的 API 端点或外部接口。以下定义各组件的 props 接口契约。

## Component Contracts

### textUtils (工具模块)

```
extractFirstSentence(text: string): string
  - 输入: 任意文本
  - 输出: 首句内容（以句号/问号/感叹号分割的第一段）
  - 空输入返回空字符串

extractRemainingText(text: string): string
  - 输入: 任意文本
  - 输出: 首句之外的剩余内容
  - 首句即全文时返回空字符串

highlightNumbers(text: string): ReactNode
  - 输入: 任意文本
  - 输出: React 节点数组，数字部分用 <strong> 包裹高亮
  - 匹配模式: 百分比(±xx%) + 价格(xx.xx)
```

### AgentReportCard (已修改)

```
Props:
  agent: string              // Agent 标识
  summary: string            // 后端返回的摘要文本
  fullReport?: string        // 可选的完整报告
  isRunning?: boolean        // 是否运行中
  thinkingMessage?: string   // 思考中提示文案
  dataSource?: string        // 数据源标签
  gridMode?: boolean         // 网格模式（Done态）

Behavior:
  - 运行态: 显示头像呼吸动画 + 思考文案 + 脉冲进度条
  - 完成态: 首句加粗展示 + 剩余内容折叠
  - 状态图标: 从 store 读取 agentStatuses 和 agentCompletedAt
  - 数字高亮: 所有文本经 highlightNumbers 处理
```

### DebateTimeline (已修改)

```
Props:
  debates: DebateEvent[]       // 辩论事件数组
  showRiskDebate?: boolean     // 是否显示风险辩论（默认 true）

Behavior:
  - 投资辩论: 研究主管总结置顶，看多/看空按轮次分栏
  - 风险辩论: 风险裁决官总结置顶，激进/保守分栏，中立居中
  - 所有文本数字高亮
```

### RiskAssessmentSection (新增)

```
Props:
  debates: DebateEvent[]         // 辩论事件数组
  decision?: DecisionEvent       // 投资决策（含 reasoning）

Behavior:
  - 5 个角色独立卡片（2x2网格）
  - 交易决策官: 内容来自 decision.reasoning 或 agentReports.trader
  - 其余角色: 内容从 debates 按 speaker 过滤，多轮合并
  - 无内容时显示"暂无输出"
  - 数字高亮
```

### DecisionCard (已修改)

```
Props:
  decision: DecisionEvent        // 投资决策数据

Behavior:
  - 风险评分色阶: 0-30绿 / 31-60黄 / 61-80橙 / 81-100红
  - Progress + 数字并行展示
  - 决策依据文本数字高亮
```

### AgentProgressPanel (已修改)

```
Props: 无（从 store 直接读取）

Behavior:
  - 统一状态图标: 就绪=灰时钟 / 分析中=蓝旋转 / 已完成=绿对勾 / 失败=红叉
  - 节点间 CSS 竖线连接
  - 已完成阶段 opacity 0.65
  - 阶段间渐变分隔线
```

### AnalysisHistoryList (已修改)

```
Props:
  stockCode: string       // 股票代码
  onRefresh?: number      // 递增触发刷新

Behavior:
  - API pageSize 改为 3
  - 空状态文案: "暂无历史分析记录"
  - 点击跳转: /knowledge/articles/{id}
```

### StockAnalysisPage (已修改)

```
Behavior:
  - "重新分析"加 Modal.confirm 二次确认
  - Done 态信息架构: 概要 → 决策 → 分析师报告 → 辩论 → 风险评估 → 历史
  - 合规提示 absolute 置底
```

## Store Contract (stockAnalysisStore 扩展)

```
New State:
  agentCompletedAt: Record<string, number>  // agent -> 完成时间戳(ms)

Modified Methods:
  updateAgentStatus(event):
    - 当 event.status === "done" 时自动记录 Date.now()
    - 同步更新 currentPhase
```
