import React from "react";
import { AnalysisMode } from "../../domain/types";

interface Props {
  value: AnalysisMode;
  onChange: (mode: AnalysisMode) => void;
}

/** 模式选择卡片：快速/深度 */
const ModeSelectionCards: React.FC<Props> = ({ value, onChange }) => {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      {/* 快速分析 */}
      <div
        onClick={() => onChange(AnalysisMode.QUICK)}
        style={{
          padding: "14px 16px",
          borderRadius: 10,
          border: `1.5px solid ${value === AnalysisMode.QUICK ? "#4096ff" : "#e8e8e8"}`,
          background: value === AnalysisMode.QUICK ? "#f0f5ff" : "#fff",
          cursor: "pointer",
          transition: "all 0.2s ease",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
          <span style={{ fontSize: 16 }}>⚡</span>
          <span style={{ fontWeight: 600, fontSize: 14, color: value === AnalysisMode.QUICK ? "#4096ff" : "#333" }}>
            快速分析
          </span>
        </div>
        <div style={{ fontSize: 12, color: "#8c8c8c", paddingLeft: 24 }}>
          2位分析师 · 约30-60秒
        </div>
      </div>

      {/* 深度分析 */}
      <div
        onClick={() => onChange(AnalysisMode.FULL)}
        style={{
          padding: "14px 16px",
          borderRadius: 10,
          border: `1.5px solid ${value === AnalysisMode.FULL ? "#4096ff" : "#e8e8e8"}`,
          background: value === AnalysisMode.FULL ? "#f0f5ff" : "#fff",
          cursor: "pointer",
          transition: "all 0.2s ease",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
          <span style={{ fontSize: 16 }}>🔬</span>
          <span style={{ fontWeight: 600, fontSize: 14, color: value === AnalysisMode.FULL ? "#4096ff" : "#333" }}>
            深度分析
          </span>
        </div>
        <div style={{ fontSize: 12, color: "#8c8c8c", paddingLeft: 24 }}>
          4位分析师+辩论+风评 · 约3-5分钟
        </div>
      </div>
    </div>
  );
};

export default ModeSelectionCards;
