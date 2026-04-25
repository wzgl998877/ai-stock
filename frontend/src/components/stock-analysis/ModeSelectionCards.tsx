import React from "react";
import { ThunderboltOutlined, ExperimentOutlined } from "@ant-design/icons";
import { AnalysisMode } from "../../domain/types";

interface Props {
  value: AnalysisMode;
  onChange: (mode: AnalysisMode) => void;
}

/** 模式选择卡片：快速/深度 */
const ModeSelectionCards: React.FC<Props> = ({ value, onChange }) => {
  return (
    <div style={{ display: "flex", gap: 12 }}>
      {/* 快速分析 */}
      <div
        onClick={() => onChange(AnalysisMode.QUICK)}
        style={{
          flex: 1,
          padding: "16px",
          borderRadius: 10,
          border: `1.5px solid ${value === AnalysisMode.QUICK ? "#533afd" : "#e8e8e8"}`,
          background: value === AnalysisMode.QUICK ? "#f8f7ff" : "#fff",
          cursor: "pointer",
          transition: "all 0.2s ease",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
          <div
            style={{
              width: 32,
              height: 32,
              borderRadius: 8,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              background: value === AnalysisMode.QUICK ? "#533afd" : "#f5f5f5",
              color: value === AnalysisMode.QUICK ? "#fff" : "#8c8c8c",
              fontSize: 16,
              transition: "all 0.2s ease",
            }}
          >
            <ThunderboltOutlined />
          </div>
          <span style={{ fontWeight: 600, fontSize: 14, color: value === AnalysisMode.QUICK ? "#533afd" : "#333" }}>
            快速分析
          </span>
        </div>
        <div style={{ fontSize: 12, color: "#8c8c8c", lineHeight: 1.6 }}>
          2 位分析师 · 约30-60秒
        </div>
      </div>

      {/* 深度分析 */}
      <div
        onClick={() => onChange(AnalysisMode.FULL)}
        style={{
          flex: 1,
          padding: "16px",
          borderRadius: 10,
          border: `1.5px solid ${value === AnalysisMode.FULL ? "#533afd" : "#e8e8e8"}`,
          background: value === AnalysisMode.FULL ? "#f8f7ff" : "#fff",
          cursor: "pointer",
          transition: "all 0.2s ease",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
          <div
            style={{
              width: 32,
              height: 32,
              borderRadius: 8,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              background: value === AnalysisMode.FULL ? "#533afd" : "#f5f5f5",
              color: value === AnalysisMode.FULL ? "#fff" : "#8c8c8c",
              fontSize: 16,
              transition: "all 0.2s ease",
            }}
          >
            <ExperimentOutlined />
          </div>
          <span style={{ fontWeight: 600, fontSize: 14, color: value === AnalysisMode.FULL ? "#533afd" : "#333" }}>
            深度分析
          </span>
        </div>
        <div style={{ fontSize: 12, color: "#8c8c8c", lineHeight: 1.6 }}>
          4 位分析师 + 辩论 + 风评 · 约3-5分钟
        </div>
      </div>
    </div>
  );
};

export default ModeSelectionCards;
