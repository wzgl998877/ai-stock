/** AI 推演事件卡片 — 紧凑设计版 */

import React from "react";
import { Button, Tooltip } from "antd";
import { ThunderboltOutlined } from "@ant-design/icons";
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

const sentimentCfg: Record<string, { label: string; color: string; bg: string }> = {
  positive: { label: "利好", color: "#00A86B", bg: "rgba(0,168,107,0.1)" },
  negative: { label: "利空", color: "#E74C3C", bg: "rgba(231,76,60,0.1)" },
  neutral:  { label: "中性", color: "#F39C12", bg: "rgba(243,156,18,0.1)" },
};

const ImpactEventCard: React.FC<ImpactEventCardProps> = ({ impact, onViewDetail }) => {
  const navigate = useNavigate();
  const s = sentimentCfg[impact.sentiment || "neutral"] || sentimentCfg.neutral;
  const primaryStock = impact.matched_stocks?.[0];
  const primaryName = primaryStock?.name || primaryStock?.code || "";

  const handleQuickAnalysis = () => {
    const params = new URLSearchParams({
      eventTitle: impact.title,
      eventSummary: impact.summary || "",
      eventType: impact.event_type || "other",
    });
    navigate(`/analysis?${params.toString()}`);
  };

  const formatTime = (dateStr: string | null) => {
    if (!dateStr) return { short: "", full: "" };
    const d = new Date(dateStr);
    const now = new Date();
    const diffMin = Math.floor((now.getTime() - d.getTime()) / 60000);
    const full = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")} ${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
    if (diffMin < 60) return { short: `${diffMin}分钟前`, full };
    const diffHour = Math.floor(diffMin / 60);
    if (diffHour < 24) return { short: `${diffHour}小时前`, full };
    return { short: `${d.getMonth() + 1}月${d.getDate()}日`, full };
  };

  const time = formatTime(impact.first_seen_at);

  const aiVerdict =
    impact.sentiment === "positive"
      ? "可能推动上涨"
      : impact.sentiment === "negative"
      ? "关注下行风险"
      : "影响有限，持续观察";

  return (
    <div
      style={{
        background: "#ffffff",
        borderRadius: 16,
        padding: "16px 20px",
        boxShadow: "0 1px 3px rgba(0,0,0,0.04), 0 1px 2px rgba(0,0,0,0.02)",
        cursor: "pointer",
        transition: "all 0.25s ease",
        display: "flex",
        gap: 16,
      }}
      onClick={() => onViewDetail(impact.id)}
      onMouseEnter={(e) => {
        const el = e.currentTarget as HTMLDivElement;
        el.style.transform = "translateY(-2px)";
        el.style.boxShadow = "0 8px 24px rgba(0,0,0,0.08), 0 2px 8px rgba(0,0,0,0.04)";
      }}
      onMouseLeave={(e) => {
        const el = e.currentTarget as HTMLDivElement;
        el.style.transform = "none";
        el.style.boxShadow = "0 1px 3px rgba(0,0,0,0.04), 0 1px 2px rgba(0,0,0,0.02)";
      }}
    >
      {/* 左侧：主内容 */}
      <div style={{ flex: 1, minWidth: 0 }}>
        {/* 第一行：股票 + 标签 + 时间 */}
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
          {primaryStock && (
            <span style={{ fontWeight: 600, fontSize: 14, color: "#0f172a", whiteSpace: "nowrap" }}>
              {primaryName}{" "}
              {primaryStock.name && (
                <span style={{ fontWeight: 400, color: "#94a3b8", fontSize: 12 }}>{primaryStock.code}</span>
              )}
              {impact.matched_stocks.length > 1 && (
                <span style={{ fontWeight: 400, color: "#2A6DFF", fontSize: 12, marginLeft: 4 }}>
                  +{impact.matched_stocks.length - 1}
                </span>
              )}
            </span>
          )}
          <span
            style={{
              padding: "2px 10px",
              borderRadius: 12,
              fontSize: 12,
              fontWeight: 500,
              background: s.bg,
              color: s.color,
              whiteSpace: "nowrap",
            }}
          >
            {s.label}
          </span>
          {impact.has_related_analysis && (
            <span style={{ padding: "2px 8px", borderRadius: 12, fontSize: 11, fontWeight: 500, background: "rgba(42,109,255,0.08)", color: "#2A6DFF", whiteSpace: "nowrap" }}>
              已分析
            </span>
          )}
          <span style={{ marginLeft: "auto", flexShrink: 0 }}>
            <Tooltip title={time.full}>
              <span style={{ fontSize: 12, color: "#94a3b8", whiteSpace: "nowrap", cursor: "default" }}>
                {time.short}
              </span>
            </Tooltip>
          </span>
        </div>

        {/* 第二行：标题（单行截断，悬浮显示全文） */}
        <Tooltip title={impact.title.length > 40 ? impact.title : undefined}>
          <div
            style={{
              fontSize: 14,
              fontWeight: 600,
              color: "#0f172a",
              lineHeight: 1.5,
              marginBottom: impact.summary ? 4 : 8,
              whiteSpace: "nowrap",
              overflow: "hidden",
              textOverflow: "ellipsis",
            }}
          >
            {impact.title}
          </div>
        </Tooltip>

        {/* 第二行b：摘要 */}
        {impact.summary && (
          <div
            style={{
              fontSize: 13,
              color: "#64748b",
              lineHeight: 1.5,
              display: "-webkit-box",
              WebkitLineClamp: 2,
              WebkitBoxOrient: "vertical",
              overflow: "hidden",
              marginBottom: 8,
            }}
          >
            {impact.summary}
          </div>
        )}

        {/* 第三行：AI 判断 */}
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <span style={{ width: 8, height: 8, borderRadius: "50%", background: s.color, flexShrink: 0 }} />
          <span style={{ fontSize: 13, color: s.color, fontWeight: 500 }}>{aiVerdict}</span>
        </div>
      </div>

      {/* 右侧：操作按钮 */}
      <div style={{ display: "flex", flexDirection: "column", justifyContent: "center", flexShrink: 0 }}>
        <Button
          type="primary"
          size="small"
          icon={<ThunderboltOutlined />}
          onClick={(e) => { e.stopPropagation(); handleQuickAnalysis(); }}
          style={{ borderRadius: 8, background: "#2A6DFF", borderColor: "#2A6DFF", fontSize: 12 }}
        >
          深度分析
        </Button>
      </div>
    </div>
  );
};

export default ImpactEventCard;
