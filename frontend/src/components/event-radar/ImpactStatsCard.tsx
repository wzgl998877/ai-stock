/** AI 市场监控状态栏 */

import React, { useEffect, useRef } from "react";

interface ImpactStatsCardProps {
  stats: {
    today_total: number;
    today_positive: number;
    today_negative: number;
    today_neutral: number;
    affected_stocks_count: number;
    week_total: number;
  };
}

const ImpactStatsCard: React.FC<ImpactStatsCardProps> = ({ stats }) => {
  const styleRef = useRef<HTMLStyleElement | null>(null);

  useEffect(() => {
    if (!document.getElementById("radar-pulse-style")) {
      const style = document.createElement("style");
      style.id = "radar-pulse-style";
      style.textContent = `
        @keyframes radarPulse {
          0%, 100% { opacity: 1; box-shadow: 0 0 0 0 rgba(99,102,241,0.3); }
          50% { opacity: 0.7; box-shadow: 0 0 0 6px rgba(99,102,241,0); }
        }
        @keyframes radarGradient {
          0% { background-position: 0% 0; }
          100% { background-position: 200% 0; }
        }
      `;
      document.head.appendChild(style);
      styleRef.current = style;
    }
    return () => {
      styleRef.current?.remove();
    };
  }, []);

  const sentiment = stats.today_positive > stats.today_negative
    ? { label: "偏多", dir: "▲", color: "#16a34a" }
    : stats.today_negative > stats.today_positive
    ? { label: "偏空", dir: "▼", color: "#dc2626" }
    : { label: "中性", dir: "—", color: "#64748b" };

  const items = [
    { label: "市场情绪", value: sentiment.label, dir: sentiment.dir, color: sentiment.color },
    { label: "今日影响", value: stats.today_total, unit: "事件", color: "#0f172a" },
    { label: "利好", value: stats.today_positive, color: "#16a34a", extra: { label: "利空", value: stats.today_negative, color: "#dc2626" } },
    { label: "涉及个股", value: stats.affected_stocks_count, color: "#0f172a" },
    { label: "本周累计", value: stats.week_total, color: "#6366f1" },
  ];

  return (
    <div style={{
      background: "linear-gradient(135deg, #f8faff 0%, #f0f4ff 100%)",
      border: "1px solid #e0e7ff",
      borderRadius: 8,
      padding: "12px 20px",
      display: "flex",
      alignItems: "center",
      gap: 24,
      marginBottom: 16,
      position: "relative",
      overflow: "hidden",
    }}>
      {/* Bottom gradient line */}
      <div style={{
        position: "absolute", bottom: 0, left: 0, right: 0, height: 2,
        background: "linear-gradient(90deg, #6366f1, #8b5cf6, #6366f1)",
        backgroundSize: "200% 100%",
        animation: "radarGradient 3s linear infinite",
      }} />

      {/* Pulse + AI label */}
      <div style={{ display: "flex", alignItems: "center", gap: 8, flexShrink: 0 }}>
        <div style={{
          width: 8, height: 8, borderRadius: "50%", background: "#6366f1",
          animation: "radarPulse 2s ease-in-out infinite",
        }} />
        <span style={{ color: "#6366f1", fontSize: 12, fontWeight: 600 }}>AI 监控中</span>
      </div>

      <div style={{ width: 1, height: 20, background: "#e0e7ff", flexShrink: 0 }} />

      {/* Stat items */}
      {items.map((item, i) => (
        <React.Fragment key={i}>
          <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13, whiteSpace: "nowrap" }}>
            <span style={{ color: "#64748b" }}>{item.label}</span>
            <span style={{ color: item.color, fontWeight: 600 }}>
              {item.value}{item.dir ? ` ${item.dir}` : ""}
            </span>
            {"unit" in item && item.unit && <span style={{ color: "#64748b" }}>{item.unit}</span>}
            {"extra" in item && item.extra && (
              <>
                <span style={{ color: "#94a3b8" }}>/</span>
                <span style={{ color: "#64748b" }}>{item.extra.label}</span>
                <span style={{ color: item.extra.color, fontWeight: 600 }}>{item.extra.value}</span>
              </>
            )}
          </div>
          {i < items.length - 1 && <div style={{ width: 1, height: 20, background: "#e0e7ff", flexShrink: 0 }} />}
        </React.Fragment>
      ))}
    </div>
  );
};

export default ImpactStatsCard;
