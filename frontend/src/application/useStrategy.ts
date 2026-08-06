/**
 * 缠论策略编排 hook（T036）。
 *
 * 薄封装 ``strategyStore``：聚合重算进度字段、计算百分比，向组件暴露
 * ``start/stop/progress`` 等易用 API。完成后徽标刷新由 store 内部保证。
 */

import { useStrategyStore } from "../store/strategyStore";
import type { RecalculateParams } from "../services/strategyService";

export interface UseStrategy {
  running: boolean;
  period: string;
  total: number;
  done: number;
  failed: number;
  skipped: number;
  /** 进度百分比 0-100（total=0 时为 0） */
  progress: number;
  error: string | null;
  start: (params?: RecalculateParams) => Promise<void>;
  stop: () => void;
}

export function useStrategy(): UseStrategy {
  const s = useStrategyStore();
  const progress = s.recalcTotal > 0 ? Math.round((s.recalcDone / s.recalcTotal) * 100) : 0;
  return {
    running: s.recalcRunning,
    period: s.recalcPeriod,
    total: s.recalcTotal,
    done: s.recalcDone,
    failed: s.recalcFailed,
    skipped: s.recalcSkipped,
    progress,
    error: s.recalcError,
    start: s.recalculate,
    stop: s.stopRecalc,
  };
}
