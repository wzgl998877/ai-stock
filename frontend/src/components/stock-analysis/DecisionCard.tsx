import React from "react";
import { Card, Typography, Tag, Progress, Statistic, Row, Col, Alert } from "antd";
import { ArrowUpOutlined, ArrowDownOutlined, MinusOutlined } from "@ant-design/icons";
import type { DecisionEvent } from "../../domain/types";
import { highlightNumbers } from "../../utils/textUtils";

const { Text, Paragraph } = Typography;

const ACTION_CONFIG: Record<string, { color: string; bg: string; border: string; icon: React.ReactNode }> = {
  "买入": { color: "#15be53", bg: "#f0fdf4", border: "#bbf7d0", icon: <ArrowUpOutlined /> },
  "卖出": { color: "#ea2261", bg: "#fff1f2", border: "#fecdd3", icon: <ArrowDownOutlined /> },
  "持有": { color: "#3b82f6", bg: "#eff6ff", border: "#bfdbfe", icon: <MinusOutlined /> },
};

/** 风险评分色阶：0-30绿 / 31-60黄 / 61-80橙 / 81-100红 */
const getRiskColor = (score: number): string => {
  const pct = Math.round(score * 100);
  if (pct <= 30) return "#15be53";
  if (pct <= 60) return "#f59e0b";
  if (pct <= 80) return "#f97316";
  return "#ea2261";
};

interface DecisionCardProps {
  decision: DecisionEvent;
}

const DecisionCard: React.FC<DecisionCardProps> = ({ decision }) => {
  const config = ACTION_CONFIG[decision.action] || ACTION_CONFIG["持有"];
  const riskColor = getRiskColor(decision.risk_score || 0);

  return (
    <Card
      style={{ borderRadius: 6, border: `2px solid ${config.border}`, marginBottom: 12 }}
      styles={{ body: { padding: "16px 20px" } }}
    >
      {/* 操作方向 + 目标价 */}
      <Row gutter={16} align="middle" style={{ marginBottom: 16 }}>
        <Col>
          <Tag
            icon={config.icon}
            style={{
              fontSize: 16,
              borderRadius: 6,
              padding: "4px 16px",
              background: config.bg,
              color: config.color,
              border: `1px solid ${config.border}`,
              fontWeight: 500,
            }}
          >
            {decision.action}
          </Tag>
        </Col>
        <Col>
          <Statistic
            title={<Text style={{ fontSize: 11, color: "#94a3b8" }}>目标价</Text>}
            value={decision.target_price || 0}
            precision={2}
            suffix="元"
            valueStyle={{ fontSize: 20, color: "#061b31", fontWeight: 400, fontFeatureSettings: "'tnum'" }}
          />
        </Col>
      </Row>

      {/* 置信度 + 风险评分（色阶条+数字并行） */}
      <Row gutter={24} style={{ marginBottom: 16 }}>
        <Col xs={24} sm={12}>
          <Text style={{ fontSize: 11, color: "#94a3b8", display: "block", marginBottom: 6 }}>置信度</Text>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <Progress
              percent={Math.round((decision.confidence || 0) * 100)}
              strokeColor="#533afd"
              size="small"
              showInfo={false}
              style={{ flex: 1, marginBottom: 0 }}
            />
            <Text style={{ fontSize: 12, color: "#061b31", fontFeatureSettings: "'tnum' on", fontWeight: 500, flexShrink: 0 }}>
              {Math.round((decision.confidence || 0) * 100)}%
            </Text>
          </div>
        </Col>
        <Col xs={24} sm={12}>
          <Text style={{ fontSize: 11, color: "#94a3b8", display: "block", marginBottom: 6 }}>风险评分</Text>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <Progress
              percent={Math.round((decision.risk_score || 0) * 100)}
              strokeColor={riskColor}
              size="small"
              showInfo={false}
              style={{ flex: 1, marginBottom: 0 }}
            />
            <Text style={{ fontSize: 12, color: riskColor, fontFeatureSettings: "'tnum' on", fontWeight: 500, flexShrink: 0 }}>
              {Math.round((decision.risk_score || 0) * 100)}
            </Text>
          </div>
        </Col>
      </Row>

      {/* 决策依据 — 数字高亮 */}
      {decision.reasoning && (
        <div style={{ marginBottom: 12 }}>
          <Text style={{ fontSize: 11, color: "#94a3b8", display: "block", marginBottom: 4 }}>决策依据</Text>
          <Paragraph style={{ fontSize: 13, color: "#273951", lineHeight: 1.7, margin: 0 }}>
            {highlightNumbers(decision.reasoning)}
          </Paragraph>
        </div>
      )}

      {/* 免责声明 */}
      <Alert
        type="warning"
        message="以上分析仅供参考，不构成任何投资建议"
        showIcon
        style={{ borderRadius: 4, marginTop: 8 }}
        banner={false}
      />
    </Card>
  );
};

export default DecisionCard;
