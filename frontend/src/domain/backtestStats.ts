/**
 * 回测明细统计聚合（纯函数，T048 详情页页面化）。
 *
 * 口径与后端汇总（``chanlun_backtest._aggregate``）对齐：
 * - 粒度为**信号笔数**（同一股票可多笔信号）；
 * - 明细 ``ret_*`` 是真实涨跌，此处按**信号视角**统一：买点原值、卖点取反
 *   （跌 = 卖对 = 赢），使盈亏统计与汇总表胜率一致；
 * - ``win_rate`` 分母含 0 收益样本（平局不算赢），与后端 ``wins/sc`` 一致。
 */

import type { BacktestSignalDetailItem, BacktestWindow } from "./types";
import { isBuySignal } from "./constants";

/** 单条明细在指定窗口的信号视角收益（买=真实涨跌，卖=取反）；越界/缺失返回 null */
export function signalViewReturn(
  item: BacktestSignalDetailItem,
  window: BacktestWindow,
): number | null {
  const raw = item[`ret_${window}`] as number | null;
  if (raw == null || !Number.isFinite(raw)) return null;
  return isBuySignal(item.signal_type) ? raw : -raw;
}

export interface WinLossStats {
  /** 该窗口有有效收益的样本数（与 summary.sample 对齐） */
  total: number;
  /** 信号视角收益 > 0 的笔数 */
  win: number;
  /** 信号视角收益 < 0 的笔数 */
  loss: number;
  /** 恰好为 0 的笔数（分母内、不算赢） */
  flat: number;
  /** 涉及股票只数（按有效样本去重） */
  stockCount: number;
  /** 胜率 0-1（无样本为 null，与后端一致） */
  winRate: number | null;
}

/** 盈亏笔数统计：只统计该窗口收益非空的样本（近期信号未来窗越界已剔除） */
export function winLossStats(
  items: BacktestSignalDetailItem[],
  window: BacktestWindow,
): WinLossStats {
  let win = 0;
  let loss = 0;
  let flat = 0;
  const stocks = new Set<string>();
  for (const it of items) {
    const v = signalViewReturn(it, window);
    if (v == null) continue;
    stocks.add(it.stock_code);
    if (v > 0) win += 1;
    else if (v < 0) loss += 1;
    else flat += 1;
  }
  const total = win + loss + flat;
  return {
    total,
    win,
    loss,
    flat,
    stockCount: stocks.size,
    winRate: total > 0 ? win / total : null,
  };
}

/** 收益分档（信号视角）：边界为左闭右开 [min, max)，首尾档开放 */
export interface ReturnTierDef {
  label: string;
  min: number | null;
  max: number | null;
}

export const RETURN_TIERS: ReturnTierDef[] = [
  { label: "≥ +20%", min: 0.2, max: null },
  { label: "+10% ~ +20%", min: 0.1, max: 0.2 },
  { label: "0 ~ +10%", min: 0, max: 0.1 },
  { label: "-10% ~ 0", min: -0.1, max: 0 },
  { label: "-20% ~ -10%", min: -0.2, max: -0.1 },
  { label: "< -20%", min: null, max: -0.2 },
];

export interface ReturnTierStat {
  label: string;
  count: number;
  /** 占有效样本比例 0-1（无样本为 null） */
  pct: number | null;
  /** 是否盈利侧（用于红/绿着色，A 股习惯红盈绿亏） */
  positive: boolean;
}

/** 分档统计：returns 需先转信号视角；count=0 档 pct 为 0（分母无样本时 null） */
export function tierDistribution(returns: number[]): {
  tiers: ReturnTierStat[];
  /** 最大档计数（比例条宽度归一化用）；无样本为 0 */
  maxCount: number;
} {
  const vals = returns.filter((v) => v != null && Number.isFinite(v));
  const total = vals.length;
  const tiers = RETURN_TIERS.map((t) => {
    const count = vals.filter((v) => {
      const geMin = t.min == null || v >= t.min;
      const ltMax = t.max == null || v < t.max;
      return geMin && ltMax;
    }).length;
    return {
      label: t.label,
      count,
      pct: total > 0 ? count / total : null,
      positive: t.min == null || t.min >= 0,
    };
  });
  return { tiers, maxCount: tiers.reduce((m, t) => Math.max(m, t.count), 0) };
}

/** 明细筛选条件（信号视角） */
export type DetailFilter = "all" | "win" | "loss";

/** 按信号视角收益过滤明细（all 原样返回；win>0 / loss<0） */
export function filterByView(
  items: BacktestSignalDetailItem[],
  window: BacktestWindow,
  filter: DetailFilter,
): BacktestSignalDetailItem[] {
  if (filter === "all") return items;
  return items.filter((it) => {
    const v = signalViewReturn(it, window);
    if (v == null) return false;
    return filter === "win" ? v > 0 : v < 0;
  });
}
