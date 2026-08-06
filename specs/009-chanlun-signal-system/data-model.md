# Phase 1 Data Model: 缠论策略监控与信号回测

**Date**: 2026-08-04
**复用约定**：30 分钟 K 线复用既有 `t_stock_daily_quote`（`period='m30'`，见 research.md D1），不新建 K 线表。价格统一 `DECIMAL(12,3)`，比例 `DECIMAL(8,6)`，`user_id` 用 `VARCHAR(32)`。所有表带 `create_time`/`update_time`（`server_default=CURRENT_TIMESTAMP` + `ON UPDATE`）。

---

## 实体关系总览

```text
t_stock_daily_quote (既有, 扩展 period='m30')
        │ 读取 OHLCV
        ▼
   ChanlunService (纯函数)
        │ 产出
        ▼
t_strategy_signal ──────┐
t_strategy_structure    │  一致性比对
t_strategy_monitor_config
t_strategy_run_log
        │ 回测复用同引擎
        ▼
t_backtest_report 1───* t_backtest_signal_detail
        │ 预聚合
        ▼
t_backtest_summary
```

---

## 1. `t_strategy_signal`（缠论信号历史，核心）

| 字段 | 类型 | 说明 |
|---|---|---|
| id | BIGINT PK AUTO | |
| user_id | VARCHAR(32) | 所属用户（冗余便于查询，监控配置已按用户） |
| stock_code | VARCHAR(10) | 股票代码 |
| period | VARCHAR(8) | `daily` / `m30` |
| signal_type | VARCHAR(8) | `buy1`/`buy2`/`buy3`/`sell1`/`sell2`/`sell3` |
| structure_level | VARCHAR(8) | `stroke`（笔）/ `segment`（线段） |
| signal_time | DATETIME | 信号发生时间（触发 K 线时间戳） |
| confirmed_at | DATETIME | 确认时间（确认 K 线收盘时间） |
| trigger_price | DECIMAL(12,3) | 信号触发价 |
| status | VARCHAR(12) | `confirmed` / `invalidated` |
| invalidated_reason | VARCHAR(64) | 失效原因（如 `data_source_revision`），可空 |
| algo_version | VARCHAR(16) | 算法版本（如 `1.0.0`） |
| dedup_key | VARCHAR(128) | 去重键 = stock_code|period|signal_type|signal_time|algo_version |
| create_time / update_time | DATETIME | |

**约束**：`UNIQUE(dedup_key)` 保证幂等；`INDEX(stock_code, period, signal_time DESC)`；`INDEX(user_id, status)`。
**状态机**：`confirmed` →（数据源修正）→ `invalidated`（终态，不回退）。

---

## 2. `t_strategy_structure`（缠论结构快照，供 K 线渲染）

| 字段 | 类型 | 说明 |
|---|---|---|
| id | BIGINT PK AUTO | |
| stock_code | VARCHAR(10) | |
| period | VARCHAR(8) | `daily` / `m30` |
| strokes_json | JSON | 笔列表（端点 time/price/direction） |
| segments_json | JSON | 线段列表 |
| zhongshu_json | JSON | 中枢列表（ZD/ZG/DD/GG/起止时间） |
| last_kline_time | DATETIME | 计算所依据最新 K 线时间 |
| algo_version | VARCHAR(16) | |
| update_time | DATETIME | |

**约束**：`UNIQUE(stock_code, period)`（覆盖式更新，每股每周期一行）。
**说明**：JSON 仅用于结构快照扩展字段（宪章允许）；可查询核心字段为 `stock_code/period/last_kline_time`。

---

## 3. `t_strategy_monitor_config`（逐股监控配置）

| 字段 | 类型 | 说明 |
|---|---|---|
| id | BIGINT PK AUTO | |
| user_id | VARCHAR(32) | |
| stock_code | VARCHAR(10) | |
| daily_enabled | TINYINT(1) | 默认 1 |
| m30_enabled | TINYINT(1) | 默认 1 |
| create_time / update_time | DATETIME | |

**约束**：`UNIQUE(user_id, stock_code)`。
**联动**：自选股移除时同步删除该配置（UseCase 层处理）。

---

## 4. `t_strategy_run_log`（计算任务日志）

| 字段 | 类型 | 说明 |
|---|---|---|
| id | BIGINT PK AUTO | |
| user_id | VARCHAR(32) | 可空（系统定时任务时为触发用户或 `system`） |
| period | VARCHAR(8) | `daily` / `m30` |
| trigger_type | VARCHAR(12) | `scheduled` / `manual` |
| status | VARCHAR(12) | `running` / `done` / `failed` |
| total / success / failed | INT | 股票计数 |
| failed_detail | JSON | `[{stock_code, reason}]`，如 `no_new_data`/`insufficient_data` |
| started_at / finished_at | DATETIME | |
| duration_ms | INT | |
| algo_version | VARCHAR(16) | |

**约束**：`INDEX(period, started_at DESC)`。

---

## 5. `t_backtest_report`（回测报告）

| 字段 | 类型 | 说明 |
|---|---|---|
| id | BIGINT PK AUTO | |
| user_id | VARCHAR(32) | |
| range_label | VARCHAR(4) | `1y` / `3y` / `5y` |
| start_date / end_date | DATE | 实际区间 |
| stock_count | INT | 参与股票数 |
| signal_total | INT | 信号总数 |
| excluded_invalidated | INT | 剔除的失效信号数 |
| benchmark_return | DECIMAL(8,6) | 沪深300 同期累计涨跌 |
| algo_version | VARCHAR(16) | |
| status | VARCHAR(12) | `running` / `done` / `failed` |
| create_time | DATETIME | |

**约束**：`INDEX(user_id, create_time DESC)`。

---

## 6. `t_backtest_signal_detail`（回测信号明细）

| 字段 | 类型 | 说明 |
|---|---|---|
| id | BIGINT PK AUTO | |
| report_id | BIGINT FK→t_backtest_report | |
| stock_code | VARCHAR(10) | |
| period | VARCHAR(8) | |
| signal_type | VARCHAR(8) | |
| structure_level | VARCHAR(8) | |
| signal_time | DATETIME | |
| trigger_price | DECIMAL(12,3) | |
| ret_5 / ret_10 / ret_20 / ret_60 | DECIMAL(8,6) | 各窗口收益，可空 |
| window_complete | TINYINT(1) | 窗口是否完整（false 则 ret_* 全空） |

**约束**：`UNIQUE(report_id, stock_code, period, signal_type, signal_time)`；`INDEX(report_id, period, signal_type)`。

---

## 7. `t_backtest_summary`（回测聚合统计，预聚合加速查询）

| 字段 | 类型 | 说明 |
|---|---|---|
| id | BIGINT PK AUTO | |
| report_id | BIGINT FK→t_backtest_report | |
| period | VARCHAR(8) | |
| signal_type | VARCHAR(8) | |
| window | SMALLINT | 5/10/20/60 |
| sample_count | INT | |
| win_rate | DECIMAL(8,6) | 胜率 |
| avg_return | DECIMAL(8,6) | 平均收益 |
| median_return | DECIMAL(8,6) | |
| profit_loss_ratio | DECIMAL(8,6) | 盈亏比 |
| note | VARCHAR(32) | 如 `sample_insufficient`（样本<10）/ `window_incomplete` |

**约束**：`UNIQUE(report_id, period, signal_type, window)`；可由明细重算，预聚合仅为查询性能。

---

## 领域实体（Domain Entities，纯 dataclass）

对标 `app/domain/entities/stock_indicator.py`，新增 `app/domain/entities/chanlun.py`、`backtest.py`：

- **Fractal**：type(top/bottom)、kline_index、price、time
- **Bi（笔）**：direction、start_fractal、end_fractal、kline_count、confirmed
- **Segment（线段）**：direction、start_bi、end_bi、confirmed、break_type(first/second)
- **Zhongshu（中枢）**：ZG/ZD/GG/DD、enter_time/exit_time、sub_levels[]、state(forming/extended/ended)
- **ChanlunSignal**：stock_code、period、signal_type、structure_level、signal_time、confirmed_at、trigger_price、algo_version、status
- **StructureSnapshot**：stock_code、period、strokes[]、segments[]、zhongshu[]、last_kline_time、algo_version
- **BacktestReport / BacktestSignalDetail / BacktestSummary**：与上述表一一对应

**枚举**（`app/domain/models/chanlun_enums.py`）：`SignalType`、`StrategyPeriod(daily,m30)`、`SignalStatus(confirmed,invalidated)`、`StructureLevel(stroke,segment)`、`WindowDays(5,10,20,60)`。

---

## Alembic 迁移

- 新建 `versions/{rev}_add_chanlun_strategy_tables.py`，`down_revision` 指向当前 head（探索确认 head 为 `g7h8i9j0k1l2_add_event_radar_tables.py`，实现时以 `alembic heads` 为准）。
- 必须在 `app/infrastructure/db/migrations/env.py:10-23` 的 import 列表补入新 ORM 模型，否则 autogenerate 检测不到（探索已确认此约束）。
- `upgrade()` 用 `op.create_table` + `op.create_index` + `op.create_unique_constraint`；`downgrade()` 反向 drop。范式参照 `e5f6a7b8c9d0_add_market_data_module2_tables.py`。
- `period='m30'` 无需表结构变更（既有 `period VARCHAR(10)` 足够），仅在应用层枚举扩展，**无 DDL**。

---

## 验证规则（来自 spec）

- 数据不足：日线 <60 根、m30 <120 根 → 不计算、不写信号，仅在 run_log 记 `insufficient_data`。
- 信号幂等：`dedup_key` 唯一约束；重复计算不新增、不改写已确认信号。
- 失效留痕：数据源修正时 `status→invalidated` + `invalidated_reason`，原行保留。
- 回测窗口越界：`window_complete=false`，`ret_*` 全空，不计入收益统计但仍计入 sample_count。
