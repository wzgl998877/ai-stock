import React from "react";
import { Card, Progress, Tag, Space, Typography } from "antd";
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  SyncOutlined,
} from "@ant-design/icons";

const { Text } = Typography;

interface SyncProgressProps {
  status: "idle" | "running" | "completed" | "failed";
  processed: number;
  total: number;
  success: number;
  failed: number;
  errorMessage: string | null;
  sourceType: string;
  dataType: string;
  durationMs: number | null;
}

const STATUS_CONFIG: Record<string, { color: string; icon: React.ReactNode; text: string }> = {
  idle: { color: "default", icon: null, text: "等待中" },
  running: {
    color: "processing",
    icon: <SyncOutlined spin />,
    text: "同步中",
  },
  completed: {
    color: "success",
    icon: <CheckCircleOutlined />,
    text: "同步完成",
  },
  failed: {
    color: "error",
    icon: <CloseCircleOutlined />,
    text: "同步失败",
  },
};

const DATA_TYPE_LABELS: Record<string, string> = {
  basic_info: "基础信息",
  market_quote: "实时行情",
  daily_quote: "历史K线",
  financial: "财务数据",
};

const SyncProgress: React.FC<SyncProgressProps> = ({
  status,
  processed,
  total,
  success,
  failed,
  errorMessage,
  sourceType,
  dataType,
  durationMs,
}) => {
  if (status === "idle") {
    return null;
  }

  const config = STATUS_CONFIG[status];
  const percentage = total > 0 ? Math.round((processed / total) * 100) : 0;

  const formatDuration = (ms: number | null) => {
    if (!ms) return "";
    const seconds = Math.floor(ms / 1000);
    return `${seconds}s`;
  };

  return (
    <Card
      title={
        <Space>
          {config.icon}
          <Text>{config.text}</Text>
          <Tag color="blue">{sourceType}</Tag>
          <Tag>{DATA_TYPE_LABELS[dataType] || dataType}</Tag>
          {durationMs !== null && <Tag>耗时 {formatDuration(durationMs)}</Tag>}
        </Space>
      }
      size="small"
      style={{ marginBottom: 16 }}
    >
      <Progress
        percent={percentage}
        status={status === "failed" ? "exception" : status === "completed" ? "success" : "active"}
        format={() => `${processed} / ${total}`}
        strokeColor={status === "failed" ? "#ff4d4f" : undefined}
      />
      <div style={{ marginTop: 8 }}>
        <Space size="large">
          <Text type="secondary">成功: </Text>
          <Text type="success">{success}</Text>
          {failed > 0 && (
            <>
              <Text type="secondary">失败: </Text>
              <Text type="danger">{failed}</Text>
            </>
          )}
        </Space>
      </div>
      {errorMessage && (
        <div style={{ marginTop: 8 }}>
          <Text type="danger">错误: {errorMessage}</Text>
        </div>
      )}
    </Card>
  );
};

export default SyncProgress;
