# Implementation Plan: 投资事件影响雷达

**Branch**: `007-event-radar` | **Date**: 2026-05-11 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/007-event-radar/spec.md`

## Summary

构建「投资事件影响雷达」模块（模块四），核心使命是"系统比用户更早发现——哪些事件正在影响他的投资"。系统通过定时采集财经信息（财联社 RSS + 现有搜索引擎），自动提取关联股票/行业，匹配用户自选股，判断影响方向和置信度，以"影响雷达面板"和"预警推送"两种方式主动告知用户，并提供一键联动模块一事件/个股分析的闭环。

技术路径：后端复用 DDD 四层架构（Router → Application → Domain → Infrastructure），新增事件采集管线（APScheduler 定时任务）、影响判断引擎（规则引擎 + LLM 兜底）、晨报工作流（LangGraph）。前端新增事件雷达页面（Ant Design 卡片化布局）+ 铃铛预警组件 + 自选股影响徽标。

## Technical Context

**Language/Version**: Python 3.11 (后端), TypeScript (前端)
**Primary Dependencies**: FastAPI, SQLAlchemy 2.0 (async), LangGraph, APScheduler, React 18, Ant Design 5, Zustand, ECharts
**Storage**: MySQL（6 张新表）+ Redis（缓存）
**Testing**: pytest (后端), Vitest (前端)
**Target Platform**: Web (Linux server + 现代浏览器)
**Project Type**: Web application (前后端分离)
**Performance Goals**: 面板加载 ≤ 2s，事件扫描到可见 ≤ 15min，预警延迟 ≤ 5min
**Constraints**: 版权合规（摘要 ≤ 200 字），每日预警 ≤ 5 条，影响判断规则引擎为主
**Scale/Scope**: ≤ 100 用户，≤ 30 只自选股/用户，每日影响事件 ≤ 10 条/用户

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| 宪章条款 | 状态 | 说明 |
|----------|------|------|
| I. 三模块协同优先 | ✅ PASS | 新增模块四明确标注与模块一（一键分析联动）、模块二（自选股影响徽标、全局股票抽屉）、知识库（历史分析关联）的跳转和数据关联 |
| II. 个人投研工具边界 | ✅ PASS | 页面须展示"不构成投资建议"声明；不涉及自动交易；影响判断为辅助参考 |
| III. 简洁实用 | ✅ PASS | 复用现有 MetadataExtractor、SearchService、AIService、LangGraph；影响判断先用规则引擎后 LLM 兜底；不做过度抽象 |
| 技术栈约束 | ✅ PASS | 使用项目已引入的 FastAPI、SQLAlchemy、LangGraph、APScheduler、React、Ant Design、Zustand |
| 架构红线 - 后端分层 | ✅ PASS | 新增代码遵循 Router → Application → Domain → Infrastructure 四层架构 |
| 架构红线 - 前端 Service 层 | ✅ PASS | 新增 eventRadarService.ts，页面不直连网络 |
| 架构红线 - 密钥不泄露 | ✅ PASS | 无新增密钥，复用现有配置 |
| 流式输出成对实现 | ✅ PASS | 晨报为预生成非流式；AI 解读可复用现有 SSE 模式（Phase 2） |
| 数据约束 - Repository | ✅ PASS | 新增 6 张表的 Repository 层实现 |
| 数据约束 - Prompt 模板化 | ✅ PASS | 影响判断 Prompt 和晨报 Prompt 放入 infrastructure/ai/prompts/ |
| UI 设计原则 | ✅ PASS | 遵循 DESIGN.md，卡片化布局，结构化分区 |

**GATE RESULT: ✅ ALL PASS** — 无违宪项，可进入 Phase 0。

## Project Structure

### Documentation (this feature)

```text
specs/007-event-radar/
├── plan.md              # 本文件
├── research.md          # Phase 0 研究产出
├── data-model.md        # Phase 1 数据模型
├── quickstart.md        # Phase 1 快速启动指南
├── contracts/           # Phase 1 API 契约
│   └── api-contracts.md
└── tasks.md             # Phase 2 任务（/speckit.tasks 生成）
```

### Source Code (repository root)

```text
# 后端新增文件
backend/app/
├── routers/
│   └── event_radar.py                              # API 路由
├── application/
│   ├── dtos/
│   │   └── event_radar_dto.py                      # DTO
│   └── use_cases/
│       ├── event_radar.py                           # 面板查询用例
│       ├── event_alert.py                           # 预警管理用例
│       └── morning_briefing.py                      # 晨报用例
├── domain/
│   ├── entities/
│   │   ├── impact_event.py                          # 影响事件实体
│   │   ├── impact_article.py                        # 事件原始报道实体
│   │   ├── user_impact.py                           # 用户影响关联实体
│   │   ├── user_alert.py                            # 预警记录实体
│   │   ├── morning_briefing.py                      # 晨报实体
│   │   └── radar_config.py                          # 雷达配置实体
│   ├── repositories/
│   │   ├── impact_event_repo.py                     # 影响事件仓储接口
│   │   ├── impact_article_repo.py                   # 报道仓储接口
│   │   ├── user_impact_repo.py                      # 用户影响仓储接口
│   │   ├── user_alert_repo.py                       # 预警仓储接口
│   │   ├── morning_briefing_repo.py                 # 晨报仓储接口
│   │   └── radar_config_repo.py                     # 配置仓储接口
│   └── services/
│       ├── impact_assessment.py                     # 影响判断引擎（核心领域服务）
│       ├── sentiment_rule_engine.py                 # 情感规则引擎
│       ├── event_dedup.py                           # 事件去重服务
│       └── event_stock_matcher.py                   # 事件-股票匹配服务
├── infrastructure/
│   ├── db/
│   │   └── migrations/versions/                    # Alembic 迁移文件
│   │       └── xxxx_add_event_radar_tables.py
│   ├── repositories/
│   │   ├── mysql_impact_event_repo.py               # 影响事件仓储实现
│   │   ├── mysql_impact_article_repo.py             # 报道仓储实现
│   │   ├── mysql_user_impact_repo.py                # 用户影响仓储实现
│   │   ├── mysql_user_alert_repo.py                 # 预警仓储实现
│   │   ├── mysql_morning_briefing_repo.py           # 晨报仓储实现
│   │   └── mysql_radar_config_repo.py               # 配置仓储实现
│   ├── crawler/
│   │   ├── base_provider.py                         # 信息源抽象基类
│   │   └── cls_provider.py                          # 财联社信息源
│   ├── workflow/
│   │   └── graph/
│   │       └── morning_briefing_graph.py            # 晨报 LangGraph 工作流
│   ├── ai/
│   │   └── prompts/
│   │       ├── impact_assessment.py                 # 影响判断 Prompt
│   │       └── morning_briefing.py                  # 晨报生成 Prompt
│   └── scheduler/
│       └── event_crawler_scheduler.py               # APScheduler 采集调度
├── tests/
│   ├── unit/
│   │   ├── domain/
│   │   │   ├── test_impact_assessment.py
│   │   │   ├── test_sentiment_rule_engine.py
│   │   │   ├── test_event_dedup.py
│   │   │   └── test_event_stock_matcher.py
│   │   └── infrastructure/
│   │       ├── test_cls_provider.py
│   │       └── test_morning_briefing_graph.py
│   └── integration/
│       └── test_event_radar_api.py

# 前端新增文件
frontend/src/
├── pages/
│   ├── EventRadarPage.tsx                           # 影响雷达面板页面
│   └── MorningBriefingPage.tsx                      # 晨报页面
├── components/
│   ├── event-radar/
│   │   ├── ImpactEventCard.tsx                      # 影响事件卡片
│   │   ├── ImpactStatsCard.tsx                      # 影响概览统计
│   │   ├── EventDetailDrawer.tsx                    # 事件详情 Drawer
│   │   ├── AlertDrawer.tsx                          # 预警 Drawer
│   │   ├── MorningBriefingModal.tsx                 # 晨报弹窗
│   │   ├── RadarConfigModal.tsx                     # 雷达配置弹窗
│   │   └── WatchlistImpactColumn.tsx                # 自选股影响列组件
│   └── layout/
│       └── AlertBell.tsx                            # 铃铛预警图标（增强）
├── services/
│   └── eventRadarService.ts                         # 事件雷达 API 服务
├── store/
│   └── eventRadarStore.ts                           # 事件雷达状态管理
└── domain/
    └── types.ts                                     # 新增类型（追加）
```

**Structure Decision**: Web application（前后端分离）。后端新增文件严格遵循 DDD 四层架构，在现有 `backend/app/` 对应层中扩展。前端新增页面和组件在现有 `frontend/src/` 结构中扩展。新增 `infrastructure/crawler/` 目录存放信息源实现，新增 `infrastructure/scheduler/` 目录存放 APScheduler 调度。

## Complexity Tracking

> 无宪章违规，无需填写。
