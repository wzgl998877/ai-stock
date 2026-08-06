# SSE Event Contract: 缠论重算与回测进度

**Date**: 2026-08-04
**范式**：复用后端「范式 A」（`sync_executor.py:60-62`）——带命名事件 + 后台解耦 + Queue；前端 fetch+ReadableStream（`stockAnalysisService.ts:45-103`），需带 `getAuthHeaders()`。

---

## 帧格式

```
event: <event_type>
data: <json>

```

（每帧以 `\n\n` 结尾；30s 无事件发心跳 `": heartbeat\n\n"`）

## 事件类型

### 重算 `POST /api/v1/strategy/recalculate`

| event | data | 说明 |
|---|---|---|
| `calc_started` | `{ "period","total" }` | 开始，total=待算股票数 |
| `calc_progress` | `{ "stock_code","status":"done"|"skipped"|"failed","reason":null }` | 每只完成推送一次 |
| `data_error` | `{ "message":"数据未更新" }` | 最新 K 线日期 < 今日（盘中/未同步） |
| `calc_completed` | `{ "total","success","failed","duration_ms","algo_version" }` | 结束 |
| `calc_error` | `{ "message" }` | 致命错误 |
| `heartbeat` | （注释行） | 保活 |

### 回测 `POST /api/v1/backtest/run`

| event | data | 说明 |
|---|---|---|
| `backtest_started` | `{ "range","stock_count" }` | |
| `backtest_progress` | `{ "stock_code","signals_found" }` | 每只完成推送 |
| `backtest_completed` | `{ "report_id","signal_total","excluded_invalidated","duration_ms" }` | 含 report_id |
| `backtest_error` | `{ "message" }` | |

---

## 后端实现要点

- `StreamingResponse(event_generator(), media_type="text/event-stream", headers={ Cache-Control:no-cache, Connection:keep-alive, "X-Accel-Buffering":"no" })`（复用 `sync.py:88-96`）。
- 长任务跑在独立后台 task + 独立 DB session（`async with session_factory()`，参照 `sync_executor._run_sync_background`），SSE generator 仅从 `asyncio.Queue` 读事件；SSE 断开不中断落库。
- 超时保护：单股计算 `asyncio.wait_for(timeout=30)`；整任务参照 `stock_analysis_timeout=300` 配置项新加 `chanlun_backtest_timeout`。

## 前端实现要点

- `strategyService.recalculate(...)` / `runBacktest(...)` 返回 `AbortController`（参照 `stockAnalysisService.streamStockAnalysis`）。
- 解析：`response.body.getReader()` + `TextDecoder`，`buffer.split('\n\n')` 切帧，逐行解析 `event:`/`data:`，`JSON.parse(data)`。
- UI：进度条（`total` vs 已推送 progress 数）+ loading + 停止按钮（`abort`）+ 完成后刷新对应 store。
- 事件类型枚举追加到 `domain/types.ts`（如 `StrategySSEEvent`）。
