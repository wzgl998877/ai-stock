# REST API Contract: 缠论策略监控与信号回测

**Date**: 2026-08-04
**统一前缀**：`/api/v1/strategy`（监控）、`/api/v1/backtest`（回测）
**鉴权**：全部 `Depends(get_current_user)`，注入 `X-User-Id/X-User-Account/X-User-Name` 头（复用 `app/core/deps.py`）；数据按 `current_user.user_id` 隔离。
**SSE 规范**：见 [sse-events.md](./sse-events.md)。

---

## 监控相关

### 1. 批量获取自选股双周期最新信号（徽标）

`GET /api/v1/strategy/watchlist-signals`

- **用途**：自选股列表信号列一次拉齐（复用现有批量行情范式）。
- **Response 200**：
  ```json
  {
    "items": [
      {
        "stock_code": "300750",
        "stock_name": "宁德时代",
        "daily": { "signal_type": "buy3", "signal_time": "2026-08-03", "confirmed_at": "2026-08-03T15:05:00", "trigger_price": 245.30 },
        "m30":    { "signal_type": null, "signal_time": null, "confirmed_at": null, "trigger_price": null },
        "daily_status": "monitored_nodata",
        "m30_status": "disabled"
      }
    ]
  }
  ```
  - `signal_type`：`buy1/buy2/buy3/sell1/sell2/sell3` 或 `null`（无近期信号）
  - `daily_status`/`m30_status`：`monitored`（有信号）/ `monitored_nodata`（监控中无信号）/ `disabled`（已关闭）/ `insufficient_data`
- **缓存**：Redis `strategy:watchlist-signals:{user_id}` TTL 600s；信号落库时主动失效。

### 2. 单股当前信号状态

`GET /api/v1/strategy/stocks/{code}/signals?period=daily`

- **Response 200**：`{ "code","name","period","signals":[...], "structure":{ "last_kline_time","strokes","segments","zhongshu" } }`

### 3. 单股信号历史

`GET /api/v1/strategy/stocks/{code}/signal-history?period=daily&signal_type=buy1&page=1&page_size=20`

- **Response 200**：`{ "items":[{signal_type,period,structure_level,signal_time,confirmed_at,trigger_price,algo_version,status,invalidated_reason}], "total" }`
- 失效信号以 `status="invalidated"` 返回，前端删除线展示。

### 4. 单股结构快照（K 线渲染）

`GET /api/v1/strategy/stocks/{code}/structure?period=daily`

- **Response 200**：`{ "strokes":[{start:{time,price},end:{time,price},direction,confirmed}], "segments":[...], "zhongshu":[{zd,zg,dd,gg,enter_time,exit_time}], "last_kline_time","algo_version" }`
- **缓存**：Redis `strategy:structure:{code}:{period}` TTL 600s。

### 5. 更新监控开关

`PUT /api/v1/strategy/stocks/{code}/config`

- **Body**：`{ "daily_enabled": true, "m30_enabled": false }`
- **Response 200**：回显更新后配置。
- **联动**：自选股移除时由 watchlist UseCase 触发关闭（不在此接口）。

### 6. 手动重算（SSE）

`POST /api/v1/strategy/recalculate`

- **Body**：`{ "period": "daily", "stock_codes": ["300750"] }`（`stock_codes` 可空=全部启用股票）
- **Response**：`text/event-stream`，事件见 sse-events.md。
- **校验**：数据未更新（最新 K 线日期 < 今日）→ 发 `data_error` 事件提示「数据未更新」，不静默跳过。

### 7. 计算任务状态

`GET /api/v1/strategy/run-status`

- **Response 200**：`{ "daily": {last_run_at,duration_ms,total,success,failed,failed_detail,algo_version}, "m30": {...} }`

---

## 回测相关

### 8. 发起回测（SSE）

`POST /api/v1/backtest/run`

- **Body**：`{ "range": "3y", "periods": ["daily","m30"], "stock_codes": null }`（null=全部启用自选股）
- **Response**：`text/event-stream`，事件见 sse-events.md；完成后 `report_id` 随 `done` 事件返回。
- **校验**：回测与监控复用 `ChanlunService`（SC-005 一致性）。

### 9. 报告列表

`GET /api/v1/backtest/reports?page=1&page_size=10`

- **Response 200**：`{ "items":[{report_id,range_label,start_date,end_date,stock_count,signal_total,algo_version,status,create_time}], "total" }`

### 10. 报告详情（汇总表）

`GET /api/v1/backtest/reports/{id}`

- **Response 200**：
  ```json
  {
    "meta": { "range_label","stock_count","signal_total","excluded_invalidated","algo_version","benchmark_return","finished_at" },
    "summary": [
      { "period":"daily","signal_type":"buy1","window":20,"sample":58,"win_rate":0.62,"avg_return":0.041,"median_return":0.023,"profit_loss_ratio":1.35,"note":null }
    ]
  }
  ```
  - `note`：`sample_insufficient`（样本<10）/ `window_incomplete` / null

### 11. 报告明细下钻

`GET /api/v1/backtest/reports/{id}/details?period=daily&signal_type=buy1&window=20&stock_code=&page=1&page_size=20`

- **Response 200**：`{ "items":[{stock_code,signal_type,signal_time,trigger_price,ret_5,ret_10,ret_20,ret_60,window_complete}], "total" }`

---

## 错误约定

- 统一走 `app/core/exceptions.py`，Response 形如 `{ "detail": "..." }`，与现有 router 一致。
- 鉴权缺失：401；越权访问他人数据：403；股票不存在：404；区间/参数非法：422。
