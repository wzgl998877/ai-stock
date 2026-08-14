/**
 * 回测明细 Drawer（T048）。
 *
 * 按汇总单元格的 (period, signal_type, window) 下钻：明细列表 + 该窗口收益分布直方图
 * （T049）+「在 K 线图中查看」跳转个股详情定位 K 线（D4）。失效/越界窗口样本已剔除。
 */

import React, { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Drawer, Table, Skeleton, Empty, Alert, Typography, Tag } from "antd";
import { getReportDetails } from "../../services/strategyService";
import {
  SIGNAL_TYPE_LABELS,
  STRATEGY_DISCLAIMER,
} from "../../domain/constants";
import type {
  BacktestSignalDetailItem,
  BacktestWindow,
  ChanlunPeriod,
  SignalType,
} from "../../domain/types";
import ReturnDistributionChart from "./ReturnDistributionChart";

const { Text } = Typography;

export interface BacktestDetailFilter {
  period: ChanlunPeriod;
  signal_type: SignalType;
  window: BacktestWindow;
}

interface BacktestDetailDrawerProps {
  open: boolean;
  onClose: () => void;
  reportId: number | null;
  filter: BacktestDetailFilter | null;
}

export const BacktestDetailDrawer: React.FC<BacktestDetailDrawerProps> = ({
  open,
  onClose,
  reportId,
  filter,
}) => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [items, setItems] = useState<BacktestSignalDetailItem[]>([]);

  const fetchData = useCallback(async () => {
    if (!reportId || !filter) return;
    setLoading(true);
    try {
      const res = await getReportDetails(reportId, {
        period: filter.period,
        signal_type: filter.signal_type,
        window: filter.window,
        page_size: 100,
      });
      setItems(res.items);
    } catch {
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, [reportId, filter]);

  useEffect(() => {
    if (open) fetchData();
  }, [open, fetchData]);

  const winAttr = filter ? `ret_${filter.window}` : "ret_20";
  const title = filter
    ? `${SIGNAL_TYPE_LABELS[filter.signal_type]} · ${filter.window} 日明细`
    : "回测明细";

  const columns = [
    {
      title: "代码", dataIndex: "stock_code", width: 90,
      render: (c: string) => <span style={{ fontVariantNumeric: "tabular-nums" }}>{c}</span>,
    },
    {
      title: "时间", dataIndex: "signal_time", width: 140,
      render: (t: string) => (t ? t.replace("T", " ").slice(0, 16) : "—"),
    },
    {
      title: "触发价", dataIndex: "trigger_price", width: 90, align: "right" as const,
      render: (v: number | null) => (v != null ? v.toFixed(2) : "—"),
    },
    {
      title: `${filter?.window ?? 20}日收益`, key: "ret", width: 110, align: "right" as const,
      render: (_: unknown, r: BacktestSignalDetailItem) => {
        const v = (r as any)[winAttr] as number | null;
        if (v == null) return <Text type="secondary">—</Text>;
        const color = v >= 0 ? "#ea2261" : "#16c79a";
        return <span style={{ color, fontVariantNumeric: "tabular-nums" }}>{(v * 100).toFixed(2)}%</span>;
      },
    },
    {
      title: "操作", width: 130,
      render: (_: unknown, r: BacktestSignalDetailItem) => (
        <a
          style={{ fontSize: 12 }}
          onClick={() =>
            navigate(
              `/market/stock/${r.stock_code}?signalDate=${String(r.signal_time).slice(0, 10)}&period=${filter?.period ?? "daily"}`,
            )
          }
        >
          在 K 线图中查看
        </a>
      ),
    },
  ];

  const returns = items.map((r) => (r as any)[winAttr] as number | null).filter((v): v is number => v != null);

  return (
    <Drawer title={title} open={open} onClose={onClose} width={560} destroyOnClose>
      {filter && (
        <div style={{ marginBottom: 12 }}>
          <Tag color="purple">{filter.period === "daily" ? "日 K" : "30 分钟"}</Tag>
          <Tag color="purple">{SIGNAL_TYPE_LABELS[filter.signal_type]}</Tag>
          <Tag color="purple">{filter.window} 日窗口</Tag>
        </div>
      )}

      <div style={{ marginBottom: 16 }}>
        <Text type="secondary" style={{ fontSize: 12 }}>
          {filter?.window ?? 20} 日窗口收益分布
        </Text>
        <ReturnDistributionChart returns={returns} window={filter?.window ?? 20} height={200} />
      </div>

      {loading ? (
        <Skeleton active paragraph={{ rows: 6 }} />
      ) : items.length === 0 ? (
        <Empty description="暂无明细样本" />
      ) : (
        <Table<BacktestSignalDetailItem>
          rowKey={(r) => `${r.stock_code}-${r.signal_time}`}
          size="small"
          dataSource={items}
          columns={columns as any}
          pagination={{ pageSize: 10, showSizeChanger: false, size: "small" }}
          scroll={{ x: "max-content" }}
        />
      )}

      <Alert style={{ marginTop: 12 }} type="warning" message={STRATEGY_DISCLAIMER} banner />
    </Drawer>
  );
};

export default BacktestDetailDrawer;
