/** 影响事件卡片 */

import React from "react";
import { Card, Tag, Button, Typography } from "antd";
import {
  EyeOutlined,
  ThunderboltOutlined,
} from "@ant-design/icons";
import { useNavigate } from "react-router-dom";

const { Text, Paragraph } = Typography;

interface MatchedStock {
  code: string;
  name: string;
  direction: string;
  confidence: number;
}

interface ImpactEventCardProps {
  impact: {
    id: number;
    event_id: number;
    title: string;
    summary: string | null;
    event_type: string | null;
    sentiment: string | null;
    importance: string | null;
    source_count: number;
    matched_stocks: MatchedStock[];
    priority: string;
    is_read: boolean;
    first_seen_at: string | null;
    source_name: string;
  };
  onViewDetail: (impactId: number) => void;
}

const sentimentConfig: Record<string, { color: string; label: string }> = {
  positive: { color: "#15be53", label: "利好" },
  negative: { color: "#ea2261", label: "利空" },
  neutral: { color: "#64748d", label: "中性" },
};

const priorityConfig: Record<string, { color: string; label: string }> = {
  P0: { color: "red", label: "紧急" },
  P1: { color: "orange", label: "重要" },
  P2: { color: "blue", label: "一般" },
};

const eventTypeLabels: Record<string, string> = {
  geopolitical: "地缘政治",
  policy: "政策",
  earnings: "业绩",
  industry: "行业",
  macro: "宏观",
  other: "其他",
};

const ImpactEventCard: React.FC<ImpactEventCardProps> = ({ impact, onViewDetail }) => {
  const navigate = useNavigate();
  const sentiment = sentimentConfig[impact.sentiment || "neutral"] || sentimentConfig.neutral;
  const priority = priorityConfig[impact.priority] || priorityConfig.P2;

  const handleQuickAnalysis = () => {
    const params = new URLSearchParams({
      eventTitle: impact.title,
      eventSummary: impact.summary || "",
      eventType: impact.event_type || "other",
    });
    navigate(`/analysis?${params.toString()}`);
  };

  const formatTime = (dateStr: string | null) => {
    if (!dateStr) return "";
    const d = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - d.getTime();
    const diffMin = Math.floor(diffMs / 60000);
    if (diffMin < 60) return `${diffMin}分钟前`;
    const diffHour = Math.floor(diffMin / 60);
    if (diffHour < 24) return `${diffHour}小时前`;
    return `${d.getMonth() + 1}/${d.getDate()}`;
  };

  return (
    <Card
      size="small"
      style={{
        borderRadius: 6,
        border: impact.is_read ? "1px solid #e5edf5" : "1px solid #533afd",
        borderLeft: `3px solid ${sentiment.color}`,
        marginBottom: 8,
      }}
      bodyStyle={{ padding: "12px 16px" }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 4 }}>
            <Tag color={priority.color} style={{ margin: 0, fontSize: 11 }}>{priority.label}</Tag>
            <Tag color={sentiment.color === "#15be53" ? "success" : sentiment.color === "#ea2261" ? "error" : "default"} style={{ margin: 0, fontSize: 11 }}>
              {sentiment.label}
            </Tag>
            {impact.event_type && (
              <Text style={{ fontSize: 12, color: "#94a3b8" }}>
                {eventTypeLabels[impact.event_type] || impact.event_type}
              </Text>
            )}
            {impact.source_count >= 3 && (
              <Tag color="volcano" style={{ margin: 0, fontSize: 11 }}>热点</Tag>
            )}
            <Text style={{ fontSize: 12, color: "#b0b8c4", marginLeft: "auto" }}>
              {formatTime(impact.first_seen_at)}
            </Text>
          </div>
          <Paragraph
            style={{ margin: 0, fontSize: 14, color: "#061b31", fontWeight: 500, lineHeight: 1.5 }}
            ellipsis={{ rows: 2 }}
          >
            {impact.title}
          </Paragraph>
          {impact.matched_stocks.length > 0 && (
            <div style={{ marginTop: 6, display: "flex", gap: 4, flexWrap: "wrap" }}>
              {impact.matched_stocks.slice(0, 4).map((stock) => (
                <Tag
                  key={stock.code}
                  color={stock.direction === "positive" ? "green" : stock.direction === "negative" ? "red" : "default"}
                  style={{ fontSize: 11, margin: 0 }}
                >
                  {stock.name || stock.code}
                  {stock.direction === "positive" ? " ▲" : stock.direction === "negative" ? " ▼" : ""}
                </Tag>
              ))}
            </div>
          )}
        </div>
      </div>
      <div style={{ display: "flex", justifyContent: "flex-end", gap: 6, marginTop: 8 }}>
        <Button size="small" icon={<EyeOutlined />} onClick={() => onViewDetail(impact.id)}>
          详情
        </Button>
        <Button size="small" type="primary" icon={<ThunderboltOutlined />} onClick={handleQuickAnalysis}>
          一键分析
        </Button>
      </div>
    </Card>
  );
};

export default ImpactEventCard;
