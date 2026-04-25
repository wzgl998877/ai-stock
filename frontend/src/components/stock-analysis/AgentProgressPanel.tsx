import React from "react";
import { Typography } from "antd";
import {
  StockOutlined,
  SwapOutlined,
  DollarOutlined,
  SafetyCertificateOutlined,
  CheckCircleFilled,
  CloseCircleFilled,
  LoadingOutlined,
  ClockCircleOutlined,
} from "@ant-design/icons";
import { useStockAnalysisStore } from "../../store/stockAnalysisStore";
import { AGENT_DISPLAY_NAMES, AGENT_PROFILES, ANALYSIS_PHASE_LABELS } from "../../domain/constants";
import { AnalysisMode } from "../../domain/types";

const { Text } = Typography;

const PHASE_ICONS: Record<string, React.ReactNode> = {
  analysts: <StockOutlined />,
  debate: <SwapOutlined />,
  trader: <DollarOutlined />,
  risk: <SafetyCertificateOutlined />,
};

const PHASE_ORDER_FULL = ["analysts", "debate", "trader", "risk"];
const PHASE_ORDER_QUICK = ["analysts"];

const AGENTS_BY_PHASE_FULL: Record<string, string[]> = {
  analysts: ["market_analyst", "fundamentals_analyst", "news_analyst", "sentiment_analyst"],
  debate: ["bull_researcher", "bear_researcher", "research_manager"],
  trader: ["trader"],
  risk: ["risky_debator", "safe_debator", "neutral_debator", "risk_judge"],
};

const AGENTS_BY_PHASE_QUICK: Record<string, string[]> = {
  analysts: ["market_analyst", "fundamentals_analyst"],
};

/** 统一状态图标 */
const STATUS_ICONS: Record<string, { icon: React.ReactNode; color: string }> = {
  pending: { icon: <ClockCircleOutlined style={{ fontSize: 12 }} />, color: "#94a3b8" },
  running: { icon: <LoadingOutlined style={{ fontSize: 12 }} spin />, color: "#3b82f6" },
  done: { icon: <CheckCircleFilled style={{ fontSize: 12 }} />, color: "#15be53" },
  failed: { icon: <CloseCircleFilled style={{ fontSize: 12 }} />, color: "#ea2261" },
};

/** 格式化完成时间戳为 HH:mm */
const formatTime = (ts: number) => {
  const d = new Date(ts);
  return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
};

/** Agent 角色头像：圆形彩色背景 + emoji */
const AgentAvatar: React.FC<{ agent: string; status: string }> = ({ agent, status }) => {
  const profile = AGENT_PROFILES[agent];
  const size = 28;
  const isRunning = status === "running";
  return (
    <div
      style={{
        width: size,
        height: size,
        borderRadius: "50%",
        background: status === "pending" ? "#f1f5f9" : profile?.bgColor || "#f1f5f9",
        border: `1.5px solid ${status === "pending" ? "#e2e8f0" : profile?.borderColor || "#e2e8f0"}`,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontSize: 14,
        flexShrink: 0,
        opacity: status === "pending" ? 0.5 : status === "done" ? 0.75 : 1,
        transition: "all 0.3s ease",
        boxShadow: isRunning ? `0 0 0 3px ${profile?.bgColor || "#f0efff"}` : "none",
        animation: isRunning ? "agentBreath 2s ease-in-out infinite" : "none",
      }}
    >
      {profile?.emoji || "\u{1F916}"}
    </div>
  );
};

const AgentProgressPanel: React.FC = () => {
  const { agentStatuses, agentCompletedAt, currentPhase, analysisMode } = useStockAnalysisStore();

  const isQuick = analysisMode === AnalysisMode.QUICK;
  const phaseOrder = isQuick ? PHASE_ORDER_QUICK : PHASE_ORDER_FULL;
  const agentsByPhase = isQuick ? AGENTS_BY_PHASE_QUICK : AGENTS_BY_PHASE_FULL;

  return (
    <div style={{ padding: "4px 0" }}>
      {phaseOrder.map((phase, phaseIdx) => {
        const agents = agentsByPhase[phase] || [];
        const isActive = currentPhase === phase;
        const allDone = agents.length > 0 && agents.every((a) => agentStatuses[a] === "done");

        return (
          <div
            key={phase}
            style={{
              marginBottom: 8,
              opacity: allDone ? 0.65 : 1,
              transition: "opacity 0.3s ease",
            }}
          >
            {/* 阶段标题 */}
            <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 6, paddingLeft: 4 }}>
              <span style={{
                color: isActive ? "#533afd" : allDone ? "#15be53" : "#94a3b8",
                fontSize: 13,
                transition: "color 0.3s ease",
              }}>
                {PHASE_ICONS[phase]}
              </span>
              <Text style={{
                fontSize: 12,
                fontWeight: isActive ? 500 : 400,
                color: isActive ? "#533afd" : allDone ? "#15be53" : "#94a3b8",
                transition: "color 0.3s ease",
              }}>
                {ANALYSIS_PHASE_LABELS[phase]}
              </Text>
              {allDone && (
                <CheckCircleFilled style={{ fontSize: 10, color: "#15be53", marginLeft: 2 }} />
              )}
            </div>

            {/* Agent 列表 — 带连接线 */}
            <div style={{ display: "flex", flexDirection: "column", gap: 0 }}>
              {agents.map((agent, agentIdx) => {
                const status = agentStatuses[agent] || "pending";
                const profile = AGENT_PROFILES[agent];
                const isRunning = status === "running";
                const isDone = status === "done";
                const isFailed = status === "failed";
                const completedAt = agentCompletedAt[agent];
                const statusIcon = STATUS_ICONS[status] || STATUS_ICONS.pending;
                const isLast = agentIdx === agents.length - 1;

                return (
                  <div key={agent} style={{ position: "relative" }}>
                    {/* 左侧连接线 */}
                    {!isLast && (
                      <div style={{
                        position: "absolute",
                        left: 19,
                        top: 34,
                        bottom: 0,
                        width: 1,
                        background: isDone ? "#bbf7d0" : isRunning ? "#bfdbfe" : "#e5edf5",
                        transition: "background 0.3s ease",
                        zIndex: 0,
                      }} />
                    )}

                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 8,
                        padding: "6px 8px",
                        borderRadius: 6,
                        background: isRunning ? (profile?.bgColor || "#f0efff") : "transparent",
                        border: isRunning ? `1px solid ${profile?.borderColor || "#d6d9fc"}` : "1px solid transparent",
                        transition: "all 0.3s ease",
                        position: "relative",
                        zIndex: 1,
                      }}
                    >
                      <AgentAvatar agent={agent} status={status} />
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <Text style={{
                          fontSize: 12,
                          fontWeight: isRunning ? 500 : 400,
                          color: isRunning ? (profile?.color || "#533afd") : isDone ? "#64748d" : isFailed ? "#ea2261" : "#94a3b8",
                          display: "block",
                          transition: "color 0.3s ease",
                        }}>
                          {AGENT_DISPLAY_NAMES[agent] || agent}
                        </Text>

                        {/* 统一状态文案 + 图标 */}
                        <Text style={{
                          fontSize: 11,
                          color: statusIcon.color,
                          display: "flex",
                          alignItems: "center",
                          gap: 4,
                          marginTop: 2,
                        }}>
                          {statusIcon.icon}
                          <span>
                            {status === "pending" && "就绪"}
                            {status === "running" && "分析中"}
                            {status === "done" && `已完成${completedAt ? ` ${formatTime(completedAt)}` : ""}`}
                            {status === "failed" && `失败${completedAt ? ` ${formatTime(completedAt)}` : ""}`}
                          </span>
                        </Text>
                      </div>

                      {/* Running 态：呼吸脉冲点 */}
                      {isRunning && (
                        <div
                          style={{
                            width: 6,
                            height: 6,
                            borderRadius: "50%",
                            background: profile?.color || "#533afd",
                            animation: "agentPulse 1.5s ease-in-out infinite",
                            flexShrink: 0,
                          }}
                        />
                      )}
                    </div>
                  </div>
                );
              })}
            </div>

            {/* 阶段间分隔线（非最后一个阶段） */}
            {phaseIdx < phaseOrder.length - 1 && (
              <div style={{
                height: 1,
                background: "linear-gradient(to right, transparent, #e5edf5 20%, #e5edf5 80%, transparent)",
                margin: "8px 4px",
              }} />
            )}
          </div>
        );
      })}
    </div>
  );
};

export default AgentProgressPanel;
