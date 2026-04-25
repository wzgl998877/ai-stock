# Implementation Plan: 个股分析界面展示优化与存档

**Branch**: `005-analysis-ui-archive` | **Date**: 2025-04-25 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/005-analysis-ui-archive/spec.md`

## Summary

将个股分析从"表单+日志"体验升级为"AI投研指挥舱"专业体验。核心改动分为五大部分：(1) 启动配置页重构为双栏布局+Agent拓扑图预览；(2) 分析执行页统一快速/深度模式体验，左侧Agent进度+右侧阶段联动；(3) 结果页结构化报告呈现（卡片化+辩论分栏+数字高亮）；(4) 后端增量存档（每阶段自动保存到数据库）；(5) 新增分析记录列表页与详情回看。涉及前端7个新组件+6个修改组件+1个新页面+1个路由，后端4个修改文件+1个新迁移+2个新接口。

## Technical Context

**Language/Version**: TypeScript (React 18) + Python 3 (FastAPI)
**Primary Dependencies**: Ant Design 5, Zustand, @ant-design/icons (前端); SQLAlchemy 2 (async), Alembic (后端)
**Storage**: MySQL (t_analysis_article 表扩展 status 列 + analysis_data JSON 字段启用)
**Testing**: tsc --noEmit (前端编译检查); pytest (后端单元测试)
**Target Platform**: 桌面浏览器（Chrome/Edge，1920x1080+）
**Project Type**: Web application (前端 SPA + 后端 REST API)
**Performance Goals**: Agent 状态变化 0.5s 内反映；详情页 3s 内加载；动画 60fps
**Constraints**: 复用现有 SSE 事件流；分析存档需增量写入（每阶段完成即保存）
**Scale/Scope**: 1 个新页面 + 7 个新组件 + 6 个修改组件 + 后端 4 个修改文件 + 1 个新迁移

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Status | Notes |
|------|--------|-------|
| 三模块协同优先 | PASS | 改动集中在模块一（AI 分析），分析记录跳转复用个股分析页面 |
| 个人投研工具边界 | PASS | 合规提示恒常置底，"不构成投资建议"始终可见 |
| 简洁实用 (KISS) | PASS | 复用 Ant Design 组件和现有 SSE 流，不引入新依赖 |
| 技术栈合规 | PASS | React 18 + TypeScript + Ant Design 5 + Zustand + FastAPI |
| 架构红线 | PASS | 后端 Router→Application→Domain→Infrastructure；前端所有 API 经 services/ |
| 流式输出成对 | PASS | SSE 流不变，存档在后端完成不依赖前端触发 |
| UI 设计原则 | PASS | 双栏布局、卡片化、信息层级清晰 |

## Project Structure

### Documentation (this feature)

```text
specs/005-analysis-ui-archive/
├── plan.md              # 本文件
├── spec.md              # 功能规格
├── research.md          # Phase 0 研究决策
├── data-model.md        # Phase 1 数据模型
├── quickstart.md        # Phase 1 快速入门
├── contracts/
│   ├── api-endpoints.md # 后端 API 契约
│   └── ui-components.md # 前端组件契约
├── checklists/
│   └── requirements.md  # 质量检查清单
└── tasks.md             # Phase 2 任务（/speckit.tasks 生成）
```

### Source Code (repository root)

```text
# ---- 后端 ----
backend/
├── app/
│   ├── domain/
│   │   └── entities/
│   │       └── article.py                      # [修改] 添加 analysis_data/article_type/status 字段
│   ├── application/
│   │   ├── dtos/
│   │   │   └── article_dto.py                  # [修改] DTO 增加 status/analysis_mode 字段
│   │   └── use_cases/
│   │       ├── stock_analysis_use_case.py       # [修改] 每阶段完成时增量保存到 t_analysis_article
│   │       └── manage_article.py               # [修改] 支持按 article_type 查询+status 过滤
│   ├── infrastructure/
│   │   ├── db/
│   │   │   ├── models.py                       # [修改] AnalysisArticle 添加 status 列
│   │   │   └── migrations/versions/
│   │   │       └── xxx_add_status_to_article.py # [新增] Alembic 迁移
│   │   └── repositories/
│   │       └── mysql_article_repo.py            # [修改] save/_to_entity 处理新字段
│   └── routers/
│       └── analysis.py                          # [修改] 新增记录详情+列表接口
├── tests/
│   └── unit/
│       └── test_analysis_archive.py             # [新增] 存档相关单元测试

# ---- 前端 ----
frontend/src/
├── utils/
│   └── textUtils.tsx                            # [已有] 首句切分+数字高亮
├── store/
│   └── stockAnalysisStore.ts                    # [修改] 添加 viewMode/viewRecordId 状态
├── services/
│   └── stockAnalysisService.ts                  # [修改] 新增 recordDetail/listRecords API
├── components/stock-analysis/
│   ├── SystemStatusBar.tsx                      # [新增] 系统状态栏（在线/市场/同步）
│   ├── AgentTopologyPreview.tsx                 # [新增] Agent 协作拓扑图
│   ├── ModeSelectionCards.tsx                   # [新增] 模式选择卡片（替代 Radio.Group）
│   ├── HistoryQuickEntry.tsx                    # [新增] 历史3条快捷入口（替代原位置）
│   ├── AgentProgressPanel.tsx                   # [修改] 支持快速模式2个Agent+深度模式12个Agent
│   ├── AgentReportCard.tsx                      # [修改] 统一卡片结构（角色标识+摘要+折叠）
│   ├── DebateTimeline.tsx                       # [修改] 分栏对比+置顶总结
│   ├── DecisionCard.tsx                         # [修改] 色阶条+数字并行
│   ├── RiskAssessmentSection.tsx                # [修改] 5角色独立卡片
│   ├── AnalysisHistoryList.tsx                  # [修改] 最近3条+跳转详情
│   └── ...（其余组件微调）
├── pages/
│   ├── StockAnalysisPage.tsx                    # [修改] Idle态双栏+执行态统一+Done态结构化+viewMode
│   └── AnalysisRecordsPage.tsx                  # [新增] 分析记录列表页
├── components/layout/
│   └── AppLayout.tsx                            # [修改] 新增"分析记录"菜单项
└── App.tsx                                      # [修改] 新增路由
```

**Structure Decision**: 不改变项目目录结构，在现有分层内修改和新增文件。

## Complexity Tracking

> 无宪法违规需豁免。
