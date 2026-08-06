/**
 * 缠论信号徽标（T032）。
 *
 * 双周期展示：买点绿色 ▲ / 卖点红色 ▼，角标 1/2/3 表示类别；
 * 无信号灰「-」、数据不足「不足」、已停用「停用」。
 * Tooltip 含信号详情 + 免责声明（FR-016）+「AI 深度分析」入口（FR-017）。
 */

import React from "react";
import { Tooltip, Tag } from "antd";
import {
  SIGNAL_BADGE_COLORS,
  SIGNAL_STATUS_LABELS,
  SIGNAL_TYPE_LABELS,
  STRATEGY_DISCLAIMER,
  isBuySignal,
  signalLevel,
} from "../../domain/constants";
import type { SignalStatus, SignalSummary } from "../../domain/types";

interface SignalBadgeProps {
  stockCode: string;
  stockName?: string;
  daily?: SignalSummary | null;
  dailyStatus?: SignalStatus;
  m30?: SignalSummary | null;
  m30Status?: SignalStatus;
  onAnalyze?: (code: string) => void;
}

const PERIOD_LABEL: Record<string, string> = { daily: "日", m30: "30m" };

function fmtTime(t: string | null): string {
  if (!t) return "—";
  return t.replace("T", " ").slice(0, 16);
}

/** 单周期徽标内容 */
function badgeInner(summary: SignalSummary | null | undefined, status: SignalStatus): React.ReactNode {
  if (status === "disabled") return <span style={{ color: "#bbb", fontSize: 12 }}>停用</span>;
  if (status === "insufficient_data") return <span style={{ color: "#bbb", fontSize: 12 }}>不足</span>;
  if (!summary || !summary.signal_type) return <span style={{ color: "#d9d9d9" }}>—</span>;
  const t = summary.signal_type;
  const color = SIGNAL_BADGE_COLORS[t];
  const arrow = isBuySignal(t) ? "▲" : "▼";
  return (
    <span style={{ color, fontWeight: 600 }}>
      {arrow}
      <sup style={{ fontSize: 10, marginLeft: 1 }}>{signalLevel(t)}</sup>
    </span>
  );
}

/** Tooltip 详情 */
function tooltipContent(
  period: string,
  summary: SignalSummary | null | undefined,
  status: SignalStatus,
  stockCode: string,
  onAnalyze?: (code: string) => void,
): React.ReactNode {
  const hasSignal = status === "monitored" && summary?.signal_type;
  return (
    <div style={{ maxWidth: 240 }}>
      <div style={{ fontWeight: 600, marginBottom: 4 }}>
        {PERIOD_LABEL[period] || period}线 · {SIGNAL_STATUS_LABELS[status]}
      </div>
      {hasSignal && (
        <div style={{ fontSize: 12, lineHeight: 1.6 }}>
          <div>类型：{SIGNAL_TYPE_LABELS[summary!.signal_type!]}</div>
          <div>时间：{fmtTime(summary!.signal_time)}</div>
          {summary!.trigger_price != null && <div>触发价：{summary!.trigger_price}</div>}
        </div>
      )}
      <div style={{ fontSize: 11, color: "#999", marginTop: 6 }}>{STRATEGY_DISCLAIMER}</div>
      {onAnalyze && (
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

export const SignalBadge: React.FC<SignalBadgeProps> = ({
  stockCode,
  daily,
  dailyStatus = "monitored_nodata",
  m30,
  m30Status = "monitored_nodata",
  onAnalyze,
}) => {
  const periods: Array<["daily" | "m30", SignalSummary | null | undefined, SignalStatus]> = [
    ["daily", daily, dailyStatus],
    ["m30", m30, m30Status],
  ];
  return (
    <span style={{ display: "inline-flex", gap: 6, alignItems: "center" }}>
      {periods.map(([p, summary, status]) => (
        <Tooltip
          key={p}
          title={tooltipContent(p, summary, status, stockCode, onAnalyze)}
          overlayStyle={{ maxWidth: 260 }}
        >
          <Tag
            style={{
              margin: 0,
              padding: "0 6px",
              lineHeight: "20px",
              fontSize: 13,
              background: "#fafafa",
              border: "1px solid #f0f0f0",
              cursor: "default",
            }}
          >
            <span style={{ color: "#999", fontSize: 11, marginRight: 3 }}>{PERIOD_LABEL[p]}</span>
            {badgeInner(summary, status)}
          </Tag>
        </Tooltip>
      ))}
    </span>
  );
};

export default SignalBadge;
