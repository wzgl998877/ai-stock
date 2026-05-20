import React, { useEffect, useCallback } from "react";
import { Table, Tag, Space, Typography, Button, Tooltip } from "antd";
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  SyncOutlined,
  RedoOutlined,
} from "@ant-design/icons";
import { useSyncStore } from "../../store/syncStore";
import type { ColumnsType } from "antd/es/table";
import type { SyncTaskRecord } from "../../services/syncService";

const { Text } = Typography;

const STATUS_MAP: Record<string, { color: string; icon: React.ReactNode; text: string }> = {
  pending: { color: "default", icon: <SyncOutlined />, text: "等待中" },
  running: { color: "processing", icon: <SyncOutlined spin />, text: "运行中" },
  completed: { color: "success", icon: <CheckCircleOutlined />, text: "完成" },
  failed: { color: "error", icon: <CloseCircleOutlined />, text: "失败" },
};

const SOURCE_TAG_COLORS: Record<string, string> = {
  tushare: "blue",
  akshare: "green",
  baostock: "orange",
  sina: "red",
};

const DATA_TYPE_LABELS: Record<string, string> = {
  basic_info: "基础信息",
  market_quote: "实时行情",
  daily_quote: "历史K线",
  financial: "财务数据",
};

const SyncHistory: React.FC = () => {
  const { syncHistory, historyTotal, historyPage, isLoadingHistory, loadHistory } =
    useSyncStore();

  useEffect(() => {
    loadHistory(1);
  }, []);

  const handlePageChange = useCallback(
    (page: number) => {
      loadHistory(page);
    },
    [loadHistory],
  );

  const handleRetry = useCallback(
    (task: SyncTaskRecord) => {
      useSyncStore.getState().retryTask(task.task_id);
      // Reload history after retry
      setTimeout(() => loadHistory(1), 1000);
    },
    [loadHistory],
  );

  const columns: ColumnsType<SyncTaskRecord> = [
    {
      title: "状态",
      dataIndex: "status",
      width: 100,
      render: (status: string) => {
        const config = STATUS_MAP[status] || STATUS_MAP.pending;
        return (
          <Tag color={config.color} icon={config.icon}>
            {config.text}
          </Tag>
        );
      },
    },
    {
      title: "数据源",
      dataIndex: "source_type",
      width: 100,
      render: (type: string) => (
        <Tag color={SOURCE_TAG_COLORS[type] || "default"}>{type}</Tag>
      ),
    },
    {
      title: "数据类型",
      dataIndex: "data_type",
      width: 100,
      render: (type: string) => DATA_TYPE_LABELS[type] || type,
    },
    {
      title: "数量",
      width: 140,
      render: (_, record) => (
        <Space>
          <Text>总计 {record.total_count || "-"}</Text>
          <Text type="success">成功 {record.success_count || 0}</Text>
          {record.fail_count > 0 && (
            <Text type="danger">失败 {record.fail_count}</Text>
          )}
        </Space>
      ),
    },
    {
      title: "耗时",
      dataIndex: "duration_ms",
      width: 80,
      render: (ms: number | null) => (ms ? `${Math.floor(ms / 1000)}s` : "-"),
    },
    {
      title: "时间",
      dataIndex: "start_time",
      width: 180,
      render: (time: string) => (time ? new Date(time).toLocaleString("zh-CN") : "-"),
    },
    {
      title: "操作",
      width: 80,
      render: (_, record) =>
        record.status === "failed" ? (
          <Tooltip title="重试">
            <Button
              type="link"
              icon={<RedoOutlined />}
              size="small"
              onClick={() => handleRetry(record)}
            />
          </Tooltip>
        ) : null,
    },
  ];

  return (
    <Table
      columns={columns}
      dataSource={syncHistory}
      rowKey="task_id"
      loading={isLoadingHistory}
      pagination={{
        current: historyPage,
        total: historyTotal,
        pageSize: 20,
        onChange: handlePageChange,
        showSizeChanger: false,
      }}
      size="small"
    />
  );
};

export default SyncHistory;
