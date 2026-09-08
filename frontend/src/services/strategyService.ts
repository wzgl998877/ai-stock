/**
 * 缠论策略监控 API Service（模块三，T030）。
 *
 * 所有 HTTP 经 ``api``（axios 实例 + 鉴权拦截器）；SSE 经 ``sse.ts``（fetch+ReadableStream）。
 * 页面/组件不直连网络，统一走本 service（宪章前端分层）。
 *
 * 后端端点：``/api/v1/strategy``（见 ``backend/app/routers/chanlun.py``）。
 */

import api from "./api";
import { streamSSE } from "./sse";
import type {
  BacktestRange,
  BacktestReportDetail,
  BacktestReportListItem,
  BacktestSignalDetailItem,
  ChanlunPeriod,
  ChanlunVersion,
  MonitorConfig,
  RunStatus,
  SignalHistoryItem,
  SignalStatus,
  SignalSummary,
  SignalMark,
  StrategySSEEvent,
  StructureData,
  WatchlistSignalItem,
} from "../domain/types";

const BASE = "/api/v1/strategy";
const BACKTEST_BASE = "/api/v1/backtest";

/** 后端返回的徽标项（含 status 字段，T050 起后端配置感知） */
interface RawWatchlistSignalItem {
  stock_code: string;
  stock_name: string;
  daily: SignalSummary | null;
  m30: SignalSummary | null;
  daily_status?: SignalStatus;
  m30_status?: SignalStatus;
}

/** 后端未返回 status 时的兜底推断（有信号→monitored，无信号→monitored_nodata） */
function inferStatus(summary: SignalSummary | null): SignalStatus {
  return summary && summary.signal_type ? "monitored" : "monitored_nodata";
}

/** 自选股双周期信号徽标（GET /watchlist-signals） */
export async function getWatchlistSignals(version?: ChanlunVersion): Promise<{
  items: WatchlistSignalItem[];
  disclaimer: string;
}> {
  const res = await api.get(`${BASE}/watchlist-signals`, {
    params: version ? { version } : undefined,
  });
  const raw = res.data as { items: RawWatchlistSignalItem[]; disclaimer?: string };
  return {
    items: (raw.items || []).map((it) => ({
      stock_code: it.stock_code,
      stock_name: it.stock_name,
      daily: it.daily,
      m30: it.m30,
      daily_status: it.daily_status ?? inferStatus(it.daily),
      m30_status: it.m30_status ?? inferStatus(it.m30),
    })),
    disclaimer: raw.disclaimer || "",
  };
}

/** 单股信号历史（GET /stocks/{code}/signals） */
export async function getSignals(
  code: string,
  params?: { period?: ChanlunPeriod; status?: "confirmed" | "invalidated"; limit?: number; version?: ChanlunVersion },
): Promise<{
  items: SignalHistoryItem[];
  total: number;
  disclaimer: string;
}> {
  const res = await api.get(`${BASE}/stocks/${code}/signals`, {
    params: {
      period: params?.period || "daily",
      status: params?.status,
      limit: params?.limit || 50,
      version: params?.version,
    },
  });
  return {
    items: res.data.items || [],
    total: res.data.total || 0,
    disclaimer: res.data.disclaimer || "",
  };
}

export interface RecalculateParams {
  stock_codes?: string[] | null;   // null/undefined = 用户全部自选股
  period?: ChanlunPeriod | "both";
  version?: ChanlunVersion;        // 缠论算法口径；缺省用服务端默认版
}

/** 单股缠论结构快照（GET /stocks/{code}/structure） */
export async function getStructure(code: string, period: ChanlunPeriod, version?: ChanlunVersion): Promise<{
  structure: StructureData;
  signalMarks: SignalMark[];
  disclaimer: string;
}> {
  const res = await api.get(`${BASE}/stocks/${code}/structure`, {
    params: version ? { period, version } : { period },
  });
  const d = res.data || {};
  const toPoint = (f: any) => ({ time: String(f.time), price: Number(f.price) });
  return {
    structure: {
      strokes: (d.strokes || []).map((s: any) => ({
        start: toPoint(s.start), end: toPoint(s.end),
        direction: s.direction, confirmed: !!s.confirmed,
      })),
      segments: (d.segments || []).map((s: any) => ({
        start: toPoint(s.start), end: toPoint(s.end),
        direction: s.direction, confirmed: !!s.confirmed,
      })),
      zhongshu: (d.zhongshu || []).map((z: any) => ({
        zd: Number(z.zd), zg: Number(z.zg), dd: Number(z.dd), gg: Number(z.gg),
        enter_time: String(z.enter_time), exit_time: z.exit_time ? String(z.exit_time) : null,
      })),
      last_kline_time: d.last_kline_time || "",
      algo_version: d.algo_version || "",
    },
    signalMarks: (d.signal_marks || []).map((m: any) => ({
      signal_type: m.signal_type,
      time: String(m.time),
      price: m.price != null ? Number(m.price) : 0,
      confirmed_at: m.confirmed_at ? String(m.confirmed_at) : String(m.time),
      level: m.level,
    })),
    disclaimer: d.disclaimer || "",
  };
}

/**
 * 触发重算并订阅 SSE 进度（POST /recalculate）。
 *
 * @param onEvent 收到强类型 ``StrategySSEEvent``（calc_started/progress/completed/error/data_error）
 * @param signal  AbortSignal，调用方可停止重算（前端流终止，后端任务继续跑完）
 */
export async function recalculate(
  params: RecalculateParams,
  onEvent: (evt: StrategySSEEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  await streamSSE({
    url: `${BASE}/recalculate`,
    method: "POST",
    body: {
      stock_codes: params.stock_codes ?? null,
      period: params.period || "daily",
      version: params.version ?? null,
    },
    signal,
    onEvent: (msg) => {
      // 后端 event 名已对齐 StrategySSEEvent 联合类型；心跳 heartbeat 忽略
      if (msg.event === "heartbeat") return;
      onEvent({ event: msg.event, data: msg.data } as StrategySSEEvent);
    },
  });
}

// ---------------------------------------------------------------------------
// 回测（T045）
// ---------------------------------------------------------------------------

export interface BacktestParams {
  range: BacktestRange;
  periods?: ChanlunPeriod[];
  stock_codes?: string[] | null;   // null/undefined = 用户全部自选股
  version?: ChanlunVersion;        // 缠论算法口径；缺省用服务端默认版
}

/** 发起回测并订阅 SSE 进度（POST /backtest/run）；完成后 ``backtest_completed`` 带 report_id */
export async function runBacktest(
  params: BacktestParams,
  onEvent: (evt: StrategySSEEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  await streamSSE({
    url: `${BACKTEST_BASE}/run`,
    method: "POST",
    body: {
      range: params.range,
      periods: params.periods || ["daily"],
      stock_codes: params.stock_codes ?? null,
      version: params.version ?? null,
    },
    signal,
    onEvent: (msg) => {
      if (msg.event === "heartbeat") return;
      onEvent({ event: msg.event, data: msg.data } as StrategySSEEvent);
    },
  });
}

/** 回测报告列表（GET /backtest/reports） */
export async function getReports(
  params?: { page?: number; page_size?: number },
): Promise<{ items: BacktestReportListItem[]; total: number; disclaimer: string }> {
  const res = await api.get(`${BACKTEST_BASE}/reports`, {
    params: { page: params?.page || 1, page_size: params?.page_size || 10 },
  });
  return {
    items: res.data.items || [],
    total: res.data.total || 0,
    disclaimer: res.data.disclaimer || "",
  };
}

/** 报告详情：meta + 汇总表（GET /backtest/reports/{id}） */
export async function getReport(id: number): Promise<BacktestReportDetail> {
  const res = await api.get(`${BACKTEST_BASE}/reports/${id}`);
  return res.data as BacktestReportDetail;
}

/** 报告明细下钻（GET /backtest/reports/{id}/details） */
export async function getReportDetails(
  id: number,
  params?: {
    period?: ChanlunPeriod;
    signal_type?: string;
    window?: number;
    stock_code?: string;
    page?: number;
    page_size?: number;
  },
): Promise<{ items: BacktestSignalDetailItem[]; total: number; disclaimer: string }> {
  const res = await api.get(`${BACKTEST_BASE}/reports/${id}/details`, { params });
  return {
    items: res.data.items || [],
    total: res.data.total || 0,
    disclaimer: res.data.disclaimer || "",
  };
}

// ---------------------------------------------------------------------------
// 监控配置与计算状态（T050/T052）
// ---------------------------------------------------------------------------

/** 更新逐股监控开关（PUT /stocks/{code}/config） */
export async function updateConfig(
  code: string,
  body: { daily_enabled?: boolean; m30_enabled?: boolean },
): Promise<MonitorConfig> {
  const res = await api.put(`${BASE}/stocks/${code}/config`, body);
  return res.data as MonitorConfig;
}

/** 计算任务状态（GET /run-status）—— 日线 / 30m 最近一次运行 */
export async function getRunStatus(version?: ChanlunVersion): Promise<RunStatus> {
  const res = await api.get(`${BASE}/run-status`, {
    params: version ? { version } : undefined,
  });
  return res.data as RunStatus;
}
