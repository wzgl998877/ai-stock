import React from "react";
import { Card, Typography, Tag, Collapse } from "antd";
import { CheckCircleFilled, CloseCircleFilled, LoadingOutlined, ClockCircleOutlined } from "@ant-design/icons";
import { AGENT_DISPLAY_NAMES, AGENT_PROFILES } from "../../domain/constants";
import { useStockAnalysisStore } from "../../store/stockAnalysisStore";
import { extractFirstSentence, extractRemainingText, highlightNumbers } from "../../utils/textUtils";

const { Text, Paragraph } = Typography;

/** 格式化完成时间戳为 HH:mm */
const formatTime = (ts?: number) => {
  if (!ts) return "";
  const d = new Date(ts);
  return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
};

/** 状态图标与颜色映射 */
const STATUS_CONFIG: Record<string, { icon: React.ReactNode; color: string; label: string }> = {
  running: { icon: <LoadingOutlined style={{ fontSize: 11 }} spin />, color: "#3b82f6", label: "分析中" },
  done: { icon: <CheckCircleFilled style={{ fontSize: 11 }} />, color: "#15be53", label: "已完成" },
  failed: { icon: <CloseCircleFilled style={{ fontSize: 11 }} />, color: "#ea2261", label: "失败" },
  pending: { icon: <ClockCircleOutlined style={{ fontSize: 11 }} />, color: "#94a3b8", label: "就绪" },
};

interface AgentReportCardProps {
  agent: string;
  summary: string;
  fullReport?: string;
  isRunning?: boolean;
  thinkingMessage?: string;
  dataSource?: string;
  gridMode?: boolean;
}

const AgentReportCard: React.FC<AgentReportCardProps> = ({ agent, summary, fullReport, isRunning, thinkingMessage, dataSource, gridMode }) => {
  const agentCompletedAt = useStockAnalysisStore((s) => s.agentCompletedAt);
  const agentStatuses = useStockAnalysisStore((s) => s.agentStatuses);
  const profile = AGENT_PROFILES[agent];
  const displayName = AGENT_DISPLAY_NAMES[agent] || agent;
  const colors = profile
    ? { bg: profile.bgColor, border: profile.borderColor }
    : { bg: "#f8fafc", border: "#e5edf5" };
  const completedAt = agentCompletedAt[agent];
  const status = agentStatuses[agent] || "pending";
  const statusConfig = STATUS_CONFIG[status] || STATUS_CONFIG.pending;

  // 首句切分
  const headline = extractFirstSentence(summary);
  const detail = extractRemainingText(summary);

  const cardStyle: React.CSSProperties = {
    borderRadius: 6,
    border: `1px solid ${colors.border}`,
    background: colors.bg,
    marginBottom: gridMode ? 0 : 12,
    height: gridMode ? "100%" : "auto",
    transition: "all 0.2s ease",
  };

  if (isRunning) {
    return (
      <Card
        size="small"
        style={cardStyle}
        styles={{ body: { padding: 12 } }}
      >
        {/* 头像 + 名字 */}
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
          <div style={{
            width: 28,
            height: 28,
            borderRadius: "50%",
            background: profile?.bgColor || "#f0efff",
            border: `1.5px solid ${profile?.borderColor || "#d6d9fc"}`,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: 14,
            flexShrink: 0,
            boxShadow: `0 0 0 3px ${profile?.bgColor || "#f0efff"}`,
            animation: "agentBreath 2s ease-in-out infinite",
          }}>
            {profile?.emoji || "🤖"}
          </div>
          <Text style={{ fontSize: 13, fontWeight: 400, color: "#061b31" }}>{displayName}</Text>
          <Text style={{ fontSize: 11, color: statusConfig.color }}>
            {statusConfig.icon} {statusConfig.label}
          </Text>
        </div>

        {/* 思考文案 */}
        <div style={{ display: "flex", alignItems: "flex-start", gap: 6, marginBottom: 10 }}>
          <span style={{ fontSize: 13, color: "#94a3b8" }}>&#x1F4AD;</span>
          <Text style={{ fontSize: 13, color: "#64748d", lineHeight: 1.5 }}>
            {thinkingMessage || profile?.thinkingMessage || "正在分析中..."}
            <span className="thinking-dots" />
          </Text>
        </div>

        {/* 脉冲进度条 */}
        <div style={{
          height: 3,
          borderRadius: 2,
          background: "#e5edf5",
          overflow: "hidden",
        }}>
          <div
            className="pulse-progress-bar"
            style={{
              height: "100%",
              borderRadius: 2,
              background: `linear-gradient(90deg, ${profile?.color || "#533afd"}, ${profile?.bgColor || "#f0efff"})`,
            }}
          />
        </div>
      </Card>
    );
  }

  // 已完成/失败/等待态的渲染
  return (
    <Card
      size="small"
      style={cardStyle}
      styles={{ body: { padding: 12 } }}
    >
      {/* 顶部：头像 + 名字 + 状态 */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <div style={{
            width: 28,
            height: 28,
            borderRadius: "50%",
            background: profile?.bgColor || "#f0efff",
            border: `1.5px solid ${profile?.borderColor || "#d6d9fc"}`,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: 14,
            flexShrink: 0,
            opacity: status === "done" ? 0.75 : 1,
          }}>
            {profile?.emoji || "🤖"}
          </div>
          <Text style={{ fontSize: 13, fontWeight: 400, color: "#061b31" }}>{displayName}</Text>
          <Text style={{ fontSize: 11, color: statusConfig.color }}>
            {statusConfig.icon} {statusConfig.label}{completedAt ? ` ${formatTime(completedAt)}` : ""}
          </Text>
        </div>
        {dataSource && (
          <Tag style={{ fontSize: 10, borderRadius: 4, background: "#f8fafc", border: "1px solid #e5edf5", color: "#64748d" }}>
            {dataSource}
          </Tag>
        )}
      </div>

      {/* 核心结论摘要行 — 加粗 + 数字高亮 */}
      {headline && (
        <Paragraph
          style={{
            fontSize: 13,
            fontWeight: 500,
            color: "#061b31",
            lineHeight: 1.6,
            margin: 0,
            marginBottom: detail ? 0 : 8,
            fontFeatureSettings: "'ss01' on",
          }}
        >
          {highlightNumbers(headline)}
        </Paragraph>
      )}

      {/* 推理详情 — 默认折叠 */}
      {detail && (
        <Collapse
          ghost
          size="small"
          style={{ marginTop: 4 }}
          items={[{
            key: "detail",
            label: <Text style={{ fontSize: 11, color: "#533afd", cursor: "pointer" }}>查看详细推理</Text>,
            children: (
              <Paragraph style={{ fontSize: 12, color: "#273951", lineHeight: 1.7, margin: 0, whiteSpace: "pre-wrap" }}>
                {highlightNumbers(detail)}
              </Paragraph>
            ),
          }]}
        />
      )}

      {/* 兜底：fullReport（后端扩展后启用） */}
      {fullReport && fullReport !== summary && (
        <Collapse
          ghost
          size="small"
          style={{ marginTop: 4 }}
          items={[{
            key: "full",
            label: <Text style={{ fontSize: 11, color: "#533afd", cursor: "pointer" }}>查看完整报告</Text>,
            children: <Paragraph style={{ fontSize: 12, color: "#273951", lineHeight: 1.7, whiteSpace: "pre-wrap" }}>{fullReport}</Paragraph>,
          }]}
        />
      )}
    </Card>
  );
};

export default AgentReportCard;
