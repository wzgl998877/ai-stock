# Tasks: 多数据源股票数据体系引入

**Input**: Design documents from `/specs/004-data-source-integration/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Organization**: Tasks organized by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and dependency management

- [x] T001 Add Python dependencies to `backend/requirements.txt`: `cryptography` (for Fernet encryption)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T002 [P] Add `DATASOURCE_ENCRYPTION_KEY` to `backend/app/core/config.py` and `backend/.env.example`
- [x] T003 [P] Implement Redis cache wrapper in `backend/app/infrastructure/cache/redis_cache.py` (connect via existing `settings.redis_url`, support `get`/`set`/`delete` with TTL, auto-degrade on connection failure)
- [x] T004 [P] Create Domain entities in `backend/app/domain/models/`:
  - `datasource.py` — DataSourceConfig entity (source_type, api_key encrypted, is_enabled, priority, config_json)
  - `sync_task.py` — SyncTask entity (task_id, source_type, data_type, status, counts, timestamps)
  - `stock_data.py` — StockBasicInfo, MarketQuote, StockDailyQuote, StockFinancial entities with Decimal price fields
- [x] T005 [P] Create Domain repository interfaces in `backend/app/domain/repositories/`:
  - `datasource_repo.py` — DataSourceRepository interface (get_all, get_by_type, save, update, delete, check_configured)
  - `sync_task_repo.py` — SyncTaskRepository interface (create, update_status, get_by_id, get_by_source_running, list_tasks, count_running_by_source)
  - `stock_data_repo.py` — StockDataRepository interface (upsert_basic, upsert_quote, upsert_daily, upsert_financial, get_basic, get_quote, get_daily, get_financial, get_by_priority)
- [x] T006 Create Alembic migration for 5 new tables in `backend/app/infrastructure/db/migrations/versions/`:
  - `t_datasource_config` (data source config)
  - `t_sync_task` (sync task tracking)
  - `t_market_quote` (real-time quotes)
  - `t_stock_daily_quote` (historical K-line)
  - `t_stock_financial` (financial data)
  - Extend existing `t_stock` with `data_source` and `market_type` columns, update unique constraint to `(stock_code, data_source)`
  - Also register all 5 new models in `backend/app/infrastructure/db/models.py`
- [x] T007 Implement MySQL Repository — DataSourceConfig in `backend/app/infrastructure/repositories/mysql_datasource_repo.py`
- [x] T008 Implement MySQL Repository — SyncTask in `backend/app/infrastructure/repositories/mysql_sync_task_repo.py`
- [x] T009 Implement MySQL Repository — Stock Data in `backend/app/infrastructure/repositories/mysql_stock_data_repo.py`
- [x] T010 Implement Data Cleaner service in `backend/app/domain/services/data_cleaner.py`:
  - `clean_basic_info(raw_dict, source)`: code `.zfill(6)`, date formatting, source tagging
  - `clean_quote(raw_dict, source)`: price validation, unit conversion (Tushare amount: 千元→元, volume: 手→股)
  - `clean_daily_quote(raw_dict, source)`: OHLC validation, date formatting, source tagging
  - `clean_financial(raw_dict, source)`: Decimal conversion, date formatting, report_date validation
- [x] T011 Implement Data Priority service in `backend/app/domain/services/data_priority.py`:
  - `get_highest_priority_source(available_sources)`: returns source with lowest priority number
  - `merge_by_priority(results_by_source)`: merges results ordered by source priority
- [x] T012 Implement Sync Task Executor in `backend/app/application/sync/sync_executor.py`:
  - `execute_sync(source_type, data_type, **params)`: main entry point, creates SyncTask, returns SSE event generator
  - Memory lock mechanism per source_type (asyncio.Lock)
  - Progress tracking and SSE event emission (`sync_started`, `sync_progress`, `sync_completed`, `sync_failed`)
  - Error handling and task status update on failure
- [x] T013 [P] Implement Tushare API Client in `backend/app/application/sync/tushare_client.py`:
  - `fetch_basic_info()`: `stock_basic` API → list of dicts
  - `fetch_quote(codes)`: `rt_k` API → list of dicts
  - `fetch_daily_quote(code, start_date, end_date, period)`: `daily` API → list of dicts
  - `fetch_financial(code)`: `fina_indicator` API → list of dicts
  - Rate limit handling (catch API errors, retry with backoff)
  - Requires Tushare token from DataSourceConfig
- [x] T014 [P] Implement AKShare API Client in `backend/app/application/sync/akshare_client.py`:
  - `fetch_basic_info()`: `stock_info_a_code_name` → list of dicts
  - `fetch_quote(codes)`: `stock_zh_a_spot_em` → list of dicts
  - `fetch_daily_quote(code, start_date, end_date, period)`: `stock_zh_a_hist` → list of dicts
  - `fetch_financial(code)`: `stock_financial_abstract_ths` → list of dicts
  - No API key required
- [x] T015 [P] Implement BaoStock API Client in `backend/app/application/sync/baostock_client.py`:
  - `fetch_basic_info()`: `query_stock_basic` → list of dicts
  - `fetch_daily_quote(code, start_date, end_date, period)`: `query_history_k_data` → list of dicts
  - `fetch_financial(code)`: `query_profit` → list of dicts
  - Login/logout session management

**Checkpoint**: Foundation ready — user story implementation can now begin in parallel

---

## Phase 3: User Story 1 — 手动触发数据同步 (Priority: P1) 🎯 MVP

**Goal**: 用户在前端同步侧边栏选择数据源+数据类型，触发同步并实时查看进度

**Independent Test**: 选择任意数据源+数据类型组合触发同步，验证数据成功存入数据库，SSE 进度实时推送

### Implementation for User Story 1

- [x] T016 [US1] Implement Sync API router in `backend/app/routers/sync.py`:
  - `GET /api/v1/sync/execute` — SSE endpoint, validates source_type + data_type, checks datasource configured, calls SyncExecutor, yields SSE events
  - `POST /api/v1/sync/tasks/{task_id}/retry` — retries a failed task
  - Error responses: 400 (not configured), 409 (in progress), 422 (invalid params)
- [x] T017 [US1] Register sync router in `backend/app/main.py` (include router with prefix `/api/v1`)
- [x] T018 [P] [US1] Create `syncService.ts` in `frontend/src/services/syncService.ts`:
  - `executeSync(sourceType, dataType, params?)` — returns EventSource for SSE stream
  - `retryTask(taskId)` — POST retry endpoint
  - Use fetch + ReadableStream for SSE (not EventSource, to support custom headers if needed)
- [x] T019 [P] [US1] Create `syncStore.ts` in `frontend/src/store/syncStore.ts` (Zustand):
  - State: `syncTasks` (Map<task_id, SyncTask>), `currentSync`, `syncHistory`, `syncStatus`
  - Actions: `startSync`, `updateProgress`, `completeSync`, `loadHistory`, `retryTask`
- [x] T020 [P] [US1] Create `DataSourceSelector.tsx` in `frontend/src/components/sync/DataSourceSelector.tsx`:
  - Dropdown for source type (Tushare / AKShare / BaoStock)
  - Dropdown for data type (基础信息 / 实时行情 / 历史K线 / 财务数据)
  - Optional date range picker (for daily_quote)
  - Optional stock code input (for single stock sync)
  - Validate: check if source is configured before enabling sync button
- [x] T021 [P] [US1] Create `SyncProgress.tsx` in `frontend/src/components/sync/SyncProgress.tsx`:
  - Progress bar with percentage (processed / total)
  - Status indicator (running / completed / failed)
  - Success/fail counts display
  - Animated spinner for running state
- [x] T022 [US1] Create `SyncPanel.tsx` in `frontend/src/pages/SyncPanel.tsx`:
  - Page layout: DataSourceSelector (top) + SyncProgress (middle) + SyncHistoryList (bottom)
  - Wire up syncStore + syncService
  - Handle SSE events: `sync_started` → update state, `sync_progress` → update progress bar, `sync_completed` → show success, `sync_failed` → show error
  - Integrate with AppLayout (add navigation entry for sync panel)
- [x] T023 [US1] Register sync panel route in `frontend/src/App.tsx` (route: `/sync`) + nav entry in `AppLayout.tsx`

**Checkpoint**: At this point, User Story 1 should be fully functional — user can select a data source + type, trigger sync, watch real-time progress, and verify data in database

---

## Phase 4: User Story 2 — 查看同步状态与历史 (Priority: P2)

**Goal**: 用户在同步侧边栏查看历次同步任务的执行状态、时间、数据源和数据量

**Independent Test**: 查看同步历史记录列表，验证状态、时间、数据量展示准确，失败记录显示错误信息

### Implementation for User Story 2

- [x] T024 [US2] Add Sync History API endpoint in `backend/app/routers/sync.py`:
  - `GET /api/v1/sync/tasks?page=1&page_size=20&source_type=&status=` — paginated list with filters
  - Response includes: task_id, source_type, data_type, status, counts, timestamps, duration_ms
- [x] T025 [P] [US2] Add `listTasks(params)` to `syncService.ts` in `frontend/src/services/syncService.ts`
- [x] T026 [P] [US2] Create `SyncHistory.tsx` in `frontend/src/components/sync/SyncHistory.tsx`:
  - Table/List view of sync history items
  - Each item shows: source type badge, data type, status badge (color-coded: green=completed, red=failed, blue=running), timestamp, record counts, duration
  - Pagination support
  - Filter dropdowns for source_type and status
  - Failed items show error message on hover/click
  - Retry button on failed items
- [x] T027 [US2] Integrate `SyncHistory` into `SyncPanel.tsx` (bottom section) — wire up to syncStore.loadHistory()

**Checkpoint**: At this point, User Stories 1 AND 2 both work independently — user can sync data and view sync history

---

## Phase 5: User Story 4 — 配置数据源密钥 (Priority: P2)

**Goal**: 用户在系统设置页面配置和管理各数据源的 API 密钥

**Independent Test**: 用户可以独立地添加、修改、删除数据源配置，配置完成后同步功能可正常使用

**Note**: Placed before US3 because datasource configuration is a prerequisite for sync functionality. US1 already assumes configured sources, but the configuration UI enables self-service setup.

### Implementation for User Story 4

- [x] T028 [US4] Implement DataSourceConfig API router in `backend/app/routers/datasource.py`:
  - `GET /api/v1/datasources` — list all, api_key masked
  - `POST /api/v1/datasources` — create/update config (encrypts api_key with Fernet)
  - `PUT /api/v1/datasources/{source_type}` — update config
  - `DELETE /api/v1/datasources/{source_type}` — delete config
  - Encryption: `cryptography.fernet.Fernet(os.environ["DATASOURCE_ENCRYPTION_KEY"])`
  - Masking: `api_key[:8] + "..." + api_key[-4:]`
- [x] T029 [US4] Register datasource router in `backend/app/main.py`
- [x] T030 [P] [US4] Create `datasourceService.ts` in `frontend/src/services/datasourceService.ts`:
  - `listDatasources()`, `saveDatasource(config)`, `deleteDatasource(type)`
- [x] T031 [P] [US4] Create `DataSourceConfig.tsx` in `frontend/src/components/datasource/DataSourceConfig.tsx`:
  - Form for each datasource type (Tushare, AKShare, BaoStock)
  - Tushare: API Key input (password field, masked display for existing config)
  - AKShare: Toggle enabled/disabled (no key needed)
  - BaoStock: username/password fields or toggle
  - Save button with loading state
  - Delete button with confirmation
  - Validation: Tushare requires non-empty api_key
  - Display priority number (read-only, pre-configured)
- [x] T032 [US4] Create datasource config page or integrate into settings in `frontend/src/pages/` (route: `/settings/datasources` or embedded in sync panel as a tab)

**Checkpoint**: At this point, Users can self-configure datasource credentials without manual intervention

---

## Phase 6: User Story 3 — 数据查询与验证 (Priority: P3)

**Goal**: 用户在同步完成后通过个股分析页面查询已同步的股票数据，按优先级展示

**Independent Test**: 在个股分析页面输入股票代码，验证能查询到同步后的数据，多数据源共存时按 Tushare > AKShare > BaoStock 优先级返回

### Implementation for User Story 3

- [x] T033 [US3] Implement Stock Data Query API router in `backend/app/routers/stock_data.py`:
  - `GET /api/v1/stocks/{code}` — basic info, returns all available data_sources
  - `GET /api/v1/stocks/{code}/quote` — latest quote, uses DataPriorityService to select highest priority source, checks Redis cache first
  - `GET /api/v1/stocks/{code}/daily?start_date=&end_date=&period=` — K-line history, checks Redis cache first
  - `GET /api/v1/stocks/{code}/financial` — financial data, checks Redis cache first
  - Cache strategy: Redis get → miss → MySQL query → Redis set with TTL → return
  - TTL: quote=5min, basic=24h, daily=24h, financial=24h
- [x] T034 [US3] Register stock_data router in `backend/app/main.py`
- [x] T035 [P] [US3] Create `stockDataService.ts` in `frontend/src/services/stockDataService.ts`:
  - `getStockBasicInfo(code)`, `getStockQuote(code)`, `getStockDaily(code, params)`, `getStockFinancial(code)`
- [x] T036 [US3] Integrate with existing `StockAnalysisPage.tsx` — add data source indicator badge showing which source the data comes from

**Checkpoint**: All user stories are now independently functional — data sync, history, config, and query all work end-to-end

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [x] T037 [P] Add Redis cache fallback logic: if Redis connection fails, gracefully degrade to direct MySQL queries
- [x] T038 [P] Add error boundary and loading states to all frontend components (SyncPanel, SyncHistory, DataSourceConfig)
- [x] T039 Add "不构成投资建议" disclaimer to sync panel page
- [x] T040 [P] Update `quickstart.md` with environment variable setup instructions and first-sync walkthrough
- [x] T041 Validate full sync flow end-to-end: configure datasource → trigger sync → watch progress → query data

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — **BLOCKS all user stories**
  - T004-T005 (Domain models + interfaces) can start in parallel with T002-T003
  - T006 (Migration) depends on T004 (models defined)
  - T007-T009 (Repository implementations) depend on T005 (interfaces) and T006 (tables exist)
  - T010-T011 (Domain services) depend on T004 (entities defined)
  - T012 (Sync Executor) depends on T010 (cleaner), T011 (priority), T007-T009 (repos), T013-T015 (clients)
  - T013-T015 (API Clients) can run in parallel, depend on T002 (encryption key config)
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - US1 (P1): Depends on T012 (Sync Executor)
  - US2 (P2): Depends on US1 (sync history builds on sync API)
  - US4 (P2): Depends on T007 (DataSourceRepo), can run in parallel with US1
  - US3 (P3): Depends on T007-T009 (Stock Data Repos), T011 (Priority Service), T003 (Redis Cache)
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 4 (P2)**: Can start after Foundational — provides self-service config UI
- **User Story 1 (P1)**: Can start after Foundational — core sync functionality
- **User Story 2 (P2)**: Depends on US1 — history viewing builds on sync task infrastructure
- **User Story 3 (P3)**: Can start after Foundational — query is independent of sync UI

### Suggested Execution Order (single developer)

```
Phase 1 (T001)
  → Phase 2 (T002-T015, parallelize where possible)
    → Phase 5 (T028-T032, US4: config UI — needed for US1 demo)
    → Phase 3 (T016-T023, US1: sync trigger + progress)
    → Phase 4 (T024-T027, US2: sync history)
    → Phase 6 (T033-T036, US3: data query)
    → Phase 7 (T037-T041, polish)
```

### Within Each User Story

- Models before services
- Services before endpoints
- Backend before frontend
- Core implementation before integration

### Parallel Opportunities

```bash
# Phase 2 parallel groups:
# Group A: T002 (config) + T003 (redis) + T004 (entities) + T005 (interfaces)
# Group B: T007 (datasource repo) + T008 (sync repo) + T009 (stock repo) [after T005+T006]
# Group C: T013 (tushare) + T014 (akshare) + T015 (baostock) [after T002]
# Group D: T010 (cleaner) + T011 (priority) [after T004]

# Phase 3 parallel:
# T018 (service) + T019 (store) + T020 (selector) + T021 (progress)

# Phase 4 parallel:
# T025 (service) + T026 (history component)

# Phase 5 parallel:
# T030 (service) + T031 (config component)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001)
2. Complete Phase 2: Foundational (T002-T015) — **CRITICAL — blocks all stories**
3. Complete Phase 3: User Story 1 (T016-T023)
4. **STOP and VALIDATE**: Test sync flow — select Tushare → basic_info → sync → verify data in MySQL
5. Demo sync panel with real-time progress

### Incremental Delivery

1. Setup + Foundational → Foundation ready (~2 days)
2. Add US4 (config UI) → Users can configure datasources (~1 day)
3. Add US1 (sync trigger) → Users can sync data with progress (~2 days)
4. Add US2 (sync history) → Users can view past syncs (~1 day)
5. Add US3 (data query) → Users can query synced data (~1.5 days)
6. Polish → Error handling, cache, validation (~0.5 days)
7. Each story adds value without breaking previous stories

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- All prices/ratios use Python `Decimal` type
- Data priority order: Tushare (1) > AKShare (2) > BaoStock (3)
- Sync uses SSE (Server-Sent Events) for real-time progress
- Redis cache auto-degrades to MySQL on connection failure
- API keys encrypted with Fernet symmetric encryption
- Commit after each task or logical group
