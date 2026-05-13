/** AI 推演事件卡片 */

import React from "react";
import { Button } from "antd";
import {
  EyeOutlined,
  ThunderboltOutlined,
  CheckCircleOutlined,
} from "@ant-design/icons";
import { useNavigate } from "react-router-dom";

interface MatchedStock {
  code: string;
  name: string;
  direction: string;
  confidence: number;
}

interface ImpactEventCardProps {
  impact: {
    id: number;
    event_id: number;
    title: string;
    summary: string | null;
    event_type: string | null;
    sentiment: string | null;
    importance: string | null;
    source_count: number;
    matched_stocks: MatchedStock[];
    matched_industries?: { name: string; direction?: string }[];
    priority: string;
    is_read: boolean;
    has_related_analysis?: boolean;
    first_seen_at: string | null;
    source_name: string;
  };
  onViewDetail: (impactId: number) => void;
}

const sentimentCfg: Record<string, { label: string; color: string; tagBg: string; tagBorder: string }> = {
  positive: { label: "利好", color: "#16a34a", tagBg: "#f0fdf4", tagBorder: "#bbf7d0" },
  negative: { label: "利空", color: "#dc2626", tagBg: "#fef2f2", tagBorder: "#fecaca" },
  neutral:  { label: "中性", color: "#64748b", tagBg: "#f8fafc", tagBorder: "#e2e8f0" },
};

const priorityCfg: Record<string, { label: string; bg: string; color: string }> = {
  P0: { label: "紧急", bg: "#fef2f2", color: "#dc2626" },
  P1: { label: "重要", bg: "#fff7ed", color: "#ea580c" },
  P2: { label: "关注", bg: "#f0f0ff", color: "#6366f1" },
};

const ImpactEventCard: React.FC<ImpactEventCardProps> = ({ impact, onViewDetail }) => {
  const navigate = useNavigate();
  const s = sentimentCfg[impact.sentiment || "neutral"] || sentimentCfg.neutral;
  const p = priorityCfg[impact.priority] || priorityCfg.P2;

  const handleQuickAnalysis = () => {
    const params = new URLSearchParams({
      eventTitle: impact.title,
      eventSummary: impact.summary || "",
      eventType: impact.event_type || "other",
    });
    navigate(`/analysis?${params.toString()}`);
  };

  const formatTime = (dateStr: string | null) => {
    if (!dateStr) return "";
    const d = new Date(dateStr);
    const now = new Date();
    const diffMin = Math.floor((now.getTime() - d.getTime()) / 60000);
    if (diffMin < 60) return `${diffMin}分钟前`;
    const diffHour = Math.floor(diffMin / 60);
    if (diffHour < 24) return `${diffHour}小时前`;
    return `${d.getMonth() + 1}/${d.getDate()}`;
  };

  // Build inference chain from matched stocks + industries
  const inferenceSteps: string[] = [];
  if (impact.matched_stocks.length > 0) {
    impact.matched_stocks.slice(0, 3).forEach(st => {
      inferenceSteps.push(st.name || st.code);
    });
  }

  return (
    <div
      style={{
        background: "#ffffff",
        border: "1px solid #e5edf5",
        borderLeft: `3px solid ${s.color}`,
        borderRadius: 8,
        padding: "14px 18px",
        cursor: "pointer",
        transition: "all 0.25s",
        marginBottom: 8,
      }}
      onMouseEnter={(e) => {
        const el = e.currentTarget as HTMLDivElement;
        el.style.borderColor = "#cbd5e1";
        el.style.boxShadow = `0 2px 12px rgba(0,0,0,0.06)`;
        el.style.transform = "translateY(-1px)";
      }}
      onMouseLeave={(e) => {
        const el = e.currentTarget as HTMLDivElement;
        el.style.borderColor = "#e5edf5";
        el.style.boxShadow = "none";
        el.style.transform = "none";
      }}
    >
      {/* Header tags */}
      <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8, flexWrap: "wrap" }}>
        <span style={{ padding: "2px 8px", borderRadius: 4, fontSize: 11, fontWeight: 600, background: p.bg, color: p.color }}>
          {p.label}
        </span>
        <span style={{ padding: "2px 8px", borderRadius: 4, fontSize: 11, fontWeight: 600, background: s.tagBg, color: s.color, border: `1px solid ${s.tagBorder}` }}>
          {s.label}
        </span>
        {impact.source_count >= 3 && (
          <span style={{ padding: "2px 8px", borderRadius: 4, fontSize: 11, fontWeight: 600, background: "#fff7ed", color: "#ea580c" }}>
            热点
          </span>
        )}
        {impact.has_related_analysis && (
          <span style={{ padding: "2px 8px", borderRadius: 4, fontSize: 11, fontWeight: 600, background: "#f0f0ff", color: "#6366f1", display: "inline-flex", alignItems: "center", gap: 3 }}>
            <CheckCircleOutlined style={{ fontSize: 10 }} /> 已分析
          </span>
        )}
        <span style={{ fontSize: 12, color: "#94a3b8", marginLeft: "auto" }}>
          {formatTime(impact.first_seen_at)}
        </span>
      </div>

      {/* Title */}
      <div style={{ fontSize: 15, fontWeight: 600, color: "#0f172a", lineHeight: 1.5, marginBottom: 8 }}>
        {impact.title}
      </div>

      {/* AI Inference Chain */}
      {inferenceSteps.length > 0 && (
        <div style={{
          background: "linear-gradient(135deg, #f8faff, #f5f3ff)",
          border: "1px solid #e0e7ff",
          borderRadius: 6,
          padding: "10px 14px",
          marginBottom: 10,
        }}>
          <div style={{ fontSize: 11, color: "#6366f1", fontWeight: 600, marginBottom: 6, letterSpacing: "0.5px" }}>
            AI 影响路径
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 6, flexWrap: "wrap" }}>
            {inferenceSteps.map((step, i) => (
              <React.Fragment key={i}>
                {i > 0 && <span style={{ color: "#a5b4fc", fontSize: 12 }}>→</span>}
                <span style={{
                  fontSize: 13, color: "#4338ca", background: "#ffffff",
                  padding: "3px 10px", borderRadius: 4, border: "1px solid #e0e7ff",
                }}>
                  {step}
                </span>
              </React.Fragment>
            ))}
          </div>
        </div>
      )}

      {/* Matched stocks */}
      {impact.matched_stocks.length > 0 && (
        <div style={{ display: "flex", alignItems: "center", gap: 6, flexWrap: "wrap", marginBottom: 6 }}>
          <span style={{ fontSize: 12, color: "#94a3b8" }}>关联个股</span>
          {impact.matched_stocks.slice(0, 4).map((stock) => (
            <span
              key={stock.code}
              style={{
                padding: "2px 10px", borderRadius: 4, fontSize: 12, fontWeight: 500, cursor: "pointer",
                background: stock.direction === "negative" ? "#fef2f2" : "#f0fdf4",
                color: stock.direction === "negative" ? "#dc2626" : "#16a34a",
                border: `1px solid ${stock.direction === "negative" ? "#fecaca" : "#bbf7d0"}`,
              }}
            >
              {stock.name || stock.code}
              {stock.direction === "positive" ? " ▲" : stock.direction === "negative" ? " ▼" : ""}
            </span>
          ))}
        </div>
      )}

      {/* Matched industries */}
      {impact.matched_industries && impact.matched_industries.length > 0 && (
        <div style={{ display: "flex", alignItems: "center", gap: 6, flexWrap: "wrap", marginBottom: 6 }}>
          <span style={{ fontSize: 12, color: "#94a3b8" }}>关联板块</span>
          {impact.matched_industries.map((ind, i) => (
            <span
              key={i}
              style={{
                padding: "2px 10px", borderRadius: 4, fontSize: 12, fontWeight: 500,
                background: "#f0f0ff", color: "#6366f1", border: "1px solid #e0e7ff",
              }}
            >
              {ind.name}
            </span>
          ))}
        </div>
      )}

      {/* AI Judgment */}
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6, fontSize: 12 }}>
        <span style={{ color: "#6366f1", fontSize: 14 }}>◆</span>
        <span style={{ color: "#94a3b8" }}>AI 判断：</span>
        <span style={{ color: s.color, fontWeight: 600 }}>
          {s.label === "利好" ? "可能推动上涨" : s.label === "利空" ? "关注下行风险" : "影响有限，持续观察"}
        </span>
      </div>

      {/* Actions */}
      <div style={{ display: "flex", justifyContent: "flex-end", gap: 6, marginTop: 4 }}>
        <Button size="small" icon={<EyeOutlined />} onClick={(e) => { e.stopPropagation(); onViewDetail(impact.id); }}>
          查看详情
        </Button>
        <Button size="small" type="primary" icon={<ThunderboltOutlined />} onClick={(e) => { e.stopPropagation(); handleQuickAnalysis(); }}>
          一键分析
        </Button>
      </div>
    </div>
  );
};

export default ImpactEventCard;
