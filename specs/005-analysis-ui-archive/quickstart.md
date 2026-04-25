# Quickstart: 个股分析界面展示优化与存档

**Feature Branch**: `005-analysis-ui-archive`

## 改动范围

本功能涉及**前端 UI 重构 + 后端增量存档**。前端改动 15+ 文件，后端改动 6+ 文件。

## 涉及文件清单

### 新增文件

| 文件 | 用途 |
|------|------|
| `frontend/src/components/stock-analysis/SystemStatusBar.tsx` | 系统状态栏（在线/市场/同步） |
| `frontend/src/components/stock-analysis/AgentTopologyPreview.tsx` | Agent 协作拓扑图预览 |
| `frontend/src/components/stock-analysis/ModeSelectionCards.tsx` | 模式选择卡片（替代 Radio.Group） |
| `frontend/src/components/stock-analysis/HistoryQuickEntry.tsx` | 历史3条快捷入口 |
| `frontend/src/pages/AnalysisRecordsPage.tsx` | 分析记录列表页 |
| `backend/app/infrastructure/db/migrations/versions/xxx_add_status.py` | Alembic 迁移（status 列） |
| `backend/tests/unit/test_analysis_archive.py` | 存档相关单元测试 |

### 修改文件

**前端**：

| 文件 | 改动要点 |
|------|----------|
| `store/stockAnalysisStore.ts` | 新增 viewMode/viewRecordId/agentCompletedAt + loadFromRecord action |
| `services/stockAnalysisService.ts` | 新增 getAnalysisRecord/listAnalysisRecords API |
| `pages/StockAnalysisPage.tsx` | Idle 态双栏重构 + 执行态快速/深度统一 + Done 态结构化 + viewMode |
| `components/stock-analysis/AgentProgressPanel.tsx` | 支持快速模式2Agent + 深度模式12Agent |
| `components/stock-analysis/AgentReportCard.tsx` | 统一卡片结构（角色标识+摘要+折叠+全量推理） |
| `components/stock-analysis/DebateTimeline.tsx` | 分栏对比+置顶总结+数字高亮 |
| `components/stock-analysis/DecisionCard.tsx` | 色阶条+数字并行+数字高亮 |
| `components/stock-analysis/RiskAssessmentSection.tsx` | 5角色独立卡片 |
| `components/stock-analysis/AnalysisHistoryList.tsx` | pageSize=3+跳转详情页 |
| `components/layout/AppLayout.tsx` | 新增"分析记录"菜单项 |
| `App.tsx` | 新增 /analysis-records 路由 |
| `domain/types.ts` | 新增 AnalysisRecordDetail 等类型 |

**后端**：

| 文件 | 改动要点 |
|------|----------|
| `domain/entities/article.py` | 新增 analysis_data/article_type/status 字段 |
| `application/dtos/article_dto.py` | DTO 增加 status/analysis_mode |
| `application/use_cases/stock_analysis_use_case.py` | 每阶段完成时增量保存到 t_analysis_article |
| `infrastructure/db/models.py` | AnalysisArticle 添加 status 列 |
| `infrastructure/repositories/mysql_article_repo.py` | save/_to_entity 处理新字段 |
| `routers/analysis.py` | 新增记录列表+详情接口 |

## 页面信息架构

### Idle 态（启动配置页）

```
┌─ SystemStatusBar（系统在线 | 市场状态 | 数据已同步）
├─ 左侧配置区 (40-45%)
│  ├─ StockSearchInput（股票搜索）
│  ├─ ModeSelectionCards（快速/深度卡片选择）
│  ├─ 开始分析按钮（过渡动效）
│  └─ 合规提示
└─ 右侧预览区 (55-60%)
   ├─ AgentTopologyPreview（Agent拓扑图+模式联动）
   └─ HistoryQuickEntry（最近3条历史分析）
```

### Done 态（深度分析结果）

```
├─ 分析概要卡片
├─ 投资决策（操作方向+目标价+置信度+风险色阶条）
├─ 分析师报告（4位独立卡片，首句加粗+折叠+数字高亮）
├─ 投资辩论（研究主管置顶 → 看多/看空分栏对比）
├─ 风险评估（5角色独立卡片）
├─ 历史分析（最近3条）
└─ 合规提示（恒常置底）
```

### Done 态（快速分析结果）

```
├─ 分析概要卡片
├─ 投资决策
├─ 分析师报告（2位：技术面+基本面）
├─ 历史分析（最近3条）
└─ 合规提示（恒常置底）
```

### 分析记录列表页

```
├─ 页面标题
├─ 记录卡片列表（按更新时间倒序）
│  └─ 每条：标的+模式+进度条+状态标识+时间+查看详情按钮
└─ 空状态引导
```

## 验证方式

### 前端验证

1. `cd frontend && npm run dev`
2. 进入 /stock-analysis 验证双栏启动页布局
3. 验证系统状态栏、Agent拓扑图、模式卡片切换
4. 分别发起快速/深度分析，验证执行界面统一体验
5. 分析完成后验证结构化报告（卡片化+辩论分栏+数字高亮+色阶条）
6. 进入 /analysis-records 验证记录列表
7. 点击"查看详情"验证详情页还原完整报告

### 后端验证

1. `cd backend && alembic upgrade head` 执行迁移
2. 发起分析，检查 t_analysis_article 表中是否创建 status=in_progress 记录
3. 分析完成后检查记录是否更新为 status=completed，analysis_data 是否包含完整数据
4. 调用 GET /api/analysis/records 验证列表接口
5. 调用 GET /api/analysis/records/{id} 验证详情接口
6. `pytest tests/unit/test_analysis_archive.py -v` 运行单元测试

### 编译检查

```bash
cd frontend && npx tsc --noEmit
```
