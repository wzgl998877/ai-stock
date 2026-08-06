# Frontend Service & Store Contract

**Date**: 2026-08-04
**约定**：所有 HTTP 经 `services/`（宪章红线），axios 实例复用 `services/api.ts`（含 `getAuthHeaders()`）。SSE 用 fetch+ReadableStream。

---

## `services/strategyService.ts`（新增）

```ts
export interface WatchlistSignalItem { stock_code: string; stock_name: string; daily: SignalSummary|null; m30: SignalSummary|null; daily_status: SignalStatus; m30_status: SignalStatus; }
export interface SignalSummary { signal_type: SignalType|null; signal_time: string|null; confirmed_at: string|null; trigger_price: number|null; }
export type SignalType = 'buy1'|'buy2'|'buy3'|'sell1'|'sell2'|'sell3';
export type SignalStatus = 'monitored'|'monitored_nodata'|'disabled'|'insufficient_data';

export const strategyService = {
  getWatchlistSignals: () => api.get('/api/v1/strategy/watchlist-signals').then(r => r.data.items as WatchlistSignalItem[]),
  getSignals: (code: string, period: Period) => api.get(`/api/v1/strategy/stocks/${code}/signals`, { params: { period } }).then(r => r.data),
  getSignalHistory: (code: string, params) => api.get(`/api/v1/strategy/stocks/${code}/signal-history`, { params }).then(r => r.data),
  getStructure: (code: string, period: Period) => api.get(`/api/v1/strategy/stocks/${code}/structure`, { params: { period } }).then(r => r.data),
  updateConfig: (code: string, body) => api.put(`/api/v1/strategy/stocks/${code}/config`, body).then(r => r.data),
  getRunStatus: () => api.get('/api/v1/strategy/run-status').then(r => r.data),
  recalculate: (body, onEvent) => streamSSE('/api/v1/strategy/recalculate', 'POST', body, onEvent),  // 返回 AbortController
  runBacktest: (body, onEvent) => streamSSE('/api/v1/backtest/run', 'POST', body, onEvent),
  getReports: (params) => api.get('/api/v1/backtest/reports', { params }).then(r => r.data),
  getReport: (id) => api.get(`/api/v1/backtest/reports/${id}`).then(r => r.data),
  getReportDetails: (id, params) => api.get(`/api/v1/backtest/reports/${id}/details`, { params }).then(r => r.data),
};
```

`streamSSE` 抽到 `services/sse.ts`（或复用 `stockAnalysisService` 内逻辑），统一 fetch+ReadableStream+`getAuthHeaders()`+AbortController。

## `store/strategyStore.ts`（新增，zustand）

对标 `stockDetailStore.ts`：

```ts
interface StrategyState {
  watchlistSignals: WatchlistSignalItem[]; signalsLoading: boolean; signalsError: string|null;
  runStatus: RunStatus|null;
  recalcRunning: boolean; recalcProgress: {done:number; total:number};
  fetchWatchlistSignals: () => Promise<void>;   // 供 WatchlistPage 列调用
  fetchRunStatus: () => Promise<void>;
  recalculate: (period, codes?) => Promise<void>; // 内部调 service.recalculate + onEvent 更新 recalcProgress
  stopRecalc: () => void;
  clear: () => void;
}
```

## `store/stockDetailStore.ts`（修改）

新增字段：`highlightDate?: string`、`signalMarks?: EChartsMarkPoint[]`、`structureData?: StructureData`。
- `fetchStockDetail(code, query)` 解析 `?signalDate=&period=`，设置 `highlightDate`。
- `fetchKlineData` 后并行 `strategyService.getStructure(code, period)` 填 `structureData`/`signalMarks`。

## `components/stock/KLineChart.tsx`（修改）

新增 props：`signalMarks?: MarkPoint[]`、`structure?: { strokes; segments; zhongshu }`、`highlightDate?: string`。
- `buildDailyOption` 内：
  - 主图 series 追加 `markPoint`（买卖点箭头，`buy` 绿 `▲`/`sell` 红 `▼`，label 角标 1/2/3）；
  - `markLine`（笔/线段端点连线，未确认用 dashed）；
  - `markArea`（中枢 [ZD,ZG] 半透明矩形）；
  - `highlightDate` → `dataZoom.startValue/endValue` 定位。
- `period==='minute'` 或 week/month 时隐藏缠论图层（由父层不传 structure 实现）。

## `components/strategy/`（新增）

- `SignalBadge`：双周期徽标（绿▲/红▼/灰—/灰「不足」/「已停用」），Tooltip 含信号信息 + 「不构成投资建议」 + 「AI 深度分析」跳转。
- `StructureToggle`：K 线图「缠论」开关（默认开），写入 stockDetailStore。
- `BacktestSummaryTable`：汇总表（period 切换、胜率着色、note 标注），点击单元格 → 明细 Drawer。
- `BacktestDetailDrawer`：明细列表 + 「在 K 线图中查看」→ `navigate('/market/stock/${code}?signalDate=...&period=...')`。
- `RecalcPanel`：策略监控面板（run-status 展示 + 立即重算 + SSE 进度）。

## 页面挂载

- `App.tsx`：加 `<Route path="/strategy" element={<StrategyMonitorPage/>}/>`、`<Route path="/strategy/backtest" element={<BacktestPage/>}/>`。
- `AppLayout.tsx:248-257`：去掉「策略监控」菜单 `disabled`，挂 `/strategy`；回测入口放策略监控页内。
- `WatchlistPage.tsx`：表格加「信号」列（双周期 `SignalBadge`，支持筛选）。
- `StockDetailPage.tsx`：底部 Tabs 加「缠论信号」；解析 `?signalDate=&period=`。
- `StockAnalysisPage.tsx`：挂载 effect 支持 `?code=` 预填（FR-017）。

## 类型与常量（`domain/`）

`types.ts` 追加：`SignalType`、`SignalStatus`、`Period='daily'|'m30'`、`WatchlistSignalItem`、`StructureData`、`BacktestReport/Summary/Detail`、`StrategySSEEvent`。
`constants.ts` 追加：信号徽标颜色映射、窗口 `[5,10,20,60]`、免责声明文案常量。

## DESIGN.md 合规

- 复用 antd `Card size="small"`、`Table`（tabular-nums、斑马纹、固定列）、`Skeleton`/`Empty`/`Alert` 三态。
- 涨跌色沿用 A 股习惯（红涨绿跌）；徽标买绿卖红与 K 线箭头一致。
- 阴影蓝调、紫主色、圆角 4-8px；禁止无结构堆叠。
