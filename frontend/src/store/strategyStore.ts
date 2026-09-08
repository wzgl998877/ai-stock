/**
 * 缠论策略监控状态（T031）。
 *
 * 管理：自选股信号徽标集合 + 重算 SSE 进度（running/total/done/failed/error）。
 * 对标 ``stockDetailStore`` 的 zustand 风格；所有网络经 ``strategyService``。
 */

import { create } from "zustand";
import {
  getRunStatus,
  getWatchlistSignals,
  recalculate,
  updateConfig as apiUpdateConfig,
  type RecalculateParams,
} from "../services/strategyService";
import type {
  ChanlunVersion,
  MonitorConfig,
  RunStatus,
  StrategySSEEvent,
  WatchlistSignalItem,
} from "../domain/types";

interface StrategyState {
  // 缠论算法口径（双版本并存，2026-09-08）：全局切换，徽标/状态/重算均跟随
  version: ChanlunVersion;

  // 徽标
  watchlistSignals: WatchlistSignalItem[];
  signalsLoading: boolean;
  signalsError: string | null;
  disclaimer: string;

  // 重算进度
  recalcRunning: boolean;
  recalcPeriod: string;
  recalcTotal: number;
  recalcDone: number;
  recalcFailed: number;
  recalcSkipped: number;
  recalcError: string | null;

  // 计算任务状态（T052）
  runStatus: RunStatus | null;
  runStatusLoading: boolean;

  setVersion: (version: ChanlunVersion) => void;
  fetchWatchlistSignals: () => Promise<void>;
  recalculate: (params?: RecalculateParams) => Promise<void>;
  stopRecalc: () => void;
  clearRecalc: () => void;
  fetchRunStatus: () => Promise<void>;
  updateConfig: (
    code: string,
    body: { daily_enabled?: boolean; m30_enabled?: boolean },
  ) => Promise<MonitorConfig>;
}

// 模块级 AbortController（store 外保持引用，停止重算用）
let _abortCtrl: AbortController | null = null;

export const useStrategyStore = create<StrategyState>((set, get) => ({
  version: "v2",

  watchlistSignals: [],
  signalsLoading: false,
  signalsError: null,
  disclaimer: "",

  recalcRunning: false,
  recalcPeriod: "",
  recalcTotal: 0,
  recalcDone: 0,
  recalcFailed: 0,
  recalcSkipped: 0,
  recalcError: null,

  runStatus: null,
  runStatusLoading: false,

  setVersion: (version) => {
    if (get().version === version) return;
    set({ version });
    // 口径切换：徽标与计算状态立即按新版本重拉
    get().fetchWatchlistSignals();
    get().fetchRunStatus();
  },

  fetchWatchlistSignals: async () => {
    set({ signalsLoading: true, signalsError: null });
    try {
      const { items, disclaimer } = await getWatchlistSignals(get().version);
      set({ watchlistSignals: items, disclaimer, signalsLoading: false });
    } catch (e: any) {
      set({ signalsError: e?.message || "加载信号失败", signalsLoading: false });
    }
  },

  recalculate: async (params?: RecalculateParams) => {
    if (get().recalcRunning) return; // 防重入
    _abortCtrl = new AbortController();
    set({
      recalcRunning: true,
      recalcError: null,
      recalcPeriod: "",
      recalcTotal: 0,
      recalcDone: 0,
      recalcFailed: 0,
      recalcSkipped: 0,
    });

    const onEvent = (evt: StrategySSEEvent) => {
      switch (evt.event) {
        case "calc_started":
          set({ recalcPeriod: evt.data.period, recalcTotal: evt.data.total, recalcDone: 0, recalcFailed: 0, recalcSkipped: 0 });
          break;
        case "calc_progress": {
          const st = evt.data.status;
          if (st === "done") set((s) => ({ recalcDone: s.recalcDone + 1 }));
          else if (st === "failed") set((s) => ({ recalcFailed: s.recalcFailed + 1 }));
          else if (st === "skipped") set((s) => ({ recalcSkipped: s.recalcSkipped + 1 }));
          break;
        }
        case "calc_completed":
          // 单周期完成：保留累计计数，等待下一周期 calc_started 或流结束
          break;
        case "calc_error":
        case "data_error":
          set({ recalcError: evt.data.message });
          break;
        default:
          break;
      }
    };

    try {
      // 版本跟随全局切换（调用方未显式指定时）
      await recalculate(
        { version: get().version, ...(params || {}) },
        onEvent,
        _abortCtrl.signal,
      );
    } catch (e: any) {
      if (e?.name !== "AbortError") {
        set({ recalcError: e?.message || "重算失败" });
      }
    } finally {
      set({ recalcRunning: false });
      _abortCtrl = null;
      // 完成后刷新徽标与计算状态
      get().fetchWatchlistSignals();
      get().fetchRunStatus();
    }
  },

  stopRecalc: () => {
    if (_abortCtrl) {
      _abortCtrl.abort();
      _abortCtrl = null;
    }
    set({ recalcRunning: false });
  },

  clearRecalc: () => {
    set({
      recalcRunning: false,
      recalcPeriod: "",
      recalcTotal: 0,
      recalcDone: 0,
      recalcFailed: 0,
      recalcSkipped: 0,
      recalcError: null,
    });
  },

  fetchRunStatus: async () => {
    set({ runStatusLoading: true });
    try {
      const status = await getRunStatus(get().version);
      set({ runStatus: status, runStatusLoading: false });
    } catch {
      set({ runStatusLoading: false });
    }
  },

  updateConfig: async (code, body) => {
    const saved = await apiUpdateConfig(code, body);
    // 配置变更影响徽标状态（disabled/monitored），刷新徽标
    get().fetchWatchlistSignals();
    return saved;
  },
}));
