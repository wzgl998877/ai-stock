/**
 * 逐股逐周期监控启停表（策略监控页）。
 *
 * 关闭某周期后，定时调度将跳过该股的该周期计算（后端 t_strategy_monitor_config）。
 * 自选股页仅展示信号，开关统一收口在本页管理。
 */

import React, { useState } from "react";
import { Switch, Table, Typography, message } from "antd";
import type { ColumnsType } from "antd/es/table";
import type { WatchlistSignalItem } from "../../domain/types";
import { useStrategyStore } from "../../store/strategyStore";

const { Text } = Typography;

interface SignalMonitorConfigTableProps {
  items: WatchlistSignalItem[];
  loading?: boolean;
}

/** 单周期开关：点击即保存，保存中禁用防连点 */
const PeriodSwitch: React.FC<{
  stockCode: string;
  period: "daily" | "m30";
  checked: boolean;
}> = ({ stockCode, period, checked }) => {
  const updateConfig = useStrategyStore((s) => s.updateConfig);
  const [saving, setSaving] = useState(false);

  const toggle = async (enabled: boolean) => {
    setSaving(true);
    try {
      await updateConfig(stockCode, { [`${period}_enabled`]: enabled });
      message.success(`${period === "daily" ? "日 K" : "30 分钟"}监控已${enabled ? "开启" : "关闭"}`);
    } catch (e: any) {
      message.error(e?.message || "更新监控配置失败");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Switch size="small" checked={checked} loading={saving} onChange={(v) => toggle(v)} />
  );
};

export const SignalMonitorConfigTable: React.FC<SignalMonitorConfigTableProps> = ({
  items,
  loading = false,
}) => {
  const columns: ColumnsType<WatchlistSignalItem> = [
    {
      title: "代码",
      dataIndex: "stock_code",
      key: "stock_code",
      width: 96,
      align: "center",
    },
    {
      title: "名称",
      dataIndex: "stock_name",
      key: "stock_name",
      width: 120,
      align: "center",
    },
    {
      title: "日 K 监控",
      key: "daily_enabled",
      width: 100,
      align: "center",
      render: (_: unknown, r: WatchlistSignalItem) => (
        <PeriodSwitch
          stockCode={r.stock_code}
          period="daily"
          checked={r.daily_status !== "disabled"}
        />
      ),
    },
    {
      title: "30 分钟监控",
      key: "m30_enabled",
      width: 100,
      align: "center",
      render: (_: unknown, r: WatchlistSignalItem) => (
        <PeriodSwitch
          stockCode={r.stock_code}
          period="m30"
          checked={r.m30_status !== "disabled"}
        />
      ),
    },
  ];

  return (
    <div>
      <Table
        rowKey="stock_code"
        size="small"
        columns={columns}
        dataSource={items}
        loading={loading}
        pagination={{ pageSize: 10, size: "small", hideOnSinglePage: true }}
        locale={{ emptyText: "暂无自选股，添加自选股后可在此管理监控开关" }}
      />
      <Text type="secondary" style={{ fontSize: 12 }}>
        关闭后定时计算将跳过该股的对应周期；手动「立即重算」仅对开启的周期生效。
      </Text>
    </div>
  );
};

export default SignalMonitorConfigTable;
