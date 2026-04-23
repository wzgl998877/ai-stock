import React from "react";
import { Card, Typography, Skeleton, Tag, Collapse } from "antd";
import { StockOutlined, FundOutlined, ReadOutlined, HeartOutlined } from "@ant-design/icons";
import { AGENT_DISPLAY_NAMES } from "../../domain/constants";

const { Text, Paragraph } = Typography;

const AGENT_ICON_MAP: Record<string, React.ReactNode> = {
  market_analyst: <StockOutlined style={{ color: "#3b82f6" }} />,
  fundamentals_analyst: <FundOutlined style={{ color: "#15be53" }} />,
  news_analyst: <ReadOutlined style={{ color: "#f59e0b" }} />,
  sentiment_analyst: <HeartOutlined style={{ color: "#a855f7" }} />,
};

const AGENT_COLOR_MAP: Record<string, { bg: string; border: string; tag: string }> = {
  market_analyst: { bg: "#eff6ff", border: "#bfdbfe", tag: "blue" },
  fundamentals_analyst: { bg: "#f0fdf4", border: "#bbf7d0", tag: "green" },
  news_analyst: { bg: "#fffbeb", border: "#fde68a", tag: "orange" },
  sentiment_analyst: { bg: "#faf5ff", border: "#d8b4fe", tag: "purple" },
};

interface AgentReportCardProps {
  agent: string;
  summary: string;
  fullReport?: string;
  isRunning?: boolean;
  dataSource?: string;
}

const AgentReportCard: React.FC<AgentReportCardProps> = ({ agent, summary, fullReport, isRunning, dataSource }) => {
  const colors = AGENT_COLOR_MAP[agent] || { bg: "#f8fafc", border: "#e5edf5", tag: "default" };
  const icon = AGENT_ICON_MAP[agent];
  const displayName = AGENT_DISPLAY_NAMES[agent] || agent;

  if (isRunning) {
    return (
      <Card
        size="small"
        style={{ borderRadius: 6, border: `1px solid ${colors.border}`, background: colors.bg, marginBottom: 12 }}
        bodyStyle={{ padding: 12 }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
          {icon}
          <Text style={{ fontSize: 13, fontWeight: 400, color: "#061b31" }}>{displayName}</Text>
        </div>
        <Skeleton active paragraph={{ rows: 2 }} title={false} />
      </Card>
    );
  }

  return (
    <Card
      size="small"
      style={{ borderRadius: 6, border: `1px solid ${colors.border}`, background: colors.bg, marginBottom: 12 }}
      bodyStyle={{ padding: 12 }}
    >
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          {icon}
          <Text style={{ fontSize: 13, fontWeight: 400, color: "#061b31" }}>{displayName}</Text>
        </div>
        {dataSource && (
          <Tag style={{ fontSize: 10, borderRadius: 4, background: "#f8fafc", border: "1px solid #e5edf5", color: "#64748d" }}>
            {dataSource}
          </Tag>
        )}
      </div>
      <Paragraph style={{ fontSize: 13, color: "#273951", lineHeight: 1.6, margin: 0 }}>
        {summary}
      </Paragraph>
      {fullReport && fullReport !== summary && (
        <Collapse
          ghost
          size="small"
          style={{ marginTop: 8 }}
          items={[{ key: "detail", label: <Text style={{ fontSize: 11, color: "#533afd" }}>查看详细报告</Text>, children: <Paragraph style={{ fontSize: 12, color: "#273951", lineHeight: 1.7, whiteSpace: "pre-wrap" }}>{fullReport}</Paragraph> }]}
        />
      )}
    </Card>
  );
};

export default AgentReportCard;
