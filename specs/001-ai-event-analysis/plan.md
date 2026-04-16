# Implementation Plan: AI 事件分析 & 行业知识库

**Branch**: `001-ai-event-analysis` | **Date**: 2026-04-16 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-ai-event-analysis/spec.md`

## Summary

实现 AI 事件分析 & 行业知识库模块（模块一 MVP），核心能力包括：5种事件类型的结构化 AI 分析（流式输出）、行业标签自动提取与确认、知识库三视图浏览与全文搜索、相似问题检测、大事提醒、新用户引导。技术方案采用 FastAPI 后端（DDD 分层）+ React 前端，通过 SSE 实现流式输出，MySQL 存储知识库，Redis 缓存热数据。

## Technical Context

**Language/Version**: Python 3.11+ (后端) / TypeScript (前端)
**Primary Dependencies**: FastAPI, SQLAlchemy/SQLModel, React 18, Ant Design 5, Zustand, ECharts 5
**Storage**: MySQL (主库) + Redis (缓存)
**Testing**: pytest (后端) / Vitest (前端)
**Target Platform**: Linux server (Docker Compose 部署), PC 浏览器
**Project Type**: Web application (前后端分离)
**Performance Goals**: 流式首字 ≤3s, 知识库搜索 ≤1s, 页面首屏 ≤2s
**Constraints**: AKShare 免费接口有频率限制; AI 调用目标 60s 内完成
**Scale/Scope**: 单用户（预留多用户扩展），PC 端为主

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| 宪章规则 | 状态 | 说明 |
|----------|------|------|
| I. 三模块协同优先 | ✅ 通过 | 模块一独立实现，预留模块二/三跳转接口（股票代码点击跳转、自选股数据读取） |
| II. 个人投研工具边界 | ✅ 通过 | 无自动交易功能，分析结果标注"不构成投资建议" |
| III. 简洁实用 | ✅ 通过 | MVP 聚焦核心闭环，不过度设计 |
| 后端分层 Router→App→Domain→Infra | ✅ 通过 | 严格遵循，详见 data-model.md 和 contracts/ |
| 前端分层 Page→App→Service | ✅ 通过 | 严格遵循，页面不直连 API |
| 禁止密钥泄露 | ✅ 通过 | API Key 仅环境变量 |
| 流式输出须成对实现 | ✅ 通过 | 后端 SSE + 前端 EventSource |
| 大模型统一抽象层 | ✅ 通过 | Infrastructure 层封装，业务层不直连 |
| Prompt 模板化管理 | ✅ 通过 | 五类模板独立文件管理 |
| 数据库 Repository 模式 | ✅ 通过 | Domain 定义接口，Infrastructure 实现 |

## Project Structure

### Documentation (this feature)

```text
specs/001-ai-event-analysis/
├── plan.md              # 本文件
├── research.md          # Phase 0 输出
├── data-model.md        # Phase 1 输出
├── quickstart.md        # Phase 1 输出
├── contracts/           # Phase 1 输出
│   ├── analysis.md      # AI 分析接口
│   ├── knowledge.md     # 知识库接口
│   └── reminder.md      # 大事提醒接口
└── tasks.md             # Phase 2 输出 (/speckit.tasks 命令生成)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── routers/
│   │   ├── analysis.py          # AI 分析路由
│   │   ├── knowledge.py         # 知识库路由
│   │   └── reminder.py          # 大事提醒路由
│   ├── application/
│   │   ├── analysis_app.py      # 分析用例
│   │   ├── knowledge_app.py     # 知识库用例
│   │   └── reminder_app.py      # 提醒用例
│   ├── domain/
│   │   ├── entities/
│   │   │   ├── article.py       # 分析文章实体
│   │   │   └── reminder.py      # 大事提醒实体
│   │   ├── value_objects/
│   │   │   ├── event_type.py    # 事件类型枚举
│   │   │   └── industry_tag.py  # 行业标签值对象
│   │   ├── services/
│   │   │   └── similarity.py    # 相似度检测领域服务
│   │   └── repositories/
│   │       ├── article_repo.py  # 文章仓库接口
│   │       ├── reminder_repo.py # 提醒仓库接口
│   │       └── search_repo.py   # 搜索仓库接口
│   ├── infrastructure/
│   │   ├── db/
│   │   │   └── models.py        # ORM 模型
│   │   ├── repositories/
│   │   │   ├── article_repo_impl.py
│   │   │   ├── reminder_repo_impl.py
│   │   │   └── search_repo_impl.py
│   │   ├── ai/
│   │   │   ├── llm_service.py   # 大模型统一封装
│   │   │   └── prompts/         # Prompt 模板目录
│   │   │       ├── geopolitical.py
│   │   │       ├── policy.py
│   │   │       ├── earnings.py
│   │   │       ├── supply_chain.py
│   │   │       └── general.py
│   │   └── search/
│   │       └── fulltext_search.py     # MySQL 全文搜索实现
│   ├── schemas/
│   │   ├── analysis.py          # 分析请求/响应 DTO
│   │   ├── knowledge.py         # 知识库 DTO
│   │   └── reminder.py          # 提醒 DTO
│   ├── core/
│   │   ├── config.py            # 配置
│   │   └── deps.py              # 依赖注入
│   └── main.py
└── tests/

frontend/
├── src/
│   ├── pages/
│   │   ├── Analysis/            # AI 分析页
│   │   │   ├── index.tsx
│   │   │   └── components/
│   │   ├── Knowledge/           # 知识库页
│   │   │   ├── index.tsx
│   │   │   └── components/
│   │   └── Reminder/            # 大事提醒页
│   │       ├── index.tsx
│   │       └── components/
│   ├── application/
│   │   ├── analysisApp.ts       # 分析用例
│   │   ├── knowledgeApp.ts      # 知识库用例
│   │   └── reminderApp.ts       # 提醒用例
│   ├── domain/
│   │   ├── types.ts             # 类型定义
│   │   └── constants.ts         # 常量（事件类型、行业列表）
│   ├── services/
│   │   ├── analysisService.ts   # 分析 API
│   │   ├── knowledgeService.ts  # 知识库 API
│   │   ├── reminderService.ts   # 提醒 API
│   │   └── request.ts           # HTTP 封装
│   ├── store/
│   │   ├── analysisStore.ts     # 分析状态
│   │   └── knowledgeStore.ts    # 知识库状态
│   ├── components/              # 公共组件
│   └── utils/
└── tests/
```

**Structure Decision**: 采用 Web application 结构（前后端分离），后端遵循 DDD 分层，前端遵循 Page→Application→Service 分层。目录按模块一的功能域组织，便于后续模块二/三扩展。

## Complexity Tracking

无宪法违规，无需记录。
