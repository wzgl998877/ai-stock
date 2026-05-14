/** 事件仪表盘 — 信息密度版 */

import React from "react";
import { Tooltip } from "antd";

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

const hexPoint = (cx: number, cy: number, r: number, i: number) => {
  const angle = ((i * 60) - 90) * Math.PI / 180;
  return `${cx + r * Math.cos(angle)},${cy + r * Math.sin(angle)}`;
};

const hexPoints = (cx: number, cy: number, r: number) =>
  Array.from({ length: 6 }, (_, i) => hexPoint(cx, cy, r, i)).join(" ");

const RADAR_LABELS = ["市场", "政策", "资金", "情绪", "基本面", "技术"];
const RADAR_DATA = [0.7, 0.5, 0.6, 0.8, 0.4, 0.3];

const ImpactStatsCard: React.FC<ImpactStatsCardProps> = ({ stats }) => {
  const sentiment = stats.today_positive > stats.today_negative
    ? { label: "偏多", dir: "▲", color: "#00A86B" }
    : stats.today_negative > stats.today_positive
    ? { label: "偏空", dir: "▼", color: "#E74C3C" }
    : { label: "中性", dir: "—", color: "#F39C12" };

  const dataPoints = RADAR_DATA.map((v, i) => hexPoint(100, 100, 70 * v, i)).join(" ");

  const statItems = [
    { label: "市场情绪", value: sentiment.label, suffix: sentiment.dir, color: sentiment.color },
    { label: "今日事件", value: stats.today_total, color: "#0f172a" },
    { label: "利好", value: stats.today_positive, color: "#00A86B" },
    { label: "利空", value: stats.today_negative, color: "#E74C3C" },
    { label: "涉及个股", value: stats.affected_stocks_count, color: "#0f172a" },
    { label: "本周累计", value: stats.week_total, color: "#2A6DFF" },
  ];

  return (
    <div style={{
      display: "flex",
      gap: 20,
      background: "#ffffff",
      borderRadius: 16,
      padding: "20px 24px",
      boxShadow: "0 1px 3px rgba(0,0,0,0.04), 0 1px 2px rgba(0,0,0,0.02)",
      marginBottom: 16,
    }}>
      {/* 左侧：统计卡片网格 */}
      <div style={{ flex: 1, display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12 }}>
        {statItems.map((item, i) => (
          <div key={i} style={{ padding: "12px 16px", background: "#F7F9FC", borderRadius: 12 }}>
            <div style={{ fontSize: 12, color: "#94a3b8", marginBottom: 4 }}>{item.label}</div>
            <div style={{ fontSize: 24, fontWeight: 600, color: item.color, lineHeight: 1.2 }}>
              {item.value}
              {item.suffix && <span style={{ fontSize: 14, marginLeft: 4 }}>{item.suffix}</span>}
            </div>
          </div>
        ))}
      </div>

      {/* 右侧：雷达图占位 */}
      <div style={{ width: 200, flexShrink: 0 }}>
        <div style={{ fontSize: 12, color: "#94a3b8", marginBottom: 8, textAlign: "center" }}>事件影响雷达</div>
        <Tooltip title="市场: 70% | 政策: 50% | 资金: 60% | 情绪: 80% | 基本面: 40% | 技术: 30%">
          <svg viewBox="0 0 200 200" style={{ width: "100%", height: "auto", cursor: "pointer" }}>
            {[0.3, 0.6, 0.9].map((scale, i) => (
              <polygon key={i} points={hexPoints(100, 100, 70 * scale)} fill="none" stroke="#e5edf5" strokeWidth="1" />
            ))}
            {Array.from({ length: 6 }).map((_, i) => {
              const angle = ((i * 60) - 90) * Math.PI / 180;
              return (
                <line key={i} x1={100} y1={100} x2={100 + 70 * Math.cos(angle)} y2={100 + 70 * Math.sin(angle)} stroke="#e5edf5" strokeWidth="1" />
              );
            })}
            <polygon points={dataPoints} fill="rgba(42,109,255,0.12)" stroke="#2A6DFF" strokeWidth="2" />
            {RADAR_DATA.map((v, i) => {
              const angle = ((i * 60) - 90) * Math.PI / 180;
              return <circle key={i} cx={100 + 70 * v * Math.cos(angle)} cy={100 + 70 * v * Math.sin(angle)} r="3" fill="#2A6DFF" />;
            })}
            {RADAR_LABELS.map((label, i) => {
              const angle = ((i * 60) - 90) * Math.PI / 180;
              return (
                <text key={i} x={100 + 90 * Math.cos(angle)} y={100 + 90 * Math.sin(angle)} textAnchor="middle" dominantBaseline="middle" fill="#94a3b8" fontSize="11">
                  {label}
                </text>
              );
            })}
          </svg>
        </Tooltip>
      </div>
    </div>
  );
};

export default ImpactStatsCard;
