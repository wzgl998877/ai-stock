# Quickstart: 个股分析界面展示优化与存档

**Feature Branch**: `005-analysis-ui-archive`

## 改动范围

本功能为**纯前端 UI 优化**，不涉及后端改动。修改的文件全部在 `frontend/src/` 下。

## 涉及文件清单

### 新增文件

| 文件 | 用途 |
|------|------|
| `utils/textUtils.tsx` | 首句切分 + 数字高亮工具函数 |
| `components/stock-analysis/RiskAssessmentSection.tsx` | 风险评估角色区块化组件 |

### 修改文件

| 文件 | 改动要点 |
|------|----------|
| `store/stockAnalysisStore.ts` | 新增 `agentCompletedAt` 字段，`updateAgentStatus` 记录完成时间 |
| `components/stock-analysis/AgentReportCard.tsx` | 摘要前置+详情折叠+数字高亮+统一状态图标 |
| `components/stock-analysis/DebateTimeline.tsx` | 多空分栏对比+研究主管/裁决官置顶+数字高亮 |
| `components/stock-analysis/DecisionCard.tsx` | 风险色阶条(4级)+数字并行展示+数字高亮 |
| `components/stock-analysis/AgentProgressPanel.tsx` | 统一状态图标+节点连接线+阶段分隔线 |
| `components/stock-analysis/AnalysisHistoryList.tsx` | pageSize=3+空状态文案优化 |
| `pages/StockAnalysisPage.tsx` | 重新分析确认弹窗+风险评估区块+合规提示置底 |

## 信息架构（Done 态完整阅读流）

```
┌─ 分析概要卡片（标题+摘要+行业标签+模式标签）
├─ 投资决策（操作方向+目标价+置信度Progress+风险色阶条）
├─ 分析师报告（2x2网格，每张：摘要加粗+详情折叠+数字高亮+状态时间戳）
├─ 投资辩论（研究主管置顶 → 看多/看空按轮次分栏对比）
├─ 风险评估（5角色独立卡片网格，无输出显示"暂无输出"）
├─ 历史分析（最近3条，点击跳转详情页）
└─ 快速模式引导（仅快速模式）
```

## 验证方式

1. 启动前端 `npm run dev`
2. 进入 /stock-analysis 页面
3. 选择一只股票，发起深度分析
4. 验证左侧面板：12 个 Agent 统一图标 + 连接线 + 阶段切换动画
5. 分析完成后验证右侧面板：上述信息架构完整性
6. 点击"重新分析"验证二次确认弹窗
7. 查看历史区域验证最近 3 条记录 + 空状态
