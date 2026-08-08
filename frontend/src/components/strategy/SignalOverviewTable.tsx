/**
 * 信号总览表（策略监控页）：自选股 × 双周期信号一览 + 筛选。
 *
 * 筛选维度：时间范围（今日/近三日/近七日/自定义区间）、信号方向（买点/卖点）、周期。
 * 复用 ``SignalCell``（置灰=历史信号）；无数据/无命中展示空态（DESIGN.md 约束）。
 *
 * 筛选语义：任一条件非「全部」即视为筛选激活——仅保留至少一个周期命中的股票，
 * 未命中的单元格显示占位「—」。
 */

import React, { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { DatePicker, Select, Table, Typography } from "antd";
import type { ColumnsType } from "antd/es/table";
import dayjs, { Dayjs } from "dayjs";
import SignalCell from "./SignalCell";
import type { ChanlunPeriod, SignalSummary, WatchlistSignalItem } from "../../domain/types";

const { Text } = Typography;
const { RangePicker } = DatePicker;

// ---------------------------------------------------------------------------
// 筛选逻辑（纯函数，导出供单测）
// ---------------------------------------------------------------------------

export type RangeKey = "all" | "today" | "3d" | "7d" | "custom";

export interface OverviewFilter {
  rangeKey: RangeKey;
  customRange: [Dayjs | null, Dayjs | null] | null;
  direction: "all" | "buy" | "sell";
  period: "all" | ChanlunPeriod;
}

export const DEFAULT_FILTER: OverviewFilter = {
  rangeKey: "all",
  customRange: null,
  direction: "all",
  period: "all",
};

export function isFilterActive(f: OverviewFilter): boolean {
  return f.rangeKey !== "all" || f.direction !== "all" || f.period !== "all";
}

/** 时间边界（日期粒度：起始日 00:00:00 ~ 结束日 23:59:59）；无时间约束返回 null */
export function rangeBounds(f: OverviewFilter): { start: Dayjs; end: Dayjs } | null {
  const today = dayjs();
  if (f.rangeKey === "today") return { start: today.startOf("day"), end: today.endOf("day") };
  if (f.rangeKey === "3d") return { start: today.subtract(2, "day").startOf("day"), end: today.endOf("day") };
  if (f.rangeKey === "7d") return { start: today.subtract(6, "day").startOf("day"), end: today.endOf("day") };
  if (f.rangeKey === "custom") {
    const [s, e] = f.customRange ?? [null, null];
    if (!s || !e) return null; // 自定义区间未选全 → 不加时间约束
    return { start: s.startOf("day"), end: e.endOf("day") };
  }
  return null;
}

/** 单格信号是否命中筛选条件（无信号视为不命中） */
export function matchesSummary(
  summary: SignalSummary | null | undefined,
  f: OverviewFilter,
  cellPeriod: ChanlunPeriod,
): boolean {
  if (!summary || !summary.signal_type) return false;
  if (f.period !== "all" && cellPeriod !== f.period) return false;
  if (f.direction !== "all" && !summary.signal_type.startsWith(f.direction)) return false;
  const b = rangeBounds(f);
  if (b) {
    const t = dayjs(summary.signal_time ?? undefined);
    if (!t.isValid() || t.isBefore(b.start) || t.isAfter(b.end)) return false;
  }
  return true;
}

// ---------------------------------------------------------------------------
// 组件
// ---------------------------------------------------------------------------

interface SignalOverviewTableProps {
  items: WatchlistSignalItem[];
  loading?: boolean;
  onAnalyze?: (code: string) => void;
}

/** 未命中筛选的单元格占位 */
const MissedCell: React.FC = () => <span style={{ color: "#e8e8e8" }}>—</span>;

export const SignalOverviewTable: React.FC<SignalOverviewTableProps> = ({
  items,
  loading = false,
  onAnalyze,
}) => {
  const navigate = useNavigate();
  const [filter, setFilter] = useState<OverviewFilter>(DEFAULT_FILTER);

  const active = isFilterActive(filter);

  // 行级过滤：筛选激活时仅保留至少一格命中的股票
  const visibleItems = useMemo(() => {
    if (!active) return items;
    return items.filter(
      (it) => matchesSummary(it.daily, filter, "daily") || matchesSummary(it.m30, filter, "m30"),
    );
  }, [items, filter, active]);

  const columns: ColumnsType<WatchlistSignalItem> = [
    {
      title: "代码",
      dataIndex: "stock_code",
      key: "stock_code",
      width: 96,
      align: "center",
      render: (code: string) => (
        <a
          style={{ color: "#533afd", textDecoration: "none", cursor: "pointer" }}
          onClick={() => navigate(`/market/stock/${code}`)}
        >
          {code}
        </a>
      ),
    },
    {
      title: "名称",
      dataIndex: "stock_name",
      key: "stock_name",
      width: 120,
      align: "center",
    },
    {
      title: "日K信号",
      key: "daily",
      width: 140,
      align: "center",
      render: (_: unknown, r: WatchlistSignalItem) =>
        active && !matchesSummary(r.daily, filter, "daily") ? (
          <MissedCell />
        ) : (
          <SignalCell
            period="daily"
            summary={r.daily}
            status={r.daily_status}
            stockCode={r.stock_code}
            onAnalyze={onAnalyze}
          />
        ),
    },
    {
      title: "30分钟信号",
      key: "m30",
      width: 140,
      align: "center",
      render: (_: unknown, r: WatchlistSignalItem) =>
        active && !matchesSummary(r.m30, filter, "m30") ? (
          <MissedCell />
        ) : (
          <SignalCell
            period="m30"
            summary={r.m30}
            status={r.m30_status}
            stockCode={r.stock_code}
            onAnalyze={onAnalyze}
          />
        ),
    },
  ];

  return (
    <div>
      {/* 筛选栏 */}
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center", marginBottom: 10 }}>
        <Select
          size="small"
          style={{ width: 110 }}
          value={filter.rangeKey}
          onChange={(v: RangeKey) => setFilter((f) => ({ ...f, rangeKey: v }))}
          options={[
            { value: "all", label: "全部时间" },
            { value: "today", label: "今日" },
            { value: "3d", label: "近三日" },
            { value: "7d", label: "近七日" },
            { value: "custom", label: "自定义" },
          ]}
        />
        {filter.rangeKey === "custom" && (
          <RangePicker
            size="small"
            allowEmpty={[false, false]}
            value={filter.customRange ?? undefined}
            onChange={(v) => setFilter((f) => ({ ...f, customRange: (v as [Dayjs | null, Dayjs | null]) ?? null }))}
          />
        )}
        <Select
          size="small"
          style={{ width: 100 }}
          value={filter.direction}
          onChange={(v) => setFilter((f) => ({ ...f, direction: v }))}
          options={[
            { value: "all", label: "全部信号" },
            { value: "buy", label: "买点" },
            { value: "sell", label: "卖点" },
          ]}
        />
        <Select
          size="small"
          style={{ width: 100 }}
          value={filter.period}
          onChange={(v) => setFilter((f) => ({ ...f, period: v }))}
          options={[
            { value: "all", label: "全部周期" },
            { value: "daily", label: "日 K" },
            { value: "m30", label: "30 分钟" },
          ]}
        />
        {active && (
          <>
            <Text type="secondary" style={{ fontSize: 12 }}>
              命中 {visibleItems.length} / {items.length} 只
            </Text>
            <a
              style={{ fontSize: 12 }}
              onClick={() => setFilter(DEFAULT_FILTER)}
            >
              重置
            </a>
          </>
        )}
      </div>

      <Table
        rowKey="stock_code"
        size="small"
        columns={columns}
        dataSource={visibleItems}
        loading={loading}
        pagination={{ pageSize: 10, size: "small", hideOnSinglePage: true }}
        locale={{
          emptyText: active ? "当前筛选条件下暂无命中信号" : "暂无自选股信号数据，请先在策略监控页重算或添加自选股",
        }}
      />
      <Text type="secondary" style={{ fontSize: 12 }}>
        置灰「历史」= 超出新鲜度窗口的历史信号（日 K 7 天 / 30 分钟 2 天），仅供回溯参考。
      </Text>
    </div>
  );
};

export default SignalOverviewTable;
