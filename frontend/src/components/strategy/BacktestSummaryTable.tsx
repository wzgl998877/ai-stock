/**
 * 回测汇总表（T047）。
 *
 * 矩阵：行=信号类型（一/二/三类买卖），列=观察窗口（5/10/20/60 日），单元格=胜率。
 * 胜率 >50% 绿 / <50% 红；样本 <10 标「样本不足」；点击单元格打开明细 Drawer。
 * 表头挂基准涨跌 + 三条免责声明（FR-016）。数字 tabular-nums（DESIGN.md）。
 */

import React, { useMemo, useState } from "react";
import { Table, Segmented, Typography, Alert } from "antd";
import {
  BACKTEST_DISCLAIMER,
  SIGNAL_TYPE_LABELS,
} from "../../domain/constants";
import type {
  BacktestSummaryCell,
  BacktestWindow,
  ChanlunPeriod,
  SignalType,
} from "../../domain/types";

const { Text } = Typography;

const PERIOD_OPTS = [
  { label: "日 K", value: "daily" as ChanlunPeriod },
  { label: "30 分钟", value: "m30" as ChanlunPeriod },
];

const SIGNAL_ROWS: SignalType[] = ["buy1", "buy2", "buy3", "sell1", "sell2", "sell3"];
const WINDOW_COLS: BacktestWindow[] = [5, 10, 20, 60];

interface BacktestSummaryTableProps {
  summary: BacktestSummaryCell[];
  loading?: boolean;
  benchmarkReturn: number | null;
  onCellClick: (period: ChanlunPeriod, signalType: SignalType, window: BacktestWindow) => void;
}

function winColor(wr: number | null | undefined): string {
  if (wr == null) return "#8c8c8c";
  if (wr > 0.5) return "#16c79a";
  if (wr < 0.5) return "#ea2261";
  return "#8c8c8c";
}

export const BacktestSummaryTable: React.FC<BacktestSummaryTableProps> = ({
  summary,
  loading = false,
  benchmarkReturn,
  onCellClick,
}) => {
  const [period, setPeriod] = useState<ChanlunPeriod>("daily");

  const cellMap = useMemo(() => {
    const m = new Map<string, BacktestSummaryCell>();
    for (const c of summary) m.set(`${c.period}|${c.signal_type}|${c.window}`, c);
    return m;
  }, [summary]);

  const columns = [
    {
      title: "信号类型",
      dataIndex: "st",
      fixed: "left" as const,
      width: 110,
      render: (t: SignalType) => (
        <span style={{ fontVariantNumeric: "tabular-nums" }}>{SIGNAL_TYPE_LABELS[t]}</span>
      ),
    },
    ...WINDOW_COLS.map((w) => ({
      title: `${w} 日`,
      key: String(w),
      align: "center" as const,
      width: 112,
      render: (_: unknown, row: { st: SignalType }) => {
        const c = cellMap.get(`${period}|${row.st}|${w}`);
        if (!c) {
          return <span style={{ color: "#d9d9d9" }}>—</span>;
        }
        const wr = c.win_rate;
        const insufficient = c.note === "sample_insufficient";
        return (
          <a
            onClick={() => onCellClick(period, row.st, w)}
            style={{ display: "block", fontVariantNumeric: "tabular-nums" }}
          >
            <span style={{ color: winColor(wr), fontWeight: 600, fontSize: 14 }}>
              {wr != null ? `${(wr * 100).toFixed(0)}%` : "—"}
            </span>
            <div style={{ fontSize: 11, color: "#999" }}>
              {c.sample} 样本{insufficient ? " · 不足" : ""}
            </div>
          </a>
        );
      },
    })),
  ];

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
        <Segmented options={PERIOD_OPTS} value={period} onChange={(v) => setPeriod(v as ChanlunPeriod)} />
        <Text type="secondary" style={{ fontSize: 12, fontVariantNumeric: "tabular-nums" }}>
          同期基准（沪深300）：
          {benchmarkReturn != null ? `${(benchmarkReturn * 100).toFixed(2)}%` : "暂无"}
        </Text>
      </div>
      <Table
        size="small"
        rowKey="st"
        dataSource={SIGNAL_ROWS.map((s) => ({ st: s, key: s }))}
        columns={columns as any}
        pagination={false}
        loading={loading}
        scroll={{ x: "max-content" }}
      />
      <Alert style={{ marginTop: 12 }} type="warning" message={BACKTEST_DISCLAIMER} banner />
    </div>
  );
};

export default BacktestSummaryTable;
