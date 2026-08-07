/**
 * 信号总览表（策略监控页）：自选股 × 双周期信号一览。
 *
 * 复用 ``SignalCell``（日 K / 30m 各一列），置灰=历史信号；
 * 无数据时展示空态（DESIGN.md loading/empty 约束），点击代码跳个股详情。
 */

import React from "react";
import { useNavigate } from "react-router-dom";
import { Table, Typography, Spin } from "antd";
import type { ColumnsType } from "antd/es/table";
import SignalCell from "./SignalCell";
import type { WatchlistSignalItem } from "../../domain/types";

const { Text } = Typography;

interface SignalOverviewTableProps {
  items: WatchlistSignalItem[];
  loading?: boolean;
  onAnalyze?: (code: string) => void;
}

export const SignalOverviewTable: React.FC<SignalOverviewTableProps> = ({
  items,
  loading = false,
  onAnalyze,
}) => {
  const navigate = useNavigate();

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
      render: (_: unknown, r: WatchlistSignalItem) => (
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
      render: (_: unknown, r: WatchlistSignalItem) => (
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
      <Table
        rowKey="stock_code"
        size="small"
        columns={columns}
        dataSource={items}
        loading={loading}
        pagination={{ pageSize: 10, size: "small", hideOnSinglePage: true }}
        locale={{
          emptyText: loading ? <Spin size="small" /> : "暂无自选股信号数据，请先在策略监控页重算或添加自选股",
        }}
      />
      <Text type="secondary" style={{ fontSize: 12 }}>
        置灰「历史」= 超出新鲜度窗口的历史信号（日 K 7 天 / 30 分钟 2 天），仅供回溯参考。
      </Text>
    </div>
  );
};

export default SignalOverviewTable;
