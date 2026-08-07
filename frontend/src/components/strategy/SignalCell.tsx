/**
 * 缠论信号单元格（单周期展示，替代旧的双周期 SignalBadge）。
 *
 * 展示约定：
 * - 买点绿色 ▲、卖点红色 ▼ + 类别文案（一类买点/二类卖点…）+ 信号时间；
 * - 历史信号（is_fresh=false，超出新鲜度窗口）整体置灰并加「历史」前缀；
 * - 无信号灰「—」、数据不足「不足」、已停用「停用」；
 * - Tooltip 含信号详情 + 免责声明（FR-016）+「AI 深度分析」入口（FR-017）。
 */

import React from "react";
import { Tooltip } from "antd";
import {
  SIGNAL_BADGE_COLORS,
  SIGNAL_STATUS_LABELS,
  SIGNAL_TYPE_LABELS,
  STRATEGY_DISCLAIMER,
  isBuySignal,
} from "../../domain/constants";
import type { ChanlunPeriod, SignalStatus, SignalSummary } from "../../domain/types";

export const PERIOD_LABEL: Record<ChanlunPeriod, string> = { daily: "日 K", m30: "30m" };

/** "2026-08-05T15:00:00" → "08-05 15:00"（表格紧凑展示） */
export function fmtSignalTime(t: string | null): string {
  if (!t) return "—";
  const s = t.replace("T", " ");
  // 优先取 MM-DD HH:mm；年份不同的信号保留年份前缀
  const year = new Date().getFullYear();
  if (s.startsWith(String(year))) return s.slice(5, 16);
  return s.slice(0, 16);
}

export interface SignalCellProps {
  period: ChanlunPeriod;
  summary?: SignalSummary | null;
  status?: SignalStatus;
  stockCode?: string;
  onAnalyze?: (code: string) => void;
}

const muted: React.CSSProperties = { color: "#bbb", fontSize: 12 };

/** Tooltip 详情 */
function tooltipContent(
  period: ChanlunPeriod,
  summary: SignalSummary | null | undefined,
  status: SignalStatus,
  stockCode?: string,
  onAnalyze?: (code: string) => void,
): React.ReactNode {
  const hasSignal = !!summary?.signal_type;
  const historical = hasSignal && summary!.is_fresh === false;
  return (
    <div style={{ maxWidth: 240 }}>
      <div style={{ fontWeight: 600, marginBottom: 4 }}>
        {PERIOD_LABEL[period]} · {SIGNAL_STATUS_LABELS[status]}
        {historical ? "（历史信号）" : ""}
      </div>
      {hasSignal && (
        <div style={{ fontSize: 12, lineHeight: 1.6 }}>
          <div>类型：{SIGNAL_TYPE_LABELS[summary!.signal_type!]}</div>
          <div>时间：{summary!.signal_time?.replace("T", " ").slice(0, 16) ?? "—"}</div>
          {summary!.trigger_price != null && <div>触发价：{summary!.trigger_price}</div>}
        </div>
      )}
      <div style={{ fontSize: 11, color: "#999", marginTop: 6 }}>{STRATEGY_DISCLAIMER}</div>
      {onAnalyze && stockCode && (
        <a
          style={{ display: "inline-block", marginTop: 6, fontSize: 12 }}
          onClick={(e) => {
            e.preventDefault();
            onAnalyze(stockCode);
          }}
        >
          AI 深度分析 →
        </a>
      )}
    </div>
  );
}

export const SignalCell: React.FC<SignalCellProps> = ({
  period,
  summary,
  status = "monitored_nodata",
  stockCode,
  onAnalyze,
}) => {
  let body: React.ReactNode;
  if (status === "disabled") {
    body = <span style={muted}>停用</span>;
  } else if (status === "insufficient_data") {
    body = <span style={muted}>不足</span>;
  } else if (!summary || !summary.signal_type) {
    body = <span style={{ color: "#d9d9d9" }}>—</span>;
  } else {
    const t = summary.signal_type;
    const historical = summary.is_fresh === false;
    const color = historical ? "#bfbfbf" : SIGNAL_BADGE_COLORS[t];
    const arrow = isBuySignal(t) ? "▲" : "▼";
    body = (
      <div style={{ lineHeight: 1.3 }}>
        <span style={{ color, fontWeight: 600, fontSize: 13 }}>
          {historical && <span style={{ fontWeight: 400, marginRight: 2 }}>历史</span>}
          {arrow} {SIGNAL_TYPE_LABELS[t]}
        </span>
        <div style={{ color: "#999", fontSize: 11, fontVariantNumeric: "tabular-nums" }}>
          {fmtSignalTime(summary.signal_time)}
        </div>
      </div>
    );
  }

  return (
    <Tooltip
      title={tooltipContent(period, summary, status, stockCode, onAnalyze)}
      overlayStyle={{ maxWidth: 260 }}
    >
      <span style={{ display: "inline-block", cursor: "default", textAlign: "center" }}>{body}</span>
    </Tooltip>
  );
};

export default SignalCell;
