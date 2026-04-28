import React from "react";
import { Card, Typography, Button } from "antd";
import { FireOutlined, SafetyCertificateOutlined, TeamOutlined, AuditOutlined, FileTextOutlined } from "@ant-design/icons";
import { AGENT_PROFILES } from "../../domain/constants";
import { useStockAnalysisStore } from "../../store/stockAnalysisStore";
import { extractFirstSentence, highlightNumbers } from "../../utils/textUtils";
import type { DebateEvent } from "../../domain/types";

const { Text, Paragraph } = Typography;

/** 格式化完成时间戳为 HH:mm */
const formatTime = (ts?: number) => {
  if (!ts) return "";
  const d = new Date(ts);
  return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
};

/** 风险角色配置 */
const RISK_ROLES = [
  { agent: "risky_debator", label: "激进派", icon: <FireOutlined />, phase: "risk" },
  { agent: "safe_debator", label: "保守派", icon: <SafetyCertificateOutlined />, phase: "risk" },
  { agent: "neutral_debator", label: "中立派", icon: <TeamOutlined />, phase: "risk" },
  { agent: "risk_judge", label: "风险裁决官", icon: <AuditOutlined />, phase: "risk" },
] as const;

interface RiskAssessmentSectionProps {
  debates: DebateEvent[];
}

/** 单个风险角色卡片 — 摘要 + 查看报告按钮 */
const RoleCard: React.FC<{
  agent: string;
  label: string;
  icon: React.ReactNode;
  content: string | null;
  status: string;
  completedAt?: number;
}> = ({ agent, label, icon, content, status, completedAt }) => {
  const profile = AGENT_PROFILES[agent];
  const colors = profile
    ? { bg: profile.bgColor, border: profile.borderColor, color: profile.color }
    : { bg: "#f8fafc", border: "#e5edf5", color: "#64748d" };
  const setSelectedReportAgent = useStockAnalysisStore((s) => s.setSelectedReportAgent);

  const isDone = status === "done";
  const isRunning = status === "running";

  // 只展示首句摘要
  const headline = content ? extractFirstSentence(content) : null;

  return (
    <Card
      size="small"
      style={{
        borderRadius: 6,
        border: `1px solid ${colors.border}`,
        background: colors.bg,
        height: "100%",
        transition: "all 0.2s ease",
      }}
      styles={{ body: { padding: 12 } }}
    >
      {/* 顶部：角色名 + 状态 */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <div style={{
            width: 28,
            height: 28,
            borderRadius: "50%",
            background: colors.bg,
            border: `1.5px solid ${colors.border}`,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: 14,
            flexShrink: 0,
            opacity: isDone ? 0.75 : 1,
            color: colors.color,
          }}>
            {profile?.emoji || icon}
          </div>
          <Text style={{ fontSize: 13, fontWeight: 500, color: "#061b31" }}>{label}</Text>
        </div>
        <Text style={{ fontSize: 11, color: isDone ? "#15be53" : isRunning ? "#3b82f6" : "#94a3b8" }}>
          {isDone ? `已完成${completedAt ? ` ${formatTime(completedAt)}` : ""}` : isRunning ? "分析中..." : "就绪"}
        </Text>
      </div>

      {/* 摘要首句 */}
      {headline ? (
        <Paragraph style={{ fontSize: 12, color: "#273951", lineHeight: 1.6, margin: 0, marginBottom: 6 }}>
          {highlightNumbers(headline)}
        </Paragraph>
      ) : (
        <Text style={{ fontSize: 12, color: "#94a3b8", fontStyle: "italic" }}>暂无输出</Text>
      )}

      {/* 查看完整报告按钮 */}
      {content && content.length > (headline?.length || 0) + 10 && (
        <Button
          type="link"
          size="small"
          icon={<FileTextOutlined />}
          style={{ fontSize: 11, color: "#533afd", padding: 0, marginTop: 2, height: "auto" }}
          onClick={() => setSelectedReportAgent(agent)}
        >
          查看完整报告
        </Button>
      )}
    </Card>
  );
};

const RiskAssessmentSection: React.FC<RiskAssessmentSectionProps> = ({ debates }) => {
  const agentStatuses = useStockAnalysisStore((s) => s.agentStatuses);
  const agentCompletedAt = useStockAnalysisStore((s) => s.agentCompletedAt);

  // 提取各角色的辩论内容（合并多轮）
  const getSpeakerContent = (speaker: string): string | null => {
    const items = debates.filter(d => d.speaker === speaker);
    if (items.length === 0) return null;
    return items.map(d => d.content).join("\n\n");
  };

  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 12 }}>
      {RISK_ROLES.map((role) => {
        const content = getSpeakerContent(role.agent);
        const status = agentStatuses[role.agent] || "pending";
        const completedAt = agentCompletedAt[role.agent];

        return (
          <RoleCard
            key={role.agent}
            agent={role.agent}
            label={role.label}
            icon={role.icon}
            content={content}
            status={status}
            completedAt={completedAt}
          />
        );
      })}
    </div>
  );
};

export default RiskAssessmentSection;
