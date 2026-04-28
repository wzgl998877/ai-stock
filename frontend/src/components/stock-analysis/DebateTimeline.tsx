import React from "react";
import { Typography, Card, Button, Tag } from "antd";
import {
  ArrowUpOutlined, ArrowDownOutlined, FireOutlined,
  SafetyCertificateOutlined, TeamOutlined, AuditOutlined,
  FileTextOutlined, SwapOutlined, WarningOutlined,
} from "@ant-design/icons";
import { AGENT_DISPLAY_NAMES, AGENT_PROFILES } from "../../domain/constants";
import { extractFirstSentence, highlightNumbers } from "../../utils/textUtils";
import { useStockAnalysisStore } from "../../store/stockAnalysisStore";
import type { DebateEvent } from "../../domain/types";

const { Text, Paragraph } = Typography;

/** 角色配置 — 全部左右交替，没有居中 */
const SPEAKER_CONFIG: Record<string, {
  icon: React.ReactNode;
  color: string;
  bg: string;
  border: string;
  align: "left" | "right";
  prefix: string;
}> = {
  bull_researcher:    { icon: <ArrowUpOutlined />, color: "#15be53", bg: "#f0fdf4", border: "#bbf7d0", align: "left", prefix: "我是看多研究员" },
  bear_researcher:    { icon: <ArrowDownOutlined />, color: "#ea2261", bg: "#fff1f2", border: "#fecdd3", align: "right", prefix: "我是看空研究员" },
  research_manager:   { icon: <AuditOutlined />, color: "#0891b2", bg: "#ecfeff", border: "#a5f3fc", align: "left", prefix: "我是研究主管" },
  risky_debator:      { icon: <FireOutlined />, color: "#f59e0b", bg: "#fffbeb", border: "#fde68a", align: "left", prefix: "我是激进派分析师" },
  safe_debator:       { icon: <SafetyCertificateOutlined />, color: "#3b82f6", bg: "#eff6ff", border: "#bfdbfe", align: "right", prefix: "我是保守派分析师" },
  neutral_debator:    { icon: <TeamOutlined />, color: "#a855f7", bg: "#faf5ff", border: "#d8b4fe", align: "left", prefix: "我是中立派分析师" },
  risk_judge:         { icon: <AuditOutlined />, color: "#4f46e5", bg: "#eef2ff", border: "#c7d2fe", align: "right", prefix: "我是风险裁决官" },
};

const SUMMARY_MAX_LEN = 150;

const truncateSummary = (content: string): string => {
  const first = extractFirstSentence(content);
  if (first.length <= SUMMARY_MAX_LEN) return first;
  return first.slice(0, SUMMARY_MAX_LEN) + "...";
};

/** 构建带轮次的开头语 */
const buildOpening = (speaker: string, round: number): string => {
  const config = SPEAKER_CONFIG[speaker];
  if (!config) return "";
  const base = config.prefix;
  if (round > 0) return `${base}（第${round}轮），`;
  return `${base}，`;
};

interface DebateTimelineProps {
  debates: DebateEvent[];
  showRiskDebate?: boolean;
}

/** 聊天气泡 — 有内容 */
const ChatBubble: React.FC<{ debate: DebateEvent }> = ({ debate }) => {
  const config = SPEAKER_CONFIG[debate.speaker] || { icon: null, color: "#64748d", bg: "#f8fafc", border: "#e5edf5", align: "left" as const, prefix: "" };
  const setSelectedReportAgent = useStockAnalysisStore((s) => s.setSelectedReportAgent);
  const profile = AGENT_PROFILES[debate.speaker];
  const displayName = AGENT_DISPLAY_NAMES[debate.speaker] || debate.speaker;

  const summary = truncateSummary(debate.content);
  const hasMore = debate.content.length > summary.length + 10;
  const opening = buildOpening(debate.speaker, debate.round);

  const isRight = config.align === "right";

  return (
    <div style={{
      display: "flex",
      justifyContent: isRight ? "flex-end" : "flex-start",
      marginBottom: 14,
    }}>
      <div style={{ display: "flex", gap: 10, maxWidth: "78%", flexDirection: isRight ? "row-reverse" : "row" }}>
        {/* 头像 */}
        <div style={{
          width: 34, height: 34, borderRadius: "50%",
          background: config.bg, border: `1.5px solid ${config.border}`,
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: 16, flexShrink: 0, color: config.color,
          boxShadow: `0 0 0 3px ${config.bg}`,
          marginTop: 2,
        }}>
          {profile?.emoji || config.icon}
        </div>

        <div style={{ flex: 1, minWidth: 0 }}>
          {/* 角色名 */}
          <div style={{
            display: "flex", alignItems: "center", gap: 6, marginBottom: 5,
            justifyContent: isRight ? "flex-end" : "flex-start",
          }}>
            <Text style={{ fontSize: 12, fontWeight: 600, color: config.color }}>
              {displayName}
            </Text>
          </div>

          {/* 气泡 */}
          <div style={{
            padding: "12px 16px",
            borderRadius: isRight ? "12px 2px 12px 12px" : "2px 12px 12px 12px",
            background: config.bg,
            border: `1px solid ${config.border}`,
          }}>
            {opening && (
              <Text style={{ fontSize: 13, color: config.color, fontWeight: 500 }}>
                {opening}
              </Text>
            )}
            <Paragraph style={{ fontSize: 13, color: "#273951", lineHeight: 1.75, margin: 0, marginBottom: hasMore ? 6 : 0 }}>
              {highlightNumbers(summary)}
            </Paragraph>
            {hasMore && (
              <Button
                type="link"
                size="small"
                icon={<FileTextOutlined />}
                style={{ fontSize: 11, color: config.color, padding: 0, height: "auto" }}
                onClick={() => setSelectedReportAgent(debate.speaker)}
              >
                查看完整报告
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

/** 空气泡 — 未生成报告，保持角色颜色，不置灰 */
const EmptyBubble: React.FC<{ speaker: string }> = ({ speaker }) => {
  const config = SPEAKER_CONFIG[speaker] || { icon: null, color: "#94a3b8", bg: "#f8fafc", border: "#e5edf5", align: "left" as const, prefix: "" };
  const profile = AGENT_PROFILES[speaker];
  const displayName = AGENT_DISPLAY_NAMES[speaker] || speaker;

  const isRight = config.align === "right";

  return (
    <div style={{
      display: "flex",
      justifyContent: isRight ? "flex-end" : "flex-start",
      marginBottom: 14,
    }}>
      <div style={{ display: "flex", gap: 10, maxWidth: "78%", flexDirection: isRight ? "row-reverse" : "row" }}>
        <div style={{
          width: 34, height: 34, borderRadius: "50%",
          background: config.bg, border: `1.5px solid ${config.border}`,
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: 16, flexShrink: 0, color: config.color,
          boxShadow: `0 0 0 3px ${config.bg}`,
          marginTop: 2,
        }}>
          {profile?.emoji || config.icon}
        </div>

        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{
            display: "flex", alignItems: "center", gap: 6, marginBottom: 5,
            justifyContent: isRight ? "flex-end" : "flex-start",
          }}>
            <Text style={{ fontSize: 12, fontWeight: 600, color: config.color }}>
              {displayName}
            </Text>
          </div>
          <div style={{
            padding: "12px 16px",
            borderRadius: isRight ? "12px 2px 12px 12px" : "2px 12px 12px 12px",
            background: config.bg,
            border: `1px dashed ${config.border}`,
          }}>
            <Text style={{ fontSize: 12, color: "#94a3b8" }}>
              未生成报告（可能因 API 限流导致）
            </Text>
          </div>
        </div>
      </div>
    </div>
  );
};

/** 阶段分隔带 — 投资辩论 / 研究主管结论 / 风险辩论 / 风险裁决 */
const PhaseDivider: React.FC<{
  icon: React.ReactNode;
  label: string;
  color: string;
}> = ({ icon, label, color }) => (
  <div style={{
    display: "flex", alignItems: "center", gap: 10,
    margin: "8px 0 14px 0",
    padding: "6px 0",
    borderTop: `2px solid ${color}20`,
  }}>
    <div style={{
      width: 24, height: 24, borderRadius: 6,
      background: `${color}15`, border: `1px solid ${color}30`,
      display: "flex", alignItems: "center", justifyContent: "center",
      fontSize: 12, color,
    }}>
      {icon}
    </div>
    <Text style={{ fontSize: 12, fontWeight: 600, color }}>
      {label}
    </Text>
    <div style={{ flex: 1, height: 1, background: `${color}20` }} />
  </div>
);

const DebateTimeline: React.FC<DebateTimelineProps> = ({ debates, showRiskDebate = true }) => {
  if (debates.length === 0) return null;

  const investmentDebates = debates.filter(d => d.speaker.includes("researcher"));
  const riskDebates = debates.filter(d => d.speaker.includes("debator"));
  const managerDebate = debates.find(d => d.speaker === "research_manager");
  const riskJudgeDebate = debates.find(d => d.speaker === "risk_judge");

  const maxRound = Math.max(...investmentDebates.map(d => d.round), 0);
  const rounds = Array.from({ length: maxRound }, (_, i) => i + 1);

  return (
    <>
      {/* === 投资辩论 === */}
      {investmentDebates.length > 0 && (
        <Card
          size="small"
          style={{ borderRadius: 8, border: "1px solid #e5edf5", marginBottom: 16 }}
          styles={{ body: { padding: "16px 20px" } }}
        >
          {/* 卡片标题 */}
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
            <SwapOutlined style={{ fontSize: 14, color: "#533afd" }} />
            <Text style={{ fontSize: 14, fontWeight: 600, color: "#061b31" }}>投资辩论</Text>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 14 }}>
            <Tag style={{ fontSize: 10, borderRadius: 3, background: "#f0fdf4", color: "#15be53", border: "1px solid #bbf7d0", margin: 0, padding: "1px 6px" }}>
              <ArrowUpOutlined /> 看多
            </Tag>
            <Text style={{ fontSize: 10, color: "#94a3b8" }}>VS</Text>
            <Tag style={{ fontSize: 10, borderRadius: 3, background: "#fff1f2", color: "#ea2261", border: "1px solid #fecdd3", margin: 0, padding: "1px 6px" }}>
              <ArrowDownOutlined /> 看空
            </Tag>
          </div>

          {/* 辩论对话序列：每轮看多先说、看空后说 */}
          {rounds.map((round) => {
            const bull = investmentDebates.find(d => d.speaker === "bull_researcher" && d.round === round);
            const bear = investmentDebates.find(d => d.speaker === "bear_researcher" && d.round === round);
            return (
              <React.Fragment key={round}>
                {bull ? <ChatBubble debate={bull} /> : <EmptyBubble speaker="bull_researcher" />}
                {bear ? <ChatBubble debate={bear} /> : <EmptyBubble speaker="bear_researcher" />}
              </React.Fragment>
            );
          })}

          {/* 研究主管结论 — 明显的分隔 */}
          <PhaseDivider icon={<AuditOutlined />} label="辩论结论" color="#0891b2" />
          {managerDebate ? <ChatBubble debate={managerDebate} /> : <EmptyBubble speaker="research_manager" />}
        </Card>
      )}

      {/* === 风险辩论 === */}
      {showRiskDebate && riskDebates.length > 0 && (
        <Card
          size="small"
          style={{ borderRadius: 8, border: "1px solid #e5edf5", marginBottom: 16 }}
          styles={{ body: { padding: "16px 20px" } }}
        >
          {/* 卡片标题 */}
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
            <WarningOutlined style={{ fontSize: 14, color: "#f59e0b" }} />
            <Text style={{ fontSize: 14, fontWeight: 600, color: "#061b31" }}>风险评估辩论</Text>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 14 }}>
            <Tag style={{ fontSize: 10, borderRadius: 3, background: "#fffbeb", color: "#f59e0b", border: "1px solid #fde68a", margin: 0, padding: "1px 6px" }}>
              <FireOutlined /> 激进
            </Tag>
            <Text style={{ fontSize: 10, color: "#94a3b8" }}>VS</Text>
            <Tag style={{ fontSize: 10, borderRadius: 3, background: "#eff6ff", color: "#3b82f6", border: "1px solid #bfdbfe", margin: 0, padding: "1px 6px" }}>
              <SafetyCertificateOutlined /> 保守
            </Tag>
            <Text style={{ fontSize: 10, color: "#94a3b8" }}>+</Text>
            <Tag style={{ fontSize: 10, borderRadius: 3, background: "#faf5ff", color: "#a855f7", border: "1px solid #d8b4fe", margin: 0, padding: "1px 6px" }}>
              <TeamOutlined /> 中立
            </Tag>
          </div>

          {/* 按轮次渲染 */}
          {(() => {
            const riskMaxRound = Math.max(...riskDebates.map(d => d.round), 0);
            const riskRounds = Array.from({ length: riskMaxRound }, (_, i) => i + 1);
            return riskRounds.map((round) => {
              const risky = riskDebates.find(d => d.speaker === "risky_debator" && d.round === round);
              const safe = riskDebates.find(d => d.speaker === "safe_debator" && d.round === round);
              const neutral = riskDebates.find(d => d.speaker === "neutral_debator" && d.round === round);
              return (
                <React.Fragment key={round}>
                  {risky ? <ChatBubble debate={risky} /> : <EmptyBubble speaker="risky_debator" />}
                  {safe ? <ChatBubble debate={safe} /> : <EmptyBubble speaker="safe_debator" />}
                  {neutral ? <ChatBubble debate={neutral} /> : <EmptyBubble speaker="neutral_debator" />}
                </React.Fragment>
              );
            });
          })()}

          {/* 风险裁决官 */}
          <PhaseDivider icon={<AuditOutlined />} label="风险裁决" color="#4f46e5" />
          {riskJudgeDebate ? <ChatBubble debate={riskJudgeDebate} /> : <EmptyBubble speaker="risk_judge" />}
        </Card>
      )}
    </>
  );
};

export default DebateTimeline;
