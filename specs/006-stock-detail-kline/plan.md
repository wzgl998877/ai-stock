# Implementation Plan: 股票详情页与行情数据展示

**Branch**: `006-stock-detail-kline` | **Date**: 2026-04-30 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/006-stock-detail-kline/spec.md`

---

## Summary

为AI Stock产品的模块二（行情数据展示）构建完整的个股详情页，支持K线图（分时/日K/周K/月K）、技术指标（MA/MACD/KDJ）、财务数据、自选股管理、行业对比和模块一联动。基于已有后端数据层（StockDataRepository + MySQL + Redis）和前端架构（React + TypeScript + Ant Design + ECharts + Zustand）进行扩展，新增5个数据库表、3个后端Router、4个前端Page和若干组件。

---

## Technical Context

| 项目 | 值 |
|------|------|
| **Language/Version** | Python 3.11 (后端) / TypeScript 5.x (前端) |
| **Primary Dependencies** | FastAPI + SQLAlchemy (后端) / React 18 + Ant Design 5 + ECharts 5 + Zustand (前端) |
| **Storage** | MySQL 8.0 (主库) + Redis 6.0 (缓存) |
| **Testing** | pytest + pytest-asyncio (后端) / Vitest (前端) |
| **Target Platform** | Web (PC为主) |
| **Project Type** | Web application (frontend + backend) |
| **Performance Goals** | K线渲染 ≤2s / 侧边栏展示 ≤1.5s / 搜索响应 ≤500ms |
| **Constraints** | 数据延迟15-30分钟可接受 / 单用户最多10分组×100股 / 只做A股 / 无登录系统，固定userId="default" |
| **Scale/Scope** | 5000+股票 / 31个一级行业 / 每股票3年日K约750条 |

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Gate 1: 三模块协同
- ✅ 模块一 → 模块二：文章内股票代码点击 → 侧边栏K线（FR-001）
- ✅ 模块二 → 模块一：相关分析标签点击 → 跳转知识库定位文章（FR-008）
- ✅ 模块二 → 模块三：自选股列表显示缠论信号灯（FR-011，用"-"占位）

### Gate 2: 个人投研工具边界
- ✅ 无自动交易功能
- ✅ 数据延迟标注（FR-014）
- ✅ "不构成投资建议"提示（FR-014）

### Gate 3: 架构红线
- ✅ 后端分层：Router → Application → Domain → Infrastructure（新增Router不直连DB）
- ✅ 前端分层：Page → Application → Service（新增Page不直接使用fetch）
- ✅ 密钥管理：AKShare无需API Key，其他密钥走环境变量

### Gate 4: 数据约束
- ✅ 金额使用Decimal（继承现有Domain模型）
- ✅ 数据库操作走Repository（新增Repository遵循已有模式）
- ✅ Prompt模板化管理（本Feature不涉及AI/Prompt）

### Gate 5: UI设计约束
- ✅ 结构化布局（卡片化、分区化）
- ✅ loading/empty/error状态
- ✅ 遵循DESIGN.md设计系统

**Result: ALL GATES PASS** ✅

---

## Project Structure

### Documentation (this feature)

```text
specs/006-stock-detail-kline/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/
│   └── api.md           # API契约文档
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

**Structure Decision**: Web application (frontend + backend) — 与现有项目结构一致

```text
backend/
├── app/
│   ├── routers/
│   │   ├── stock_data.py          # 已有, 扩展: /minute, /indicators, /detail, /search
│   │   ├── watchlist.py           # 新增: 自选股分组CRUD
│   │   ├── industry.py            # 新增: 行业列表与对比
│   │   └── article_relation.py    # 新增: 文章-股票关联查询
│   ├── application/
│   │   ├── use_cases/
│   │   │   ├── stock_detail.py    # 新增: 个股详情聚合
│   │   │   ├── watchlist.py       # 新增: 自选股用例
│   │   │   ├── industry.py        # 新增: 行业对比用例
│   │   │   └── indicator_calc.py  # 新增: 技术指标计算
│   │   └── dtos/
│   │       └── market_data_dto.py # 新增: DTO定义
│   ├── domain/
│   │   ├── entities/
│   │   │   ├── industry_stock.py  # 新增
│   │   │   ├── watchlist.py       # 新增
│   │   │   └── article_stock.py   # 新增
│   │   ├── models/
│   │   │   └── stock_data.py      # 已有, 扩展: StockIndicator, MinuteQuote
│   │   ├── repositories/
│   │   │   ├── watchlist_repo.py  # 新增: Interface
│   │   │   ├── industry_repo.py   # 新增: Interface
│   │   │   └── article_stock_repo.py # 新增: Interface
│   │   └── services/
│   │       └── indicator_service.py  # 新增: MACD/KDJ计算
│   ├── infrastructure/
│   │   ├── repositories/
│   │   │   ├── mysql_watchlist_repo.py   # 新增
│   │   │   ├── mysql_industry_repo.py    # 新增
│   │   │   └── mysql_article_stock_repo.py # 新增
│   │   ├── db/
│   │   │   └── migrations/
│   │   │       └── versions/
│   │   │           └── xxxxxxxx_add_market_data_module2.py  # 新增
│   │   └── cache/
│   │       └── redis_cache.py     # 已有, 扩展: 搜索缓存、分时缓存
│   └── schemas/
│       └── market_data.py         # 新增: Pydantic Schemas
└── tests/
    ├── unit/
    │   ├── domain/
    │   │   └── test_indicator_service.py  # 新增
    │   └── application/
    │       └── test_watchlist.py          # 新增
    └── integration/
        └── test_stock_data_api.py         # 新增

frontend/
├── src/
│   ├── pages/
│   │   ├── StockDetailPage.tsx    # 新增: 个股详情页
│   │   ├── WatchlistPage.tsx      # 新增: 自选股管理页
│   │   └── IndustryPage.tsx       # 新增: 行业对比页
│   ├── components/
│   │   ├── stock/
│   │   │   ├── KLineChart.tsx     # 新增: ECharts K线图
│   │   │   ├── PriceCard.tsx      # 新增: 顶部价格卡
│   │   │   ├── PeriodSelector.tsx # 新增: 周期切换
│   │   │   ├── IndicatorToggle.tsx # 新增: 指标开关
│   │   │   ├── FinancialTab.tsx   # 新增: 财务数据标签
│   │   │   ├── RelatedAnalysisTab.tsx # 新增: 相关分析标签
│   │   │   ├── IndustryComparison.tsx # 新增: 同行对比
│   │   │   ├── StockSearch.tsx    # 新增: 搜索组件
│   │   │   └── StockDetailDrawer.tsx # 新增: 可滑出Drawer(模块一联动，从右侧滑出覆盖内容)
│   │   ├── watchlist/
│   │   │   ├── WatchlistGroup.tsx # 新增: 分组组件
│   │   │   ├── WatchlistItem.tsx  # 新增: 股票行组件
│   │   │   └── GroupManager.tsx   # 新增: 分组管理
│   │   └── industry/
│   │       ├── IndustryNav.tsx    # 新增: 行业导航
│   │       └── ComparisonTable.tsx # 新增: 对比表
│   ├── application/
│   │   ├── useStockDetail.ts      # 新增: 个股详情逻辑
│   │   ├── useWatchlist.ts        # 新增: 自选股逻辑
│   │   ├── useIndustry.ts         # 新增: 行业逻辑
│   │   └── useStockSearch.ts      # 新增: 搜索逻辑
│   ├── services/
│   │   ├── stockDataService.ts    # 已有, 扩展
│   │   ├── watchlistService.ts    # 新增
│   │   ├── industryService.ts     # 新增
│   │   └── articleService.ts      # 已有, 扩展(相关分析)
│   └── store/
│       ├── stockDetailStore.ts    # 新增
│       ├── watchlistStore.ts      # 新增
│       └── industryStore.ts       # 新增
└── tests/
    └── components/
        └── stock/
            └── KLineChart.test.tsx  # 新增
```

---

## Complexity Tracking

> **No violations identified.** 所有设计严格遵循宪法和rules分层要求，未引入额外项目或绕过分层约束。

| Component | Justification |
|-----------|---------------|
| 新增3个后端Router | 按领域拆分（stock/industry/watchlist），每个Router职责单一 |
| 新增5个数据库表 | 对应5个独立领域概念，表结构正交 |
| 前端新增3个Page | 对应3个独立用户场景（详情页/自选股/行业对比） |
| ECharts K线图 | 技术栈已包含ECharts，不引入新依赖 |

---

## Research Summary

见 [research.md](./research.md)

**Key Decisions**:
1. K线图: ECharts 5 Candlestick + 多Grid布局（已在技术栈中）
2. 技术指标: 前端计算MA，后端计算MACD/KDJ（后端统一计算可复用可缓存）
3. 分时数据: Redis缓存15分钟，不持久化到MySQL（数据量大、价值低）
4. 股票搜索: 后端全量列表接口 + 前端本地模糊匹配（响应快、减少请求）

---

## Data Model Summary

见 [data-model.md](./data-model.md)

**新增5个Domain Entity**:
1. `IndustryStock` — 行业-股票映射
2. `WatchlistGroup` — 自选股分组
3. `WatchlistItem` — 自选股条目
4. `ArticleStockRelation` — 文章-股票关联
5. `StockIndicator` — 技术指标缓存

**新增1个缓存Entity**（仅Redis）:
- `MinuteQuote` — 分时数据

**扩展1个已有Entity**:
- `Stock` — 增加 industry_code, industry_name, total_market_cap, float_market_cap

---

## API Contracts Summary

见 [contracts/api.md](./contracts/api.md)

**新增14个接口**:
| 接口 | 说明 |
|------|------|
| `GET /stocks/{code}/minute` | 分时数据 |
| `GET /stocks/{code}/indicators` | 技术指标 |
| `GET /stocks/search` | 模糊搜索 |
| `GET /stocks/all` | 全量股票列表 |
| `GET /stocks/{code}/detail` | 聚合详情 |
| `GET /stocks/{code}/related-articles` | 相关分析 |
| `GET /watchlist/groups` | 分组列表 |
| `POST /watchlist/groups` | 创建分组 |
| `PUT /watchlist/groups/{id}` | 重命名 |
| `DELETE /watchlist/groups/{id}` | 删除分组 |
| `POST /watchlist/groups/{id}/stocks` | 添加股票 |
| `DELETE /watchlist/groups/{id}/stocks/{code}` | 移除股票 |
| `GET /industries` | 行业列表 |
| `GET /industries/{code}/stocks` | 行业股票对比 |

---

## Quick Start

见 [quickstart.md](./quickstart.md)

**开发顺序**: 数据层(2天) → 后端接口(2天) → 前端页面(3天) → 联调集成(1天) = **约8天**
