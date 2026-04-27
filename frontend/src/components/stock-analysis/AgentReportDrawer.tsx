import React from "react";
import { Drawer, Typography, Tag, Empty } from "antd";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useStockAnalysisStore } from "../../store/stockAnalysisStore";
import { AGENT_DISPLAY_NAMES, AGENT_PROFILES } from "../../domain/constants";

const { Text } = Typography;

/** 状态图标与颜色映射 */
const STATUS_CONFIG: Record<string, { color: string; label: string }> = {
  running: { color: "#3b82f6", label: "分析中" },
  done: { color: "#15be53", label: "已完成" },
  failed: { color: "#ea2261", label: "失败" },
  pending: { color: "#94a3b8", label: "就绪" },
};

const AgentReportDrawer: React.FC = () => {
  const selectedAgent = useStockAnalysisStore((s) => s.selectedReportAgent);
  const agentFullReports = useStockAnalysisStore((s) => s.agentFullReports);
  const agentReports = useStockAnalysisStore((s) => s.agentReports);
  const agentStatuses = useStockAnalysisStore((s) => s.agentStatuses);
  const setSelectedReportAgent = useStockAnalysisStore((s) => s.setSelectedReportAgent);

  if (!selectedAgent) return null;

  const profile = AGENT_PROFILES[selectedAgent];
  const displayName = AGENT_DISPLAY_NAMES[selectedAgent] || selectedAgent;
  const fullReport = agentFullReports[selectedAgent];
  const summary = agentReports[selectedAgent] || "";
  const status = agentStatuses[selectedAgent] || "pending";
  const statusConfig = STATUS_CONFIG[status] || STATUS_CONFIG.pending;

  const hasFullReport = fullReport && fullReport !== summary;

  return (
    <Drawer
      title={null}
      placement="right"
      width={520}
      open={!!selectedAgent}
      onClose={() => setSelectedReportAgent(null)}
      styles={{
        header: { display: "none" },
        body: { padding: 0 },
      }}
    >
      {/* 头部 */}
      <div style={{
        padding: "20px 24px 16px",
        borderBottom: "1px solid #e5edf5",
        display: "flex",
        alignItems: "center",
        gap: 12,
      }}>
        <div style={{
          width: 40,
          height: 40,
          borderRadius: "50%",
          background: profile?.bgColor || "#f0efff",
          border: `1.5px solid ${profile?.borderColor || "#d6d9fc"}`,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: 20,
          flexShrink: 0,
        }}>
          {profile?.emoji || "🤖"}
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <Text style={{ fontSize: 15, fontWeight: 500, color: "#061b31" }}>{displayName}</Text>
          <div style={{ marginTop: 2 }}>
            <Tag style={{ fontSize: 11, borderRadius: 4, background: "#f8fafc", border: `1px solid ${statusConfig.color}33`, color: statusConfig.color }}>
              {statusConfig.label}
            </Tag>
          </div>
        </div>
      </div>

      {/* 主体内容 */}
      <div style={{ padding: "20px 24px" }}>
        {hasFullReport ? (
          <div className="markdown-body" style={{ fontSize: 13, lineHeight: 1.8 }}>
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{fullReport}</ReactMarkdown>
          </div>
        ) : summary ? (
          <div>
            <div className="markdown-body" style={{ fontSize: 13, lineHeight: 1.8 }}>
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{summary}</ReactMarkdown>
            </div>
            <div style={{ marginTop: 16, padding: "10px 12px", background: "#f8f7ff", borderRadius: 6, border: "1px solid #d6d9fc" }}>
              <Text style={{ fontSize: 12, color: "#64748d" }}>完整报告尚未生成</Text>
            </div>
          </div>
        ) : (
          <Empty description="暂无报告内容" />
        )}
      </div>
    </Drawer>
  );
};

export default AgentReportDrawer;
