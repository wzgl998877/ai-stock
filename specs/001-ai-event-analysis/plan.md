# Implementation Plan: AI 事件分析 & 行业知识库

**Branch**: `001-ai-event-analysis` | **Date**: 2026-04-16 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-ai-event-analysis/spec.md`

## Summary

实现模块一（AI 事件分析 & 行业知识库）的完整功能，包括：
- **AI 分析引擎**：5种事件类型（地缘政治/政策法规/财报季报/产业链分析/其他），对应独立提示词模板，流式 SSE 输出
- **知识库**：保存/浏览/搜索历史分析，三视图（行业/时间线/股票），MySQL FULLTEXT 中文全文搜索
- **辅助功能**：相似问题检测（关键词匹配）、大事提醒（站内通知）、新用户引导（3个示例）

技术方案：后端 FastAPI + DDD 分层（Router→Application→Domain→Infrastructure），前端 React 18 + Ant Design 5 + Zustand，数据 MySQL + Redis 缓存，AI 经统一抽象层接入。

## Technical Context

**Language/Version**: Python 3.11+（后端）/ TypeScript 5.x（前端）
**Primary Dependencies**: FastAPI, SQLAlchemy/SQLModel, Pydantic, httpx（后端）; React 18, Ant Design 5, Zustand, ECharts 5（前端）
**Storage**: MySQL 8.0（主库，文章/提醒/标签）+ Redis（缓存，分析任务状态/计算结果）
**Testing**: pytest（后端）/ Vitest（前端）
**Target Platform**: Linux 服务器（Docker Compose 部署）+ PC 浏览器（Chrome/Firefox/Edge）
**Project Type**: Web 应用（前后端分离）
**Performance Goals**: SSE 首字延迟 ≤3s; 搜索响应 ≤1s; 列表首屏 ≤2s
**Constraints**: 单用户系统，预留多用户扩展; LLM API Key 仅服务端环境变量
**Scale/Scope**: ~10 篇/月，31 个行业标签，~6 个前端页面

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-Design Gate

| # | Gate | Status | Notes |
|---|------|--------|-------|
| 1 | **三模块协同**：标明模块归属 + 跨模块跳转 | ✅ PASS | 归属模块一；股票代码→模块二个股详情页跳转（FR-010）；自选股数据依赖模块二 |
| 2 | **个人投研工具边界**：无自动交易/投顾能力 | ✅ PASS | 纯分析+知识库，所有推荐附"不构成投资建议"（PRD 模板已含） |
| 3 | **简洁实用**：不过度设计 | ✅ PASS | 相似检测用关键词匹配不用 AI；搜索用 MySQL 内置不用 ES；单用户先行 |
| 4 | **后端分层**：Router→Application→Domain→Infrastructure | ✅ PLANNED | 详见 Project Structure |
| 5 | **前端分层**：Page→Application→Service | ✅ PLANNED | 所有 API 经 services/，页面不直连 fetch |
| 6 | **流式输出成对实现**：后端 SSE + 前端 EventSource | ✅ PLANNED | SSE `data: ...\n\n` 格式，前端实时渲染+停止+loading |
| 7 | **AI 统一抽象层**：业务层不直连 SDK | ✅ PLANNED | Infrastructure 层封装 AIService，Prompt 模板化管理 |
| 8 | **密钥不泄露**：API Key 仅环境变量 | ✅ PASS | `.env` 管理，禁止硬编码 |
| 9 | **数据约束**：Decimal 类型 / Repository 封装 / Prompt 模板化 | ✅ PLANNED | 金额用 Decimal；所有 DB 操作在 Repository 内 |

**Gate Result**: ✅ ALL PASS — 进入 Phase 0

## Project Structure

### Documentation (this feature)

```text
specs/001-ai-event-analysis/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output (by /speckit.tasks)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── main.py                    # FastAPI 应用入口
│   ├── core/
│   │   ├── config.py              # 配置管理（环境变量）
│   │   ├── database.py            # 数据库连接
│   │   └── exceptions.py          # 统一异常
│   ├── routers/
│   │   ├── analysis.py            # AI 分析路由
│   │   ├── knowledge.py           # 知识库路由
│   │   └── reminder.py            # 大事提醒路由
│   ├── application/
│   │   ├── use_cases/
│   │   │   ├── analyze_event.py   # 事件分析用例
│   │   │   ├── manage_article.py  # 文章管理用例
│   │   │   ├── search_articles.py # 搜索用例
│   │   │   ├── detect_similar.py  # 相似检测用例
│   │   │   └── manage_reminder.py # 提醒管理用例
│   │   └── dtos/
│   │       ├── analysis_dto.py    # 分析请求/响应 DTO
│   │       ├── article_dto.py     # 文章 DTO
│   │       └── reminder_dto.py    # 提醒 DTO
│   ├── domain/
│   │   ├── entities/
│   │   │   ├── article.py         # 分析文章实体
│   │   │   └── reminder.py        # 大事提醒实体
│   │   ├── value_objects/
│   │   │   ├── event_type.py      # 事件类型枚举
│   │   │   └── industry_tag.py    # 行业标签值对象
│   │   ├── services/
│   │   │   ├── analysis_parser.py # 分析结果解析（六段/七段结构）
│   │   │   └── similarity.py      # 相似度计算
│   │   └── repositories/
│   │       ├── article_repo.py    # 文章仓储接口
│   │       ├── search_repo.py     # 搜索仓储接口
│   │       └── reminder_repo.py   # 提醒仓储接口
│   ├── infrastructure/
│   │   ├── db/
│   │   │   ├── models.py          # SQLAlchemy ORM 模型
│   │   │   └── migrations/        # Alembic 迁移
│   │   ├── repositories/
│   │   │   ├── mysql_article_repo.py
│   │   │   ├── mysql_search_repo.py
│   │   │   └── mysql_reminder_repo.py
│   │   ├── ai/
│   │   │   ├── ai_service.py      # AI 服务抽象层
│   │   │   └── prompts/
│   │   │       ├── geopolicy.py   # 地缘政治模板
│   │   │       ├── policy.py      # 政策法规模板
│   │   │       ├── earnings.py    # 财报季报模板
│   │   │       ├── chain.py       # 产业链分析模板
│   │   │       └── general.py     # 其他通用模板
│   │   └── search/
│   │       └── fulltext_search.py # MySQL FULLTEXT 搜索实现
│   ├── schemas/
│   │   └── ...                    # Pydantic schemas（如需与 DTO 分离）
│   └── data/
│       └── industries.json        # 申万31个一级行业静态数据
├── tests/
│   ├── unit/
│   ├── integration/
│   └── contract/
├── requirements.txt
├── Dockerfile
└── .env.example

frontend/
├── src/
│   ├── pages/
│   │   ├── AnalysisPage.tsx       # AI 分析页
│   │   ├── KnowledgePage.tsx      # 知识库浏览页
│   │   ├── ArticleDetailPage.tsx  # 文章详情页
│   │   └── ReminderPage.tsx       # 大事提醒管理页
│   ├── components/
│   │   ├── analysis/
│   │   │   ├── EventTypeSelector.tsx  # 事件类型选择器
│   │   │   ├── AnalysisInput.tsx      # 输入框+草稿
│   │   │   ├── AnalysisResult.tsx     # 流式结果渲染
│   │   │   ├── AnalysisStatusBar.tsx  # 全局分析状态条
│   │   │   └── SimilarPrompt.tsx      # 相似问题提示卡
│   │   ├── knowledge/
│   │   │   ├── IndustryView.tsx       # 行业视图
│   │   │   ├── TimelineView.tsx       # 时间线视图
│   │   │   ├── StockView.tsx          # 股票视图
│   │   │   ├── ArticleCard.tsx        # 文章卡片
│   │   │   └── SearchBar.tsx          # 搜索栏
│   │   ├── reminder/
│   │   │   ├── ReminderList.tsx       # 提醒列表
│   │   │   └── ReminderForm.tsx       # 添加提醒表单
│   │   ├── onboarding/
│   │   │   └── ExamplePrompts.tsx     # 新用户示例引导
│   │   └── common/
│   │       ├── StockCodeLink.tsx      # 股票代码可点击组件（→模块二）
│   │       └── IndustryTag.tsx        # 行业标签组件
│   ├── application/
│   │   ├── useAnalysis.ts         # 分析相关业务逻辑
│   │   ├── useKnowledge.ts        # 知识库相关业务逻辑
│   │   └── useReminder.ts         # 提醒相关业务逻辑
│   ├── domain/
│   │   ├── types.ts               # 业务类型定义
│   │   └── constants.ts           # 申万行业列表、事件类型等常量
│   ├── services/
│   │   ├── api.ts                 # axios 实例
│   │   ├── analysisService.ts     # 分析 API
│   │   ├── knowledgeService.ts    # 知识库 API
│   │   └── reminderService.ts     # 提醒 API
│   ├── store/
│   │   ├── analysisStore.ts       # 分析状态（Zustand）
│   │   ├── knowledgeStore.ts      # 知识库状态
│   │   └── reminderStore.ts       # 提醒状态
│   ├── hooks/
│   │   ├── useSSE.ts              # SSE 流式连接 Hook
│   │   └── useDraft.ts            # 草稿自动保存 Hook
│   └── utils/
│       └── markdown.ts            # Markdown 渲染工具
├── tests/
├── package.json
├── Dockerfile
└── .env.example
```

**Structure Decision**: 采用 Web 应用结构（Option 2），前后端分离。后端遵循 DDD 分层（Router→Application→Domain→Infrastructure），前端遵循 Page→Application→Service 分层。模块间联动通过前端路由跳转实现（股票代码→模块二详情页），接口预留。

## Complexity Tracking

> 无违规项需要论证。
