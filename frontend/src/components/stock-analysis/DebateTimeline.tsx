import React from "react";
import { Typography, Card, Tag } from "antd";
import { ArrowUpOutlined, ArrowDownOutlined, FireOutlined, SafetyCertificateOutlined, TeamOutlined, AuditOutlined } from "@ant-design/icons";
import { AGENT_DISPLAY_NAMES } from "../../domain/constants";
import { highlightNumbers } from "../../utils/textUtils";
import type { DebateEvent } from "../../domain/types";

const { Text, Paragraph } = Typography;

const SPEAKER_CONFIG: Record<string, { icon: React.ReactNode; color: string; bg: string; border: string }> = {
  bull_researcher: { icon: <ArrowUpOutlined />, color: "#15be53", bg: "#f0fdf4", border: "#bbf7d0" },
  bear_researcher: { icon: <ArrowDownOutlined />, color: "#ea2261", bg: "#fff1f2", border: "#fecdd3" },
  research_manager: { icon: <AuditOutlined />, color: "#0891b2", bg: "#ecfeff", border: "#a5f3fc" },
  risky_debator: { icon: <FireOutlined />, color: "#f59e0b", bg: "#fffbeb", border: "#fde68a" },
  safe_debator: { icon: <SafetyCertificateOutlined />, color: "#3b82f6", bg: "#eff6ff", border: "#bfdbfe" },
  neutral_debator: { icon: <TeamOutlined />, color: "#a855f7", bg: "#faf5ff", border: "#d8b4fe" },
  risk_judge: { icon: <AuditOutlined />, color: "#4f46e5", bg: "#eef2ff", border: "#c7d2fe" },
};

interface DebateTimelineProps {
  debates: DebateEvent[];
  showRiskDebate?: boolean;
}

/** 单条辩论气泡 */
const DebateBubble: React.FC<{ debate: DebateEvent }> = ({ debate }) => {
  const config = SPEAKER_CONFIG[debate.speaker] || { icon: null, color: "#64748d", bg: "#f8fafc", border: "#e5edf5" };
  return (
    <div
      style={{
        padding: "8px 12px",
        borderRadius: 6,
        background: config.bg,
        border: `1px solid ${config.border}`,
        marginBottom: 8,
        transition: "all 0.2s ease",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 6 }}>
        <Tag style={{ fontSize: 11, borderRadius: 4, background: config.bg, color: config.color, border: `1px solid ${config.border}`, margin: 0 }}>
          {config.icon} {AGENT_DISPLAY_NAMES[debate.speaker] || debate.speaker}
        </Tag>
        <Text style={{ fontSize: 10, color: "#94a3b8" }}>第{debate.round}轮</Text>
      </div>
      <Paragraph style={{ fontSize: 12, color: "#273951", lineHeight: 1.6, margin: 0 }}>
        {highlightNumbers(debate.content)}
      </Paragraph>
    </div>
  );
};

const DebateTimeline: React.FC<DebateTimelineProps> = ({ debates, showRiskDebate = true }) => {
  if (debates.length === 0) return null;

  const investmentDebates = debates.filter(d => d.speaker.includes("researcher"));
  const riskDebates = debates.filter(d => d.speaker.includes("debator"));
  const managerDebate = debates.find(d => d.speaker === "research_manager");
  const riskJudgeDebate = debates.find(d => d.speaker === "risk_judge");

  // 按轮次配对看多/看空
  const maxRound = Math.max(
    ...investmentDebates.map(d => d.round),
    0
  );
  const rounds = Array.from({ length: maxRound }, (_, i) => i + 1);

  return (
    <>
      {/* === 投资辩论区：分栏对比 === */}
      {investmentDebates.length > 0 && (
        <Card
          size="small"
          style={{ borderRadius: 6, border: "1px solid #e5edf5", marginBottom: 12 }}
          styles={{ body: { padding: "12px 16px" } }}
        >
          {/* 研究主管总结 — 置顶锚点 */}
          {managerDebate && (
            <div style={{
              padding: "10px 14px",
              borderRadius: 6,
              background: "#ecfeff",
              border: "1px solid #a5f3fc",
              marginBottom: 14,
            }}>
              <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 6 }}>
                <Tag style={{ fontSize: 11, borderRadius: 4, background: "#ecfeff", color: "#0891b2", border: "1px solid #a5f3fc", margin: 0 }}>
                  <AuditOutlined /> {AGENT_DISPLAY_NAMES[managerDebate.speaker]}
                </Tag>
                <Text style={{ fontSize: 10, color: "#94a3b8" }}>辩论结论</Text>
              </div>
              <Paragraph style={{ fontSize: 13, color: "#273951", lineHeight: 1.6, margin: 0, fontWeight: 500 }}>
                {highlightNumbers(managerDebate.content)}
              </Paragraph>
            </div>
          )}

          {/* 分栏标题 */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr auto 1fr", gap: 0, marginBottom: 8 }}>
            <div style={{ textAlign: "center" }}>
              <Tag style={{ fontSize: 12, borderRadius: 4, background: "#f0fdf4", color: "#15be53", border: "1px solid #bbf7d0", margin: 0, padding: "2px 12px" }}>
                <ArrowUpOutlined /> 看多观点
              </Tag>
            </div>
            <div style={{ width: 1 }} />
            <div style={{ textAlign: "center" }}>
              <Tag style={{ fontSize: 12, borderRadius: 4, background: "#fff1f2", color: "#ea2261", border: "1px solid #fecdd3", margin: 0, padding: "2px 12px" }}>
                <ArrowDownOutlined /> 看空观点
              </Tag>
            </div>
          </div>

          {/* 分栏内容：按轮次配对 */}
          {rounds.map((round) => {
            const bullContent = investmentDebates.find(d => d.speaker === "bull_researcher" && d.round === round);
            const bearContent = investmentDebates.find(d => d.speaker === "bear_researcher" && d.round === round);
            return (
              <div key={round} style={{ display: "grid", gridTemplateColumns: "1fr auto 1fr", gap: 0, marginBottom: round < maxRound ? 8 : 0 }}>
                {/* 左栏：看多 */}
                <div style={{ paddingRight: 12 }}>
                  {bullContent ? <DebateBubble debate={bullContent} /> : (
                    <div style={{ padding: "8px 12px", borderRadius: 6, background: "#f8fafc", border: "1px solid #e5edf5", marginBottom: 8 }}>
                      <Text style={{ fontSize: 11, color: "#94a3b8" }}>本轮无看多观点</Text>
                    </div>
                  )}
                </div>

                {/* 中线 */}
                <div style={{
                  width: 1,
                  background: "linear-gradient(to bottom, transparent, #e5edf5 15%, #e5edf5 85%, transparent)",
                  margin: "4px 0",
                }} />

                {/* 右栏：看空 */}
                <div style={{ paddingLeft: 12 }}>
                  {bearContent ? <DebateBubble debate={bearContent} /> : (
                    <div style={{ padding: "8px 12px", borderRadius: 6, background: "#f8fafc", border: "1px solid #e5edf5", marginBottom: 8 }}>
                      <Text style={{ fontSize: 11, color: "#94a3b8" }}>本轮无看空观点</Text>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </Card>
      )}

      {/* === 风险辩论区：同样分栏 === */}
      {showRiskDebate && riskDebates.length > 0 && (
        <Card
          size="small"
          style={{ borderRadius: 6, border: "1px solid #e5edf5", marginBottom: 12 }}
          styles={{ body: { padding: "12px 16px" } }}
        >
          <Text style={{ fontSize: 13, fontWeight: 400, color: "#273951", display: "block", marginBottom: 10 }}>
            风险评估辩论
          </Text>

          {/* 风险裁决官总结 — 置顶 */}
          {riskJudgeDebate && (
            <div style={{
              padding: "10px 14px",
              borderRadius: 6,
              background: "#eef2ff",
              border: "1px solid #c7d2fe",
              marginBottom: 14,
            }}>
              <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 6 }}>
                <Tag style={{ fontSize: 11, borderRadius: 4, background: "#eef2ff", color: "#4f46e5", border: "1px solid #c7d2fe", margin: 0 }}>
                  <AuditOutlined /> {AGENT_DISPLAY_NAMES[riskJudgeDebate.speaker]}
                </Tag>
                <Text style={{ fontSize: 10, color: "#94a3b8" }}>风险定论</Text>
              </div>
              <Paragraph style={{ fontSize: 13, color: "#273951", lineHeight: 1.6, margin: 0, fontWeight: 500 }}>
                {highlightNumbers(riskJudgeDebate.content)}
              </Paragraph>
            </div>
          )}

          {/* 分栏：激进 vs 保守 + 中立 */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr auto 1fr", gap: 0, marginBottom: 8 }}>
            <div style={{ textAlign: "center" }}>
              <Tag style={{ fontSize: 12, borderRadius: 4, background: "#fffbeb", color: "#f59e0b", border: "1px solid #fde68a", margin: 0, padding: "2px 12px" }}>
                <FireOutlined /> 激进观点
              </Tag>
            </div>
            <div style={{ width: 1 }} />
            <div style={{ textAlign: "center" }}>
              <Tag style={{ fontSize: 12, borderRadius: 4, background: "#eff6ff", color: "#3b82f6", border: "1px solid #bfdbfe", margin: 0, padding: "2px 12px" }}>
                <SafetyCertificateOutlined /> 保守观点
              </Tag>
            </div>
          </div>

          {/* 按轮次配对 */}
          {(() => {
            const riskMaxRound = Math.max(...riskDebates.map(d => d.round), 0);
            const riskRounds = Array.from({ length: riskMaxRound }, (_, i) => i + 1);
            return riskRounds.map((round) => {
              const riskyContent = riskDebates.find(d => d.speaker === "risky_debator" && d.round === round);
              const safeContent = riskDebates.find(d => d.speaker === "safe_debator" && d.round === round);
              const neutralContent = riskDebates.find(d => d.speaker === "neutral_debator" && d.round === round);
              return (
                <div key={round} style={{ marginBottom: round < riskMaxRound ? 8 : 0 }}>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr auto 1fr", gap: 0 }}>
                    {/* 左栏：激进 */}
                    <div style={{ paddingRight: 12 }}>
                      {riskyContent ? <DebateBubble debate={riskyContent} /> : (
                        <div style={{ padding: "8px 12px", borderRadius: 6, background: "#f8fafc", border: "1px solid #e5edf5", marginBottom: 8 }}>
                          <Text style={{ fontSize: 11, color: "#94a3b8" }}>本轮无激进观点</Text>
                        </div>
                      )}
                    </div>

                    {/* 中线 */}
                    <div style={{
                      width: 1,
                      background: "linear-gradient(to bottom, transparent, #e5edf5 15%, #e5edf5 85%, transparent)",
                      margin: "4px 0",
                    }} />

                    {/* 右栏：保守 */}
                    <div style={{ paddingLeft: 12 }}>
                      {safeContent ? <DebateBubble debate={safeContent} /> : (
                        <div style={{ padding: "8px 12px", borderRadius: 6, background: "#f8fafc", border: "1px solid #e5edf5", marginBottom: 8 }}>
                          <Text style={{ fontSize: 11, color: "#94a3b8" }}>本轮无保守观点</Text>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* 中立派 — 居中通栏 */}
                  {neutralContent && (
                    <div style={{ marginTop: 4, padding: "0 24px" }}>
                      <DebateBubble debate={neutralContent} />
                    </div>
                  )}
                </div>
              );
            });
          })()}
        </Card>
      )}
    </>
  );
};

export default DebateTimeline;
