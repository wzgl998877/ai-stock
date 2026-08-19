/**
 * 缠论信号历史列表（T040）。
 *
 * 按周期/类型筛选 + 分页；失效信号以删除线展示并附失效原因；
 * 「在 K 线图中查看」跳转个股详情并经 ``?signalDate=&period=`` 定位 K 线（D4）。
 *
 * 数据经 ``services/strategyService``（宪章前端红线：页面/组件不直连网络）。
 */

import React, { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Table, Tag, Segmented, Select, Empty, Alert, Skeleton, Typography, Button } from "antd";
import { getSignals } from "../../services/strategyService";
import {
  SIGNAL_BADGE_COLORS,
  SIGNAL_TYPE_LABELS,
  STRATEGY_DISCLAIMER,
} from "../../domain/constants";
import type { ChanlunPeriod, SignalHistoryItem, SignalType } from "../../domain/types";

const { Text } = Typography;

interface SignalHistoryListProps {
  stockCode: string;
}

const PERIOD_OPTIONS = [
  { label: "日 K", value: "daily" as ChanlunPeriod },
  { label: "30 分钟", value: "m30" as ChanlunPeriod },
];

const ALL_TYPES: SignalType[] = ["buy1", "buy2", "buy3", "sell1", "sell2", "sell3"];
const TYPE_OPTIONS: { label: string; value: SignalType | "all" }[] = [
  { label: "全部类型", value: "all" },
  ...ALL_TYPES.map((t) => ({ label: SIGNAL_TYPE_LABELS[t], value: t as SignalType | "all" })),
];

function fmtTime(t: string | null): string {
  if (!t) return "—";
  return t.replace("T", " ").slice(0, 16);
}

export const SignalHistoryList: React.FC<SignalHistoryListProps> = ({ stockCode }) => {
  const navigate = useNavigate();
  const [period, setPeriod] = useState<ChanlunPeriod>("daily");
  const [typeFilter, setTypeFilter] = useState<SignalType | "all">("all");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [items, setItems] = useState<SignalHistoryItem[]>([]);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getSignals(stockCode, { period, limit: 100 });
      setItems(res.items || []);
    } catch (e: any) {
      setItems([]);
      setError(e?.message || "信号历史加载失败");
    } finally {
      setLoading(false);
    }
  }, [stockCode, period]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const filtered = typeFilter === "all" ? items : items.filter((i) => i.signal_type === typeFilter);

  const columns = [
    {
      title: "类型",
      dataIndex: "signal_type",
      width: 100,
      render: (t: SignalType) => {
        const c = SIGNAL_BADGE_COLORS[t];
        return (
          <Tag style={{ margin: 0, color: c, borderColor: c, background: `${c}14` }}>
            {SIGNAL_TYPE_LABELS[t]}
          </Tag>
        );
      },
    },
    {
      title: "时间",
      dataIndex: "signal_time",
      width: 150,
      render: (t: string) => fmtTime(t),
    },
    {
      title: "触发价",
      dataIndex: "trigger_price",
      width: 90,
      align: "right" as const,
      render: (v: number | null) => (v != null ? v.toFixed(2) : "—"),
    },
    {
      title: "结构",
      dataIndex: "structure_level",
      width: 70,
      render: (l: string) => (l === "segment" ? "线段" : "笔"),
    },
    {
      title: "状态",
      dataIndex: "status",
      width: 90,
      render: (_: unknown, r: SignalHistoryItem) =>
        r.status === "invalidated" ? (
          <Text delete type="secondary" style={{ fontSize: 12 }}>
            已失效
          </Text>
        ) : (
          <Text type="success" style={{ fontSize: 12 }}>
            已确认
          </Text>
        ),
    },
    {
      title: "微信推送",
      dataIndex: "push_status",
      width: 90,
      render: (v: SignalHistoryItem["push_status"]) => {
        if (v === "success") return <Text type="success" style={{ fontSize: 12 }}>已推送</Text>;
        if (v === "failed") return <Text type="danger" style={{ fontSize: 12 }}>推送失败</Text>;
        if (v === "skipped") return <Text type="warning" style={{ fontSize: 12 }}>未激活跳过</Text>;
        return <Text type="secondary" style={{ fontSize: 12 }}>—</Text>;
      },
    },
    {
      title: "失效原因",
      dataIndex: "invalidated_reason",
      render: (r: string | null) => (r ? <Text type="secondary" style={{ fontSize: 12 }}>{r}</Text> : "—"),
    },
    {
      title: "操作",
      width: 130,
      render: (_: unknown, r: SignalHistoryItem) => (
        <Button
          type="link"
          size="small"
          style={{ padding: 0 }}
          onClick={() =>
            navigate(
              `/market/stock/${stockCode}?signalDate=${String(r.signal_time).slice(0, 10)}&period=${period}`,
            )
          }
        >
          在 K 线图中查看
        </Button>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: "flex", gap: 12, marginBottom: 12, flexWrap: "wrap", alignItems: "center" }}>
        <Segmented
          options={PERIOD_OPTIONS}
          value={period}
          onChange={(v) => setPeriod(v as ChanlunPeriod)}
        />
        <Select
          style={{ width: 150 }}
          value={typeFilter}
          options={TYPE_OPTIONS}
          onChange={(v) => setTypeFilter(v as SignalType | "all")}
        />
        <Text type="secondary" style={{ fontSize: 12 }}>
          共 {filtered.length} 条
        </Text>
      </div>

      {error ? (
        <Alert type="error" message={error} showIcon action={<a onClick={fetchData}>重试</a>} />
      ) : loading ? (
        <Skeleton active paragraph={{ rows: 5 }} />
      ) : filtered.length === 0 ? (
        <Empty description={items.length === 0 ? "暂无信号记录" : "当前筛选无匹配信号"} />
      ) : (
        <Table<SignalHistoryItem>
          rowKey={(r) => `${r.period}-${r.signal_type}-${r.signal_time}`}
          size="small"
          dataSource={filtered}
          columns={columns}
          pagination={{ pageSize: 10, showSizeChanger: false, size: "small" }}
          rowClassName={(r) => (r.status === "invalidated" ? "chanlun-row-invalidated" : "")}
          scroll={{ x: "max-content" }}
        />
      )}

      <Alert
        type="warning"
        style={{ marginTop: 12 }}
        message={STRATEGY_DISCLAIMER}
        banner
      />
    </div>
  );
};

export default SignalHistoryList;
