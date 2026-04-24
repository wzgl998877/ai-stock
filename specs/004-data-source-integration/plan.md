# Implementation Plan: 多数据源股票数据体系引入

**Branch**: `004-data-source-integration` | **Date**: 2026-04-24 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/004-data-source-integration/spec.md`

## Summary

将 Tushare、AKShare、BaoStock 三个数据源引入项目，构建股票数据的采集、清洗、存储体系。后端新增数据源配置管理、同步任务服务、数据清洗服务及相关 API；前端新增同步侧边栏和数据源配置页面。数据持久化使用 MongoDB（已有集合结构），缓存使用 Redis，数据读取优先级为 Tushare > AKShare > BaoStock。

## Technical Context

**Language/Version**: Python 3.11+ (后端), TypeScript 5.x (前端)
**Primary Dependencies**: FastAPI, pymongo/motor, redis, APScheduler, tushare, akshare, baostock; React 18 + Ant Design 5 (前端)
**Storage**: MongoDB (主存储: stock_basic_info, market_quotes, stock_daily_quotes, stock_financial_data, sync_tasks, datasource_configs), Redis (L1 缓存, TTL)
**Testing**: pytest (后端), Vitest/Jest (前端)
**Target Platform**: Linux/Windows 开发环境, Docker Compose 部署
**Project Type**: Web 应用 (前后端分离)
**Performance Goals**: 单股基础信息同步 < 5s; 同步进度每 2s 至少更新一次; 数据读取 < 1s (命中 Redis 缓存)
**Constraints**: Tushare API 限流约束; MongoDB 连接池最大 100; 同一数据源同步任务互斥; 数值类型使用 Decimal
**Scale/Scope**: A 股全市场约 5000+ 股票; 历史K线可达 10 年; 四种数据类型, 三个数据源

## Constitution Check (Post-Design Re-evaluation)

*Re-checked after Phase 1 design — all gates still pass.*

| Gate | Status | Rationale |
|------|--------|-----------|
| 个人投研工具边界 | PASS | 纯数据接入功能，不涉及自动交易 |
| 后端分层 | PASS | 所有新代码严格遵循 Router → Application → Domain → Infrastructure |
| 前端 Service 封装 | PASS | 新增长 `syncService.ts`、`datasourceService.ts` 经 services/ 封装 |
| 数据约束 (Decimal) | PASS | data-model.md 中所有金额/比率字段使用 DECIMAL |
| 三模块协同 | PASS | 数据源服务为模块二核心，同时支撑模块一/三 |
| UI 设计原则 | PASS | 侧边栏采用 Ant Design Drawer，配置页采用 Card 布局 |
| 密钥管理 | PASS | 加密存储 + 环境变量管理 encryption key |

## Post-Design Notes

### Key Corrections from Research

1. **存储方案修正**: 产品规范提及 MongoDB，但项目实际使用 MySQL。Phase 0 研究确认使用 MySQL 作为持久化存储，与宪章保持一致。所有数据表设计均基于 MySQL + JSON 扩展字段。

2. **Redis 实现**: 当前 Redis 已配置但未使用，本功能将首次实现 Redis 缓存层。

3. **数据源现状**: AKShare 已在工作流工具中按需使用，本功能将其升级为持久化同步体系。

4. **无 MongoDB 依赖**: 研究确认无需引入 MongoDB，MySQL 完全满足当前结构化数据存储需求。若未来确实需要 MongoDB，可独立扩展。

## Project Structure

### Documentation (this feature)

```text
specs/004-data-source-integration/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── core/
│   │   ├── config.py              # 环境变量配置 (数据源 API Key)
│   │   └── database.py            # MongoDB/Redis 连接管理
│   ├── domain/
│   │   ├── models/
│   │   │   ├── datasource.py       # 数据源配置实体
│   │   │   ├── sync_task.py        # 同步任务实体
│   │   │   └── stock_data.py       # 股票数据实体 (基础信息/行情/K线/财务)
│   │   ├── services/
│   │   │   ├── data_cleaner.py     # 数据清洗服务 (标准化/单位转换)
│   │   │   └── data_priority.py    # 数据优先级服务
│   │   └── repositories/
│   │       ├── datasource_repo.py   # 数据源配置 CRUD
│   │       ├── sync_task_repo.py    # 同步任务 CRUD
│   │       └── stock_data_repo.py   # 股票数据 CRUD
│   ├── application/
│   │   └── sync/
│   │       ├── tushare_client.py    # Tushare API 封装
│   │       ├── akshare_client.py    # AKShare API 封装
│   │       ├── baostock_client.py   # BaoStock API 封装
│   │       └── sync_executor.py     # 同步任务编排与进度管理
│   ├── infrastructure/
│   │   ├── cache/
│   │   │   └── redis_cache.py       # Redis 缓存封装 (TTL)
│   │   └── mongodb/
│   │       ├── datasource_mongo.py  # MongoDB 数据源操作
│   │       └── stock_data_mongo.py  # MongoDB 股票数据操作
│   └── api/
│       └── v1/
│           ├── datasource.py        # 数据源配置 API
│           ├── sync.py              # 同步任务 API (SSE 进度推送)
│           └── stock_data.py        # 股票数据查询 API
└── tests/
    ├── unit/
    │   ├── test_data_cleaner.py
    │   └── test_data_priority.py
    └── integration/
        ├── test_tushare_sync.py
        ├── test_akshare_sync.py
        └── test_sync_api.py

frontend/
├── src/
│   ├── pages/
│   │   └── SyncPanel.tsx            # 同步侧边栏页面
│   ├── components/
│   │   ├── sync/
│   │   │   ├── DataSourceSelector.tsx  # 数据源选择器
│   │   │   ├── SyncProgress.tsx        # 同步进度展示
│   │   │   └── SyncHistory.tsx         # 同步历史列表
│   │   └── datasource/
│   │       └── DataSourceConfig.tsx    # 数据源配置表单
│   ├── services/
│   │   ├── syncService.ts          # 同步任务 API 调用
│   │   ├── datasourceService.ts    # 数据源配置 API 调用
│   │   └── stockDataService.ts     # 股票数据查询 API 调用
│   └── stores/
│       └── syncStore.ts             # Zustand 同步状态管理
└── tests/
    └── sync/
        └── SyncPanel.test.tsx
```

**Structure Decision**: 采用前后端分离的 Web 应用结构。后端严格遵循 Router (api/) → Application (sync/) → Domain (domain/) → Infrastructure (infrastructure/) 分层。前端采用页面 + 组件 + 服务 + 状态管理的四层结构。

## Complexity Tracking

无宪法违规项，无需复杂度追踪。
