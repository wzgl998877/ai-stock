---
description: "Task list for 缠论策略监控与信号回测"
---

# Tasks: 缠论策略监控与信号回测

**Input**: Design documents from `/specs/009-chanlun-signal-system/`
**Prerequisites**: plan.md、spec.md、research.md、data-model.md、contracts/、quickstart.md
**Tests**: 宪法 `rules/testing.md` 强制单元测试门禁；缠论引擎与一致性采用 test-first，UI 关键路径含 vitest。
**Organization**: 按用户故事分组（US1 监控标注 / US2 结构与历史 / US3 回测 / US4 配置与状态），每故事可独立实现与验收。

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 可并行（不同文件、无未完成依赖）
- **[Story]**: 所属用户故事
- 所有路径为项目实际路径：`backend/app/...`、`frontend/src/...`

---

## Phase 1: Setup (共享基础设施)

**Purpose**: 目录结构与配置就位

- [X] T001 [P] 在 `backend/app/domain/{entities,services,repositories}` 与 `backend/app/application/{use_cases,dtos}` 下按 plan.md 结构新建缠论相关空模块占位（仅目录/`__init__.py`）
- [X] T002 [P] 新增配置项到 `backend/app/core/config.py`：`chanlun_scan_enabled`(默认True)、`chanlun_scan_daily_cron`、`chanlun_backtest_timeout`(默认300)、`chanlun_concurrency`(默认10)、`chanlun_algo_version`(默认"1.0.0")
- [X] T003 [P] 在 `frontend/src/domain/{types.ts,constants.ts}` 追加 `SignalType`/`SignalStatus`/`Period='daily'|'m30'`/窗口常量/免责声明文案常量

---

## Phase 2: Foundational (阻塞性地基)

**Purpose**: 缠论纯函数引擎 + 黄金样本 + 持久化 + 数据源 + 共享前端工具。⚠️ 所有用户故事须等本阶段完成。

### 2.1 算法引擎（test-first，对标 `indicator_service.py`）

- [X] T004 [P] 新增枚举 `backend/app/domain/models/chanlun_enums.py`：`SignalType`/`StrategyPeriod`/`SignalStatus`/`StructureLevel`/`WindowDays`
- [X] T005 [P] 新增实体 `backend/app/domain/entities/chanlun.py`（Fractal/Bi/Segment/Zhongshu/ChanlunSignal/StructureSnapshot，dataclass）与 `backend/app/domain/entities/backtest.py`（BacktestReport/SignalDetail/Summary）
- [X] T006 [P] 准备黄金样本 `backend/tests/fixtures/chanlun_golden_samples/`（≥10 只股票区间，人工标注分型/笔/线段/中枢/买卖点 JSON；含趋势上/下/盘整三类）
- [X] T007 [P] 编写分层失败测试 `backend/tests/unit/domain/test_chanlun_inclusion_fractal_bi.py`（包含处理、顶底分型、笔；基于 T006 样本断言）——须先 FAIL
- [X] T008 实现 `backend/app/domain/services/chanlun_service.py` 的包含处理 + 顶底分型 + 笔（纯函数，对标 `indicator_service.py`），使 T007 通过
- [X] T009 [P] 编写失败测试 `backend/tests/unit/domain/test_chanlun_segment_zhongshu.py`（特征序列线段、中枢 [ZD,ZG]/扩展）——须先 FAIL
- [X] T010 实现 `chanlun_service.py` 的线段（特征序列法，含第一/第二种破坏）+ 中枢识别，使 T009 通过
- [X] T011 [P] 编写失败测试 `backend/tests/unit/domain/test_chanlun_divergence.py`（价格幅度 + MACD 面积双条件；趋势背驰 vs 盘整背驰）——须先 FAIL
- [X] T012 实现 `backend/app/domain/services/chanlun_divergence.py`（输入接收 MACD BAR 序列，不在引擎内重算 MACD），使 T011 通过
- [X] T013 [P] 编写失败测试 `backend/tests/unit/domain/test_chanlun_buy_sell_points.py`（一/二/三类买卖点确认时机与去重）——须先 FAIL
- [X] T014 实现 `chanlun_service.py` 的一/二/三类买卖点识别 + `compute_all()` 组装入口（输入 OHLCV+MACD 序列，输出 Signal 列表 + StructureSnapshot），使 T013 通过
- [X] T015 在 `backend/tests/unit/domain/test_chanlun_service.py` 汇总：算法版本号内嵌、未收盘 K 线不参与、同位置信号去重

### 2.2 持久化（对标 `StockIndicatorModel`/`mysql_stock_indicator_repo.py`）

- [X] T016 [P] 在 `backend/app/infrastructure/db/models.py` 追加 7 个 ORM 模型（`t_strategy_signal`/`t_strategy_structure`/`t_strategy_monitor_config`/`t_strategy_run_log`/`t_backtest_report`/`t_backtest_signal_detail`/`t_backtest_summary`），字段见 data-model.md
- [X] T017 在 `backend/app/infrastructure/db/migrations/env.py` 的模型 import 列表补入 T016 新模型（否则 autogenerate 检测不到）
- [X] T018 生成并校验 Alembic 迁移 `backend/app/infrastructure/db/migrations/versions/{rev}_add_chanlun_strategy_tables.py`：`alembic revision --autogenerate`；核对 upgrade/downgrade（create_table+索引+唯一约束）；`alembic upgrade head` 验证
- [X] T019 [P] 新增 Repository 接口 `backend/app/domain/repositories/chanlun_repo.py`（ABC）与实现 `backend/app/infrastructure/repositories/mysql_chanlun_repo.py`（信号 upsert/查询/失效标记 + 结构快照覆盖式 upsert + run_log）
- [X] T020 [P] 新增 Repository 接口 `backend/app/domain/repositories/backtest_repo.py`（ABC）与实现 `backend/app/infrastructure/repositories/mysql_backtest_repo.py`（报告/明细/汇总）
- [X] T021 [P] 在 `backend/app/domain/repositories/watchlist_repo.py` 与 `backend/app/infrastructure/repositories/mysql_watchlist_repo.py` 新增 `get_all_items_by_user(user_id)`（join 分组表过滤 user_id，按 stock_code 去重）

### 2.3 数据源（research.md D1/D2）

- [X] T022 在 `backend/app/infrastructure/market/sina_kline_client.py` 扩展 `fetch(code, period='m30')`（scale=30，前复权，时间戳取区间结束时刻），并写一段一次性验证脚本确认可拿 ≥3 年 30 分钟 K（全文硬前置）
- [X] T023 [P] 在 `backend/app/application/sync/sync_executor.py` 或独立函数新增 30 分钟历史回补入口（落库到 `t_stock_daily_quote` period='m30'，复用 `upsert_daily_batch` + `_clear_kline_cache`）

### 2.4 共享前端工具（research.md D6）

- [X] T024 [P] 新建 `frontend/src/utils/marketTime.ts` 统一 `isMarketOpen()`（北京时区 A 股时段）+ `isTradingDay()`；重构 `WatchlistPage.tsx` 与 `frontend/src/store/stockDetailStore.ts` 引用之，删除两处重复实现

**Checkpoint**: 引擎单测全绿、迁移可升级、30 分钟数据可拉取、前端时区统一 → 用户故事可并行开工。

---

## Phase 3: User Story 1 - 自选股缠论信号监控与标注 (Priority: P1) 🎯 MVP

**Goal**: 收盘后自动计算全部启用自选股的双周期信号，自选股列表显示徽标、K 线显示买卖点箭头。
**Independent Test**: 加入自选股→触发一次重算→列表见徽标、K 线见箭头。

### 后端

- [X] T025 [P] [US1] 新增 DTO `backend/app/application/dtos/chanlun_dto.py`（SignalResponse/WatchlistSignalItem/StructureResponse/ConfigBody 等，价格 `Optional[Decimal]`）
- [X] T026 [US1] 实现 `backend/app/application/use_cases/chanlun_calc.py`（单股：读日K/m30K + MACD（缺则先调 `IndicatorCalcUseCase`）→ `ChanlunService.compute_all` → 信号幂等落库 + 结构快照覆盖），对标 `indicator_calc.py`
- [X] T027 [US1] 实现 `backend/app/application/use_cases/chanlun_monitor.py`（扫描 `get_all_items_by_user` 启用股票；数据新鲜度检查（最新 bar 日期未推进则记 `no_new_data` 跳过）；并发 ≤`chanlun_concurrency`；写 run_log）
- [X] T028 [P] [US1] 新增 `backend/app/infrastructure/scheduler/chanlun_scheduler.py`（日线 `mon-fri 15:40` + m30 八时点 10:05/10:35/11:05/11:35/13:35/14:05/14:35/15:05），并在 `backend/app/main.py` lifespan 注册（开关 `chanlun_scan_enabled`），对标 `event_crawler_scheduler.py`
- [X] T029 [US1] 新增路由 `backend/app/routers/chanlun.py`：`GET /api/v1/strategy/watchlist-signals`（批量徽标，Redis `strategy:watchlist-signals:{user_id}` TTL600）、`GET /stocks/{code}/signals`、`POST /recalculate`（SSE），并注册到 `main.py:239-249`

### 前端

- [X] T030 [P] [US1] 新增 `frontend/src/services/strategyService.ts`（getWatchlistSignals/getSignals/recalculate 等），并抽 `frontend/src/services/sse.ts`（fetch+ReadableStream+`getAuthHeaders()`+AbortController，复用 `stockAnalysisService` 逻辑）
- [X] T031 [P] [US1] 新增 `frontend/src/store/strategyStore.ts`（watchlistSignals/Loading/Error、recalcRunning/Progress、fetchWatchlistSignals、recalculate、stopRecalc）
- [X] T032 [P] [US1] 新增 `frontend/src/components/strategy/SignalBadge.tsx`（双周期徽标：买绿▲/卖红▼/灰—/灰「不足」/「已停用」；Tooltip 含信号信息 + 「不构成投资建议」 + 「AI 深度分析」入口）
- [X] T033 [US1] 在 `frontend/src/pages/WatchlistPage.tsx` 表格新增「信号」列（双周期 `SignalBadge`）+ 信号状态筛选；徽标数据由 `strategyStore.fetchWatchlistSignals` 提供，随现有 30 秒行情刷新一并更新
- [X] T034 [US1] 在 `frontend/src/components/stock/KLineChart.tsx` 新增 `signalMarks` prop，主图 series 追加 `markPoint`（买卖点箭头，角标 1/2/3）；补 `frontend/src/tests/components/stock/KLineChart.test.tsx` 用例
- [X] T035 [US1] `frontend/src/store/stockDetailStore.ts`：`fetchStockDetail`/`fetchKlineData` 后并行拉 `strategyService.getStructure` 组装 `signalMarks`；`IndicatorToggle` 区新增「缠论」开关（默认开）写入 store
- [X] T036 [P] [US1] 新增 `frontend/src/application/useStrategy.ts`（SSE 编排 hook：订阅重算进度、停止、完成后刷新徽标）

**Checkpoint**: US1 可独立验收——重算后自选股列表有徽标、K 线有买卖点箭头。

---

## Phase 4: User Story 2 - 缠论结构与信号历史 (Priority: P2)

**Goal**: K 线叠加笔/线段/中枢，信号历史标签页，定位到 K 线。
**Independent Test**: 已有信号的股票→开启缠论图层见笔/线段/中枢→历史 Tab 见列表→点击定位 K 线。

### 后端

- [X] T037 [P] [US2] 在 `chanlun.py` 路由新增 `GET /stocks/{code}/structure`（返回 strokes/segments/zhongshu，Redis `strategy:structure:{code}:{period}` TTL600）、`GET /stocks/{code}/signal-history`（分页、含 invalidated）

### 前端

- [X] T038 [US2] 扩展 `KLineChart.tsx`：新增 `structure`/`highlightDate` props；`markLine` 渲染笔/线段（未确认 dashed）、`markArea` 渲染中枢 [ZD,ZG] 半透明矩形（Tooltip 显示 ZD/ZG/起止）；`highlightDate` 经 `dataZoom.startValue/endValue` 定位
- [X] T039 [US2] `frontend/src/pages/StockDetailPage.tsx`：底部 Tabs 新增「缠论信号」标签页（信号历史列表 + 失效信号删除线 + 失效原因）；解析路由 `?signalDate=&period=` 写入 `stockDetailStore.highlightDate`
- [X] T040 [P] [US2] 新增 `frontend/src/components/strategy/SignalHistoryList.tsx`（按周期/类型筛选、分页、「在 K 线图中查看」→ `navigate('/market/stock/${code}?signalDate=...&period=...')`）
- [X] T041 [US2] `KLineChart.tsx` 在周期为分时/周K/月K 时隐藏缠论图层并提示「当前周期暂不支持缠论分析」

**Checkpoint**: US1+US2 均可独立工作。

---

## Phase 5: User Story 3 - 缠论信号历史回测 (Priority: P2)

**Goal**: 对自选股历史信号回测，输出胜率/收益汇总 + 明细下钻 + 分布图。
**Independent Test**: 选区间发起回测→流式进度→汇总表（胜率着色）→点击单元格看明细→定位 K 线。

### 后端

- [X] T042 [US3] 实现 `backend/app/application/use_cases/chanlun_backtest.py`：对每只自选股用 **同一 `ChanlunService`**（SC-005）重算区间信号 → 计算 5/10/20/60 窗口收益（窗口越界置 `window_complete=false`）→ 聚合 summary → 写 report/detail/summary；剔除 invalidated 仅计数
- [X] T043 [US3] 在 `chanlun.py` 或新路由新增回测端点：`POST /api/v1/backtest/run`（SSE，后台解耦 + Queue，范式 A）、`GET /reports`、`GET /reports/{id}`、`GET /reports/{id}/details`
- [X] T044 [P] [US3] 新增一致性集成测试 `backend/tests/integration/test_chanlun_consistency.py`：对黄金样本股，监控增量结果 vs 回测全量结果 100% 一致（SC-005）

### 前端

- [X] T045 [P] [US3] `strategyService.ts` 增 `runBacktest`/`getReports`/`getReport`/`getReportDetails`
- [X] T046 [P] [US3] 新增 `frontend/src/pages/BacktestPage.tsx`（区间选择 1/3/5y → 发起 → SSE 进度条 → 完成展示报告）
- [X] T047 [P] [US3] 新增 `frontend/src/components/strategy/BacktestSummaryTable.tsx`（period 切换；胜率>50% 绿/<50% 红；样本<10 标注「样本不足」；点击单元格打开明细 Drawer；附基准涨跌 + 三条免责声明）
- [X] T048 [P] [US3] 新增 `frontend/src/components/strategy/BacktestDetailDrawer.tsx`（明细列表 + 「在 K 线图中查看」）
- [X] T049 [P] [US3] 新增 `frontend/src/components/strategy/ReturnDistributionChart.tsx`（20 日窗口收益分布直方图，ECharts）

**Checkpoint**: US3 可独立验收——回测出成绩单且与监控一致。

---

## Phase 6: User Story 4 - 监控配置与计算状态 (Priority: P3)

**Goal**: 逐股/逐周期开关、计算状态面板、手动重算。
**Independent Test**: 关闭某股 m30→不再出 m30 徽标；面板触发重算见进度。

- [X] T050 [P] [US4] 在 `chanlun.py` 路由新增 `PUT /stocks/{code}/config`、`GET /run-status`
- [X] T051 [US4] `chanlun_monitor.py` 读取 `t_strategy_monitor_config` 决定扫描范围；自选股移除时由 `backend/app/application/use_cases/watchlist.py` 同步关闭/删除该股监控配置
- [X] T052 [US4] `strategyStore` 增 `runStatus`/`updateConfig`/`fetchRunStatus`
- [X] T053 [US4] 新增 `frontend/src/pages/StrategyMonitorPage.tsx`（计算状态卡片 + 「立即重算」按钮 + SSE 进度 + 算法版本）；路由 `App.tsx` 加 `/strategy` 与 `/strategy/backtest`
- [X] T054 [US4] 在 `frontend/src/components/layout/AppLayout.tsx:248-257` 启用「策略监控」菜单项（去 disabled）指向 `/strategy`
- [X] T055 [US4] `WatchlistPage.tsx` 信号列增加逐股/逐周期监控开关（调 `updateConfig`），关闭后徽标显示「已停用」

**Checkpoint**: 全部 4 个用户故事均可独立工作。

---

## Phase 7: Polish & Cross-Cutting

- [X] T056 [P] FR-016 文案审计：全部信号徽标/Tooltip/K 线 Tooltip/回测页含「规则参考信号，不构成投资建议」；移除任何「应立即买卖」「可稳定盈利」表述
- [X] T057 [P] FR-017 联动：`frontend/src/pages/StockAnalysisPage.tsx` 挂载 effect 支持 `?code=` 预填（无 recordId 时检查 code → setStock）；SignalBadge 的「AI 深度分析」跳转 `navigate('/stock-analysis?code=${code}')`；AI 结论与规则信号并列展示、互不覆盖
- [X] T058 [P] DESIGN.md 合规复核：Card/Table tabular-nums、Skeleton/Empty/Alert 三态、蓝调阴影、紫主色、圆角 4-8px；修复无结构堆叠
- [X] T059 后端分层复核（宪章红线）：`ChanlunService` 不依赖 FastAPI/DB/AI；Router 仅 SSE/鉴权；前端无直连 fetch（全走 `services/`）
- [X] T060 价格字段 Decimal 复核（宪章数据约束）：信号 trigger_price、回测 ret_* 在实体/ORM 用 Decimal，router 序列化转 float
- [X] T061 运行 `quickstart.md` 上线门禁清单全部勾选；`pytest` + `npm run test` + `npm run build`（tsc）+ `alembic upgrade/downgrade` 双向验证
- [X] T062 [P] 文档：在 `docs/v2/product-overview-v2.md` 与 `docs/v2/market-data-prd-v2.md` 把「策略监控（即将推出）」更新为已实现并引用本 spec；同步 ECharts v5→v6 文档漂移（research.md D3）

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: 无依赖，立即开始
- **Foundational (Phase 2)**: 依赖 Setup；**阻塞全部用户故事**；引擎 test-first 是关键路径（T006→T008→T009→T010→T011→T012→T013→T014 顺序）
- **US1 (Phase 3)**: 依赖 Foundational；MVP
- **US2/US3/US4 (Phase 4-6)**: 各依赖 Foundational；可并行（若多人），否则按 P1→P2→P3 顺序
- **Polish (Phase 7)**: 依赖目标用户故事完成

### User Story Dependencies

- **US1**: 依赖 Foundational；无故事间依赖（MVP，先做）
- **US2**: 依赖 Foundational；与 US1 共享 KLineChart/store，建议在 US1 后做
- **US3**: 依赖 Foundational；复用 US1 的 `ChanlunService` 调用与 SSE 范式
- **US4**: 依赖 Foundational；依赖 US1 的 monitor use_case

### Parallel Opportunities

- Phase 1 全部 [P]；Phase 2 的 T004/T005/T006/T016/T019/T020/T021/T022/T024 互不冲突可并行
- 引擎分层测试与实现须严格交替（test 先 fail → impl → pass），不可并行
- US2/US3/US4 内 [P] 任务可并行

---

## Implementation Strategy

### MVP First (US1 Only)

1. Phase 1 Setup → Phase 2 Foundational（引擎 + 迁移 + 30 分钟数据验证）
2. Phase 3 US1 → 独立验收（重算→徽标→箭头）
3. **STOP and VALIDATE**：自选股列表见双周期徽标、K 线见买卖点箭头

### Incremental Delivery

每完成一个 US 即可独立验收与部署，不破坏前置故事。

---

## Notes

- 引擎纯函数须无 IO（宪章 Domain 约束），黄金样本是上线门禁（SC-003 ≥95%）
- 30 分钟数据走 Sina scale=30 直取（research.md D1，已确认），**不**做本地 1 分钟聚合
- 每个任务或逻辑分组后提交；检查点处停止做独立验收
- 避免：模糊任务、同文件冲突、破坏故事独立性的跨故事依赖
