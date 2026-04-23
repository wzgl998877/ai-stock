import React from "react";
import { Timeline, Typography, Spin } from "antd";
import { CheckCircleFilled, LoadingOutlined, CloseCircleFilled, StockOutlined, SwapOutlined, DollarOutlined, SafetyCertificateOutlined } from "@ant-design/icons";
import { useStockAnalysisStore } from "../../store/stockAnalysisStore";
import { AGENT_DISPLAY_NAMES, AGENT_PHASE_MAPPING, ANALYSIS_PHASE_LABELS } from "../../domain/constants";
import { AgentType } from "../../domain/types";

const { Text } = Typography;

const PHASE_ICONS: Record<string, React.ReactNode> = {
  analysts: <StockOutlined />,
  debate: <SwapOutlined />,
  trader: <DollarOutlined />,
  risk: <SafetyCertificateOutlined />,
};

const PHASE_ORDER = ["analysts", "debate", "trader", "risk"];

const AGENTS_BY_PHASE: Record<string, string[]> = {
  analysts: ["market_analyst", "fundamentals_analyst", "news_analyst", "sentiment_analyst"],
  debate: ["bull_researcher", "bear_researcher", "research_manager"],
  trader: ["trader"],
  risk: ["risky_debator", "safe_debator", "neutral_debator", "risk_judge"],
};

const AgentProgressPanel: React.FC = () => {
  const { agentStatuses, currentPhase } = useStockAnalysisStore();

  return (
    <div style={{ padding: "12px 0" }}>
      {PHASE_ORDER.map((phase) => {
        const agents = AGENTS_BY_PHASE[phase] || [];
        const isActive = currentPhase === phase;
        return (
          <div key={phase} style={{ marginBottom: 16 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8, paddingLeft: 4 }}>
              <span style={{ color: isActive ? "#533afd" : "#94a3b8", fontSize: 13 }}>{PHASE_ICONS[phase]}</span>
              <Text style={{ fontSize: 12, fontWeight: isActive ? 500 : 400, color: isActive ? "#533afd" : "#64748d" }}>
                {ANALYSIS_PHASE_LABELS[phase]}
              </Text>
            </div>
            <Timeline
              items={agents.map((agent) => {
                const status = agentStatuses[agent] || "pending";
                const isRunning = status === "running";
                return {
                  color: status === "done" ? "green" : status === "running" ? "#533afd" : status === "failed" ? "red" : "gray",
                  dot: status === "running" ? <LoadingOutlined style={{ fontSize: 14 }} spin /> : undefined,
                  children: (
                    <div style={{
                      padding: "4px 8px",
                      borderRadius: 4,
                      background: isRunning ? "#f0efff" : "transparent",
                      border: isRunning ? "1px solid #d6d9fc" : "1px solid transparent",
                    }}>
                      <Text style={{
                        fontSize: 12,
                        color: status === "running" ? "#533afd" : status === "done" ? "#15be53" : status === "failed" ? "#ea2261" : "#94a3b8",
                      }}>
                        {AGENT_DISPLAY_NAMES[agent] || agent}
                      </Text>
                    </div>
                  ),
                };
              })}
            />
          </div>
        );
      })}
    </div>
  );
};

export default AgentProgressPanel;
