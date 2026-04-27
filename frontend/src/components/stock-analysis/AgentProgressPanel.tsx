import React from "react";
import { Typography, Tag } from "antd";
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

const formatTime = (ts: number) => {
  const d = new Date(ts);
  return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
};

/** 线段颜色 */
const lineColor = (isDone: boolean, isRunning: boolean) =>
  isDone ? "#15be53" : isRunning ? "#3b82f6" : "#e5e7eb";

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
        const isLastPhase = phaseIdx === phaseOrder.length - 1;

        return (
          <div key={phase} style={{ marginBottom: isLastPhase ? 0 : 8 }}>
            {/* ---- 阶段标题 ---- */}
            <div style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              padding: "8px 10px",
              borderRadius: 6,
              background: isActive ? "#f0f0ff" : allDone ? "#f0fdf4" : "transparent",
              marginBottom: 4,
            }}>
              <span style={{ color: isActive ? "#533afd" : allDone ? "#15803d" : "#b0b0b0", fontSize: 16 }}>
                {PHASE_ICONS[phase]}
              </span>
              <Text style={{
                fontSize: 14,
                fontWeight: isActive || allDone ? 600 : 400,
                color: isActive ? "#533afd" : allDone ? "#15803d" : "#b0b0b0",
              }}>
                {ANALYSIS_PHASE_LABELS[phase]}
              </Text>
              {allDone && (
                <Tag style={{
                  fontSize: 11, borderRadius: 4,
                  background: "#dcfce7", border: "1px solid #bbf7d0", color: "#15803d",
                  margin: 0, marginLeft: "auto", padding: "0 8px", lineHeight: "20px",
                }}>
                  完成
                </Tag>
              )}
              {isActive && !allDone && (
                <div style={{
                  width: 8, height: 8, borderRadius: "50%",
                  background: "#533afd", marginLeft: "auto",
                  animation: "agentPulse 1.5s ease-in-out infinite",
                }} />
              )}
            </div>

            {/* ---- Agent 列表（轨道 + 圆点） ---- */}
            {agents.map((agent, i) => {
              const status = agentStatuses[agent] || "pending";
              const profile = AGENT_PROFILES[agent];
              const isRunning = status === "running";
              const isDone = status === "done";
              const isFailed = status === "failed";
              const isPending = status === "pending";
              const isFirst = i === 0;
              const isLast = i === agents.length - 1;
              const completedAt = agentCompletedAt[agent];

              const lc = lineColor(isDone, isRunning);

              return (
                <div key={agent} style={{ display: "flex", alignItems: "stretch" }}>
                  {/* 左列：轨道线 + 圆点 */}
                  <div style={{
                    width: 32,
                    flexShrink: 0,
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                  }}>
                    {/* 上半段线 */}
                    {!isFirst && (
                      <div style={{ width: 2, height: 12, background: lc, borderRadius: 1 }} />
                    )}
                    {isFirst && <div style={{ height: 8 }} />}

                    {/* 圆点 */}
                    <div style={{
                      width: isRunning ? 12 : isDone ? 11 : 9,
                      height: isRunning ? 12 : isDone ? 11 : 9,
                      borderRadius: "50%",
                      background: isDone ? "#15be53" : isRunning ? "#3b82f6" : isFailed ? "#ea2261" : "#d1d5db",
                      border: isRunning ? "2px solid #dbeafe" : "none",
                      flexShrink: 0,
                      animation: isRunning ? "agentPulse 1.5s ease-in-out infinite" : "none",
                      transition: "all 0.3s ease",
                    }} />

                    {/* 下半段线 */}
                    {!isLast && (
                      <div style={{ width: 2, flex: 1, background: lc, borderRadius: 1 }} />
                    )}
                  </div>

                  {/* 右列：内容 */}
                  <div style={{
                    flex: 1,
                    minWidth: 0,
                    padding: `${isFirst ? 2 : 6}px 8px ${isLast ? 6 : 2}px`,
                    marginBottom: 4,
                    borderRadius: 8,
                    background: isRunning
                      ? `linear-gradient(135deg, ${profile?.bgColor || "#f0efff"} 0%, #fff 100%)`
                      : "transparent",
                    border: isRunning ? `1px solid ${profile?.borderColor || "#d6d9fc"}` : "1px solid transparent",
                    transition: "all 0.3s ease",
                  }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <span style={{ fontSize: 16 }}>{profile?.emoji || "🤖"}</span>
                      <Text style={{
                        fontSize: 14,
                        fontWeight: isRunning ? 600 : isDone ? 500 : 400,
                        color: isRunning
                          ? (profile?.color || "#3b82f6")
                          : isDone ? "#15803d"
                          : isFailed ? "#dc2626"
                          : "#9ca3af",
                      }}>
                        {AGENT_DISPLAY_NAMES[agent] || agent}
                      </Text>
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: 5, marginTop: 3, paddingLeft: 24 }}>
                      {isRunning && <LoadingOutlined style={{ fontSize: 13, color: "#3b82f6" }} spin />}
                      {isDone && <CheckCircleFilled style={{ fontSize: 13, color: "#15be53" }} />}
                      {isPending && <ClockCircleOutlined style={{ fontSize: 13, color: "#d1d5db" }} />}
                      {isFailed && <CloseCircleFilled style={{ fontSize: 13, color: "#ea2261" }} />}
                      <Text style={{
                        fontSize: 12,
                        fontWeight: isRunning ? 500 : 400,
                        color: isRunning ? "#3b82f6" : isDone ? "#16a34a" : isFailed ? "#dc2626" : "#c6c6c6",
                      }}>
                        {isRunning && "分析中..."}
                        {isDone && (completedAt ? formatTime(completedAt) : "完成")}
                        {isPending && "等待中"}
                        {isFailed && "失败"}
                      </Text>
                    </div>
                  </div>
                </div>
              );
            })}

            {/* 阶段间分隔 */}
            {!isLastPhase && (
              <div style={{
                height: 1,
                margin: "6px 8px",
                background: allDone
                  ? "linear-gradient(90deg, transparent, #86efac 30%, #86efac 70%, transparent)"
                  : "#e5e7eb",
                opacity: allDone ? 0.8 : 0.4,
              }} />
            )}
          </div>
        );
      })}
    </div>
  );
};

export default AgentProgressPanel;
