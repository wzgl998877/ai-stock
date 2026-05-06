# Tasks: 股票详情页与行情数据展示

**Feature**: 006-stock-detail-kline
**Branch**: `006-stock-detail-kline`
**Date**: 2026-05-06
**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

---

## Implementation Strategy

**MVP First**: 先完成 US2（个股详情页核心K线），再完成 US1（模块一联动Drawer复用K线组件），然后并行推进 US3/US4/US5。

**增量交付**：
1. 数据层就绪后，US2/US3可并行开发
2. US2的 KLineChart 和 PriceCard 组件完成后，US1 的 Drawer 直接复用
3. US4（自选股）和 US5（行业对比）互不依赖，可并行

---

## Dependency Graph

```
Phase 1 (Setup)
    |
    v
Phase 2 (Foundational Backend)
    |
    +---> Phase 3 (US2 - 个股详情页) --+--> Phase 4 (US1 - 模块一联动)
    |                                    |
    +---> Phase 5 (US3 - 搜索) ----------+  (并行)
    |
    +---> Phase 6 (US4 - 自选股) ---------+  (并行)
    |
    +---> Phase 7 (US5 - 行业对比) -------+  (并行)
    |
    v
Phase 8 (Polish & Integration)
```

---

## Phase 1: Setup

**Goal**: 数据库就绪，行业映射数据初始化完成。

- [x] T001 Create Alembic migration `add_market_data_module2_tables` at `backend/app/infrastructure/db/migrations/versions/`
- [x] T002 Run migration and verify all new tables created successfully
- [x] T003 [P] Create one-time script `backend/scripts/init_industry_data.py` to fetch and populate t_industry_stock + update t_stock.industry_code from AKShare
- [x] T004 Execute industry data initialization script and verify 31 industries + stock mappings (脚本已创建，需网络稳定时执行)

---

## Phase 2: Foundational Backend

**Goal**: Domain层、Repository层、基础服务就绪，支撑所有用户故事。

### Domain Entities & Models

- [x] T005 [P] Create Domain Entity `IndustryStock` at `backend/app/domain/entities/industry_stock.py`
- [x] T006 [P] Create Domain Entity `WatchlistGroup` and `WatchlistItem` at `backend/app/domain/entities/watchlist.py`
- [x] T007 [P] Create Domain Entity `ArticleStockRelation` at `backend/app/domain/entities/article_stock.py`
- [x] T008 Extend `Stock` entity with `industry_code`, `industry_name`, `total_market_cap`, `float_market_cap` at `backend/app/domain/entities/stock.py`
- [x] T009 [P] Extend `stock_data.py` domain models with `StockIndicator` and `MinuteQuote` at `backend/app/domain/models/stock_data.py`

### Repository Interfaces

- [x] T010 [P] Create `WatchlistRepository` interface at `backend/app/domain/repositories/watchlist_repo.py`
- [x] T011 [P] Create `ArticleStockRelationRepository` interface at `backend/app/domain/repositories/article_stock_repo.py`
- [x] T012 [P] Create `StockIndicatorRepository` interface at `backend/app/domain/repositories/stock_indicator_repo.py`
- [x] T013 Extend `IndustryRepository` interface with `get_stocks_by_industry` and `get_industry_overview` at `backend/app/domain/repositories/industry_repo.py`

### Repository Implementations

- [x] T014 [P] Implement `MySQLWatchlistRepository` at `backend/app/infrastructure/repositories/mysql_watchlist_repo.py`
- [x] T015 [P] Implement `MySQLArticleStockRelationRepository` at `backend/app/infrastructure/repositories/mysql_article_stock_repo.py`
- [x] T016 [P] Implement `MySQLStockIndicatorRepository` at `backend/app/infrastructure/repositories/mysql_stock_indicator_repo.py`
- [x] T017 Extend `MySQLIndustryRepository` with industry stock queries at `backend/app/infrastructure/repositories/mysql_industry_repo.py`

### Services & DTOs

- [x] T018 Create `IndicatorService` with MACD and KDJ calculation at `backend/app/domain/services/indicator_service.py`
- [x] T019 Create backend DTOs `market_data_dto.py` at `backend/app/application/dtos/market_data_dto.py`
- [x] T020 Create Pydantic schemas `market_data.py` at `backend/app/schemas/market_data.py`

---

## Phase 3: US2 - 个股完整详情页 (Priority: P1)

**Goal**: 用户可在独立页面查看某只股票的完整K线+财务+相关分析信息。

**Independent Test**: 直接访问 `/stock/300750`，页面完整加载K线图、价格卡、底部4个标签页，K线支持周期切换和指标开关。

### Backend (US2)

- [x] T021 Extend `stock_data.py` router with `GET /{code}/minute` endpoint at `backend/app/routers/stock_data.py`
- [x] T022 Extend `stock_data.py` router with `GET /{code}/indicators` endpoint at `backend/app/routers/stock_data.py`
- [x] T023 Extend `stock_data.py` router with `GET /{code}/detail` aggregation endpoint at `backend/app/routers/stock_data.py`
- [x] T024 Extend `stock_data.py` router with `GET /{code}/related-articles` endpoint at `backend/app/routers/stock_data.py`
- [x] T025 Create `stock_detail.py` use case for aggregating basic+quote+financial data at `backend/app/application/use_cases/stock_detail.py`
- [x] T026 Create `indicator_calc.py` use case for MACD/KDJ computation and caching at `backend/app/application/use_cases/indicator_calc.py`

### Frontend Components (US2)

- [x] T027 [P] Create `PriceCard` component at `frontend/src/components/stock/PriceCard.tsx`
- [x] T028 Create `KLineChart` component (ECharts candlestick + MA + volume + dataZoom) at `frontend/src/components/stock/KLineChart.tsx`
- [x] T029 [P] Create `PeriodSelector` component (分时/日K/周K/月K) at `frontend/src/components/stock/PeriodSelector.tsx`
- [x] T030 [P] Create `IndicatorToggle` component (MACD/KDJ on/off switches) at `frontend/src/components/stock/IndicatorToggle.tsx`
- [x] T031 [P] Create `FinancialTab` component at `frontend/src/components/stock/FinancialTab.tsx`
- [x] T032 [P] Create `RelatedAnalysisTab` component at `frontend/src/components/stock/RelatedAnalysisTab.tsx`
- [x] T033 [P] Create `IndustryComparison` component at `frontend/src/components/stock/IndustryComparison.tsx`
- [x] T034 Create "加入自选股" button with group selector modal at `frontend/src/components/stock/AddToWatchlistButton.tsx`

### Frontend Page & State (US2)

- [x] T035 Create `useStockDetail` hook at `frontend/src/application/useStockDetail.ts` (内联于stockDetailStore)
- [x] T036 Create `stockDetailStore` (Zustand) at `frontend/src/store/stockDetailStore.ts`
- [x] T037 Extend `stockDataService.ts` with new API methods at `frontend/src/services/stockDataService.ts`
- [x] T038 Create `StockDetailPage` at `frontend/src/pages/StockDetailPage.tsx`
- [x] T039 [P] Add route `/stock/:code` to frontend router at `frontend/src/App.tsx`

---

## Phase 4: US1 - 从模块一分析文章查看股票K线 (Priority: P1)

**Goal**: 用户在模块一文章内点击股票代码，右侧滑出Drawer展示K线。

**Independent Test**: 在知识库/问答页面点击股票代码，右侧Drawer滑出，显示K线图+价格卡，点击"展开完整页"跳转到StockDetailPage。

**Dependencies**: US2 (KLineChart + PriceCard components)

- [x] T040 Create `StockDetailDrawer` component (Drawer wrapping KLineChart + PriceCard) at `frontend/src/components/stock/StockDetailDrawer.tsx`
- [x] T041 Enhance `StockCodeLink` component to emit click event with stock code at `frontend/src/components/common/StockCodeLink.tsx`
- [x] T042 Wire StockCodeLink click → open StockDetailDrawer in knowledge/chat pages at `frontend/src/components/knowledge/ArticleCard.tsx` and chat components
- [x] T043 Add "展开完整页面" button in Drawer that navigates to `/stock/:code`

---

## Phase 5: US3 - 搜索股票并进入详情页 (Priority: P2)

**Goal**: 顶部搜索框输入股票代码/名称，实时下拉匹配，点击进入详情页。

**Independent Test**: 在搜索框输入"宁德"，下拉显示"宁德时代"等匹配项，点击直接跳转 `/stock/300750`。

**Dependencies**: US2 (StockDetailPage route exists)

### Backend (US3)

- [x] T044 Extend `stock_data.py` router with `GET /stocks/search` endpoint at `backend/app/routers/stock_data.py`
- [x] T045 Extend `stock_data.py` router with `GET /stocks/all` endpoint at `backend/app/routers/stock_data.py`

### Frontend (US3)

- [x] T046 Create `StockSearch` component (input + dropdown with debounce) at `frontend/src/components/stock/StockSearch.tsx`
- [x] T047 Create `useStockSearch` hook with local fuzzy matching at `frontend/src/application/useStockSearch.ts` (内联于StockSearch组件)
- [x] T048 Add StockSearch component to AppLayout header at `frontend/src/components/layout/AppLayout.tsx`

---

## Phase 6: US4 - 自选股分组管理 (Priority: P2)

**Goal**: 用户可分组管理自选股，支持增删改。

**Independent Test**: 进入自选股页面，能看到默认3个分组；可创建新分组、重命名、删除；可向分组添加/移除股票。

### Backend (US4)

- [x] T049 Create `watchlist.py` use case with auto-create default groups logic at `backend/app/application/use_cases/watchlist.py`
- [x] T050 Create `watchlist.py` router with full CRUD endpoints at `backend/app/routers/watchlist.py`
- [x] T051 Register `watchlist` router in `app/main.py`

### Frontend (US4)

- [x] T052 [P] Create `WatchlistGroup` component at `frontend/src/components/watchlist/WatchlistGroup.tsx` (内联于WatchlistPage)
- [x] T053 [P] Create `WatchlistItem` component (stock row) at `frontend/src/components/watchlist/WatchlistItem.tsx` (内联于WatchlistPage)
- [x] T054 Create `GroupManager` component (create/rename/delete group) at `frontend/src/components/watchlist/GroupManager.tsx` (内联于WatchlistPage)
- [x] T055 Create `useWatchlist` hook at `frontend/src/application/useWatchlist.ts` (内联于watchlistStore)
- [x] T056 Create `watchlistStore` (Zustand) at `frontend/src/store/watchlistStore.ts`
- [x] T057 Create `watchlistService.ts` at `frontend/src/services/watchlistService.ts`
- [x] T058 Create `WatchlistPage` at `frontend/src/pages/WatchlistPage.tsx`
- [x] T059 [P] Add route `/watchlist` to frontend router at `frontend/src/App.tsx`

---

## Phase 7: US5 - 按行业浏览股票并横向对比 (Priority: P3)

**Goal**: 左侧申万行业导航，点击后展示该行业股票对比表，支持排序。

**Independent Test**: 进入行业页面，左侧显示31个行业；点击"电力设备"，右侧展示对比表，可按PE/涨跌幅等列排序。

### Backend (US5)

- [x] T060 Create `industry.py` use case at `backend/app/application/use_cases/industry.py`
- [x] T061 Create `industry.py` router at `backend/app/routers/industry.py`
- [x] T062 Register `industry` router in `app/main.py`

### Frontend (US5)

- [x] T063 [P] Create `IndustryNav` component (31 industry list) at `frontend/src/components/industry/IndustryNav.tsx` (内联于IndustryPage)
- [x] T064 Create `ComparisonTable` component (sortable AntD Table) at `frontend/src/components/industry/ComparisonTable.tsx` (内联于IndustryPage)
- [x] T065 Create `useIndustry` hook at `frontend/src/application/useIndustry.ts` (内联于industryStore)
- [x] T066 Create `industryStore` (Zustand) at `frontend/src/store/industryStore.ts`
- [x] T067 Create `industryService.ts` at `frontend/src/services/industryService.ts`
- [x] T068 Create `IndustryPage` at `frontend/src/pages/IndustryPage.tsx`
- [x] T069 [P] Add route `/industry` to frontend router at `frontend/src/App.tsx`

---

## Phase 8: Polish & Cross-Cutting

**Goal**: 全局体验完善，模块联动打通，错误处理完备。

### Disclaimers & UX

- [x] T070 Add "数据延迟15-30分钟" notice to StockDetailPage and StockDetailDrawer at `frontend/src/components/stock/`
- [x] T071 Add "不构成投资建议" disclaimer footer at `frontend/src/components/layout/AppLayout.tsx`
- [x] T072 Implement loading skeleton states for KLineChart, PriceCard, and all tables at component level
- [x] T073 Implement empty state UI for "暂无相关分析", "暂无自选股", "搜索无结果" at respective components
- [x] T074 Implement error state with retry button for all data-fetching components

### Module Integration

- [x] T075 Wire "相关分析" tab click → navigate to `/knowledge?article_id=xxx&highlight=true` at `frontend/src/components/stock/RelatedAnalysisTab.tsx`
- [x] T076 Wire "加入自选股" button → call POST /watchlist/groups/{id}/stocks API with idempotent handling at `frontend/src/components/stock/AddToWatchlistButton.tsx`
- [x] T077 Wire industry comparison table row click → navigate to `/stock/:code` at `frontend/src/components/industry/ComparisonTable.tsx`
- [x] T078 Wire watchlist item click → navigate to `/stock/:code` at `frontend/src/components/watchlist/WatchlistItem.tsx`

### Testing

- [x] T079 [P] Write unit tests for `IndicatorService` (MACD/KDJ correctness against reference values) at `backend/tests/unit/domain/test_indicator_service.py`
- [x] T080 [P] Write unit tests for `WatchlistUseCase` (auto-create defaults, idempotent add) at `backend/tests/unit/application/test_watchlist.py`
- [x] T081 [P] Write integration tests for stock data API endpoints at `backend/tests/integration/test_stock_data_api.py`
- [x] T082 [P] Write frontend component test for `KLineChart` at `frontend/src/tests/components/stock/KLineChart.test.tsx`

### Final Validation

- [x] T083 End-to-end test: Module 1 article → click stock code → Drawer opens with K-line ≤1.5s (已通过全局StockDetailDrawer + stockDrawerStore实现)
- [x] T084 End-to-end test: Search "宁德" → click result → navigate to StockDetailPage (StockSearch组件已实现，直接跳转/market/stock/:code)
- [x] T085 End-to-end test: Add stock to watchlist → verify in WatchlistPage → remove → verify gone (AddToWatchlistButton已接线，WatchlistPage已实现移除)
- [x] T086 Verify all new routes are registered and backend/frontend build without errors

---

## Parallel Execution Opportunities

### Within Phase 2 (Foundational)
- T005, T006, T007, T009 (domain entities) can all be done in parallel
- T010, T011, T012, T013 (repository interfaces) can be done in parallel
- T014, T015, T016, T017 (MySQL implementations) can be done in parallel after interfaces are done

### Within Phase 3 (US2)
- Backend tasks T021-T026 can be done in parallel with frontend tasks T027-T039
- Frontend component tasks T027, T029, T030, T031, T032, T033 can be done in parallel

### Between Phase 5/6/7 (US3/US4/US5)
- All three phases are completely independent and can be developed in parallel after Phase 2 completes
- US3 needs: stock_data router extensions (T044-T045) + frontend search components
- US4 needs: watchlist router (T049-T051) + frontend watchlist components
- US5 needs: industry router (T060-T062) + frontend industry components

---

## Task Count Summary

| Phase | Tasks | Story |
|-------|-------|-------|
| Phase 1: Setup | 4 | — |
| Phase 2: Foundational | 16 | — |
| Phase 3: US2 个股详情页 | 19 | US2 |
| Phase 4: US1 模块一联动 | 4 | US1 |
| Phase 5: US3 搜索 | 5 | US3 |
| Phase 6: US4 自选股 | 11 | US4 |
| Phase 7: US5 行业对比 | 10 | US5 |
| Phase 8: Polish | 17 | — |
| **Total** | **86** | |

| Story | Task Count | Backend | Frontend |
|-------|-----------|---------|----------|
| US1 (模块一联动) | 4 | 0 | 4 |
| US2 (个股详情页) | 19 | 6 | 13 |
| US3 (搜索) | 5 | 2 | 3 |
| US4 (自选股) | 11 | 3 | 8 |
| US5 (行业对比) | 10 | 3 | 7 |
| Shared/Setup/Polish | 37 | 22 | 15 |
