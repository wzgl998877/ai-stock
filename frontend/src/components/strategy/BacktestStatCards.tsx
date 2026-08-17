/**
 * 回测详情盈亏概览统计卡（纯 UI，T048 页面化）。
 *
 * 六卡：总样本（含涉及股票数）/ 盈利笔数 / 亏损笔数 / 盈亏比 / 平均收益 / 中位收益。
 * 盈亏比与均值/中位来自后端 summary（与汇总表同源）；盈亏笔数由明细统计
 * （``domain/backtestStats``，信号视角）。A 股习惯：红=盈/信号对，绿=亏/信号错。
 */

import React from "react";
import { Col, Row, Skeleton } from "antd";
import type { BacktestSummaryCell } from "../../domain/types";
import type { WinLossStats } from "../../domain/backtestStats";

const RED = "#ea2261";
const GREEN = "#16c79a";
const NAVY = "#061b31";
const MUTED = "#64748d";

interface CardItem {
  label: string;
  value: string;
  color: string;
  sub?: string;
}

interface BacktestStatCardsProps {
  stats: WinLossStats;
  /** 当前 (period, signal_type, window) 的汇总格（盈亏比/均值/中位来源） */
  cell?: BacktestSummaryCell;
  loading?: boolean;
}

function pct(n: number, total: number): string {
  return total > 0 ? `${((n / total) * 100).toFixed(1)}%` : "—";
}

function retColor(v: number | null | undefined): string {
  if (v == null) return MUTED;
  return v > 0 ? RED : v < 0 ? GREEN : NAVY;
}

function fmtRet(v: number | null | undefined): string {
  if (v == null) return "—";
  const s = (v * 100).toFixed(2);
  return `${v > 0 ? "+" : ""}${s}%`;
}

export const BacktestStatCards: React.FC<BacktestStatCardsProps> = ({
  stats,
  cell,
  loading = false,
}) => {
  if (loading) return <Skeleton active paragraph={{ rows: 2 }} />;

  const plr = cell?.profit_loss_ratio;
  const plrSub =
    plr == null
      ? stats.loss > 0 ? "暂无数据" : "无亏损样本"
      : plr >= 1 ? "平均盈利 > 平均亏损" : "平均盈利 < 平均亏损";

  const items: CardItem[] = [
    {
      label: "总样本",
      value: `${stats.total.toLocaleString()} 笔`,
      color: NAVY,
      sub: `涉及 ${stats.stockCount} 只股票`,
    },
    {
      label: "盈利",
      value: `${stats.win.toLocaleString()} 笔`,
      color: stats.win > 0 ? RED : MUTED,
      sub: `占 ${pct(stats.win, stats.total)}`,
    },
    {
      label: "亏损",
      value: `${stats.loss.toLocaleString()} 笔`,
      color: stats.loss > 0 ? GREEN : MUTED,
      sub: `占 ${pct(stats.loss, stats.total)}`,
    },
    {
      label: "盈亏比",
      value: plr != null ? plr.toFixed(2) : "—",
      color: plr == null ? MUTED : plr >= 1 ? RED : GREEN,
      sub: plrSub,
    },
    {
      label: "平均收益",
      value: fmtRet(cell?.avg_return),
      color: retColor(cell?.avg_return),
    },
    {
      label: "中位收益",
      value: fmtRet(cell?.median_return),
      color: retColor(cell?.median_return),
    },
  ];

  return (
    <Row gutter={[12, 16]}>
      {items.map((it) => (
        <Col key={it.label} xs={12} sm={8} lg={4}>
          <div
            style={{
              padding: "12px 14px",
              border: "1px solid #e5edf5",
              borderRadius: 6,
              background: "#fafbfc",
            }}
          >
            <div style={{ fontSize: 12, color: MUTED, marginBottom: 4 }}>{it.label}</div>
            <div
              style={{
                fontSize: 20,
                fontWeight: 600,
                color: it.color,
                fontVariantNumeric: "tabular-nums",
                lineHeight: 1.3,
              }}
            >
              {it.value}
            </div>
            {it.sub && (
              <div style={{ fontSize: 11, color: MUTED, marginTop: 2, fontVariantNumeric: "tabular-nums" }}>
                {it.sub}
              </div>
            )}
          </div>
        </Col>
      ))}
    </Row>
  );
};

export default BacktestStatCards;
