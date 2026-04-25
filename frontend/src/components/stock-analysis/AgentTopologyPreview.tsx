import React from "react";
import { AnalysisMode } from "../../domain/types";

interface Props {
  analysisMode: AnalysisMode;
}

const NODES = [
  { key: "market", icon: "📊", name: "技术面分析师" },
  { key: "fundamentals", icon: "📈", name: "基本面分析师" },
  { key: "news", icon: "📰", name: "新闻舆情哨兵" },
  { key: "risk", icon: "🛡️", name: "风险评估官" },
];

const CONNECTION_LABELS = ["交叉辩论", "数据联动", "风控反馈"];

/** Agent 协作拓扑图预览 */
const AgentTopologyPreview: React.FC<Props> = ({ analysisMode }) => {
  const isFull = analysisMode === AnalysisMode.FULL;

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 0,
      }}
    >
      {NODES.map((node, idx) => {
        const active = isFull || idx < 2;

        return (
          <React.Fragment key={node.key}>
            {/* 节点 */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 10,
                padding: "10px 20px",
                borderRadius: 10,
                border: active
                  ? `1.5px solid ${isFull ? "#4096ff" : "#d9d9d9"}`
                  : "1.5px solid #f0f0f0",
                background: active
                  ? isFull
                    ? "linear-gradient(135deg, #e6f4ff 0%, #f0f5ff 100%)"
                    : "#fafafa"
                  : "#fafafa",
                opacity: active ? 1 : 0.4,
                transition: "all 0.3s ease",
                minWidth: 180,
                justifyContent: "center",
                boxShadow: isFull && active
                  ? "0 0 12px rgba(64, 150, 255, 0.15)"
                  : "none",
              }}
            >
              <span style={{ fontSize: 20 }}>{node.icon}</span>
              <span
                style={{
                  fontSize: 14,
                  fontWeight: active ? 500 : 400,
                  color: active ? "#333" : "#bfbfbf",
                }}
              >
                {node.name}
              </span>
            </div>

            {/* 连接线+标签 */}
            {idx < NODES.length - 1 && (
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  height: 32,
                  justifyContent: "center",
                }}
              >
                <div
                  style={{
                    width: 1,
                    height: 12,
                    borderLeft: "2px dashed",
                    borderColor: active ? "#91caff" : "#f0f0f0",
                  }}
                />
                <span
                  style={{
                    fontSize: 10,
                    color: active ? "#8c8c8c" : "#d9d9d9",
                    lineHeight: "14px",
                  }}
                >
                  {CONNECTION_LABELS[idx]}
                </span>
                <div
                  style={{
                    width: 1,
                    height: 12,
                    borderLeft: "2px dashed",
                    borderColor: active ? "#91caff" : "#f0f0f0",
                  }}
                />
              </div>
            )}
          </React.Fragment>
        );
      })}

      {/* 模式说明 */}
      <div
        style={{
          marginTop: 16,
          padding: "10px 16px",
          background: isFull ? "#f0f5ff" : "#f6f6f6",
          borderRadius: 8,
          fontSize: 12,
          color: "#8c8c8c",
          textAlign: "center",
          lineHeight: 1.8,
          maxWidth: 280,
        }}
      >
        {isFull ? (
          <>
            深度分析将调动 <b style={{ color: "#4096ff" }}>4位</b> AI 分析师
            <br />
            经过多空辩论与风险评估
            <br />
            预计 <b>3-5分钟</b> 产出完整报告
          </>
        ) : (
          <>
            快速分析由技术面与基本面
            <br />
            <b style={{ color: "#4096ff" }}>2位</b> 分析师协作
            <br />
            约 <b>30-60秒</b> 完成
          </>
        )}
      </div>
    </div>
  );
};

export default AgentTopologyPreview;
