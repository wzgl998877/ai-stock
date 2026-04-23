import React from "react";
import { Timeline, Typography, Card, Tag } from "antd";
import { ArrowUpOutlined, ArrowDownOutlined, FireOutlined, SafetyCertificateOutlined, BalanceOutlined } from "@ant-design/icons";
import { AGENT_DISPLAY_NAMES } from "../../domain/constants";
import type { DebateEvent } from "../../domain/types";

const { Text, Paragraph } = Typography;

const SPEAKER_CONFIG: Record<string, { icon: React.ReactNode; color: string; bg: string; border: string }> = {
  bull_researcher: { icon: <ArrowUpOutlined />, color: "#15be53", bg: "#f0fdf4", border: "#bbf7d0" },
  bear_researcher: { icon: <ArrowDownOutlined />, color: "#ea2261", bg: "#fff1f2", border: "#fecdd3" },
  risky_debator: { icon: <FireOutlined />, color: "#f59e0b", bg: "#fffbeb", border: "#fde68a" },
  safe_debator: { icon: <SafetyCertificateOutlined />, color: "#3b82f6", bg: "#eff6ff", border: "#bfdbfe" },
  neutral_debator: { icon: <BalanceOutlined />, color: "#a855f7", bg: "#faf5ff", border: "#d8b4fe" },
};

interface DebateTimelineProps {
  debates: DebateEvent[];
  showRiskDebate?: boolean;
}

const DebateTimeline: React.FC<DebateTimelineProps> = ({ debates, showRiskDebate = true }) => {
  if (debates.length === 0) return null;

  const investmentDebates = debates.filter(d => d.speaker.includes("researcher"));
  const riskDebates = debates.filter(d => d.speaker.includes("debator"));

  return (
    <Card
      size="small"
      title={<Text style={{ fontSize: 13, fontWeight: 400, color: "#273951" }}>投资辩论</Text>}
      style={{ borderRadius: 6, border: "1px solid #e5edf5", marginBottom: 12 }}
      bodyStyle={{ padding: "8px 16px" }}
    >
      {investmentDebates.length > 0 && (
        <div style={{ marginBottom: riskDebates.length > 0 ? 16 : 0 }}>
          <Text style={{ fontSize: 11, color: "#64748d", display: "block", marginBottom: 8 }}>看多 vs 看空</Text>
          <Timeline
            items={investmentDebates.map((debate, idx) => {
              const config = SPEAKER_CONFIG[debate.speaker] || { icon: null, color: "#64748d", bg: "#f8fafc", border: "#e5edf5" };
              return {
                color: debate.speaker === "bull_researcher" ? "green" : "red",
                children: (
                  <div style={{ padding: "4px 8px", borderRadius: 4, background: config.bg, border: `1px solid ${config.border}` }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 4 }}>
                      <Tag style={{ fontSize: 11, borderRadius: 4, background: config.bg, color: config.color, border: `1px solid ${config.border}`, margin: 0 }}>
                        {config.icon} {AGENT_DISPLAY_NAMES[debate.speaker] || debate.speaker}
                      </Tag>
                      <Text style={{ fontSize: 10, color: "#94a3b8" }}>第{debate.round}轮</Text>
                    </div>
                    <Paragraph style={{ fontSize: 12, color: "#273951", lineHeight: 1.6, margin: 0 }}>
                      {debate.content}
                    </Paragraph>
                  </div>
                ),
              };
            })}
          />
        </div>
      )}

      {showRiskDebate && riskDebates.length > 0 && (
        <div>
          <Text style={{ fontSize: 11, color: "#64748d", display: "block", marginBottom: 8 }}>风险评估辩论</Text>
          <Timeline
            items={riskDebates.map((debate) => {
              const config = SPEAKER_CONFIG[debate.speaker] || { icon: null, color: "#64748d", bg: "#f8fafc", border: "#e5edf5" };
              return {
                color: config.color as any,
                children: (
                  <div style={{ padding: "4px 8px", borderRadius: 4, background: config.bg, border: `1px solid ${config.border}` }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 4 }}>
                      <Tag style={{ fontSize: 11, borderRadius: 4, background: config.bg, color: config.color, border: `1px solid ${config.border}`, margin: 0 }}>
                        {config.icon} {AGENT_DISPLAY_NAMES[debate.speaker] || debate.speaker}
                      </Tag>
                      <Text style={{ fontSize: 10, color: "#94a3b8" }}>第{debate.round}轮</Text>
                    </div>
                    <Paragraph style={{ fontSize: 12, color: "#273951", lineHeight: 1.6, margin: 0 }}>
                      {debate.content}
                    </Paragraph>
                  </div>
                ),
              };
            })}
          />
        </div>
      )}
    </Card>
  );
};

export default DebateTimeline;
