import React from "react";
import { AnalysisMode } from "../../domain/types";
import {
  LineChartOutlined,
  FundOutlined,
  ReadOutlined,
  SafetyCertificateOutlined,
} from "@ant-design/icons";

interface Props {
  analysisMode: AnalysisMode;
}

const NODES = [
  { key: "market", icon: <LineChartOutlined />, name: "技术面分析师", color: "#3b82f6" },
  { key: "fundamentals", icon: <FundOutlined />, name: "基本面分析师", color: "#8b5cf6" },
  { key: "news", icon: <ReadOutlined />, name: "新闻舆情哨兵", color: "#f59e0b" },
  { key: "risk", icon: <SafetyCertificateOutlined />, name: "风险评估官", color: "#ef4444" },
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
        width: "100%",
        maxWidth: 400,
      }}
    >
      {NODES.map((node, idx) => {
        const active = isFull || idx < 2;

        return (
          <React.Fragment key={node.key}>
            {/* 节点卡片 */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 14,
                padding: "12px 24px",
                borderRadius: 10,
                width: "100%",
                maxWidth: 320,
                border: active
                  ? `1.5px solid ${isFull ? node.color + "40" : "#e0e0e0"}`
                  : "1.5px solid #f0f0f0",
                background: active
                  ? isFull
                    ? `linear-gradient(135deg, ${node.color}08 0%, ${node.color}03 100%)`
                    : "#fafafa"
                  : "#fafafa",
                opacity: active ? 1 : 0.35,
                transition: "all 0.3s ease",
                justifyContent: "flex-start",
                boxShadow: isFull && active
                  ? `0 0 16px ${node.color}12`
                  : "none",
              }}
            >
              {/* 图标圆 */}
              <div
                style={{
                  width: 36,
                  height: 36,
                  borderRadius: 8,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  background: active ? node.color + "15" : "#f0f0f0",
                  color: active ? node.color : "#d9d9d9",
                  fontSize: 18,
                  flexShrink: 0,
                  transition: "all 0.3s ease",
                }}
              >
                {node.icon}
              </div>
              <div>
                <span
                  style={{
                    fontSize: 14,
                    fontWeight: active ? 500 : 400,
                    color: active ? "#1f2937" : "#bfbfbf",
                    display: "block",
                    transition: "color 0.3s ease",
                  }}
                >
                  {node.name}
                </span>
                <span
                  style={{
                    fontSize: 11,
                    color: active ? "#8c8c8c" : "#d9d9d9",
                    transition: "color 0.3s ease",
                  }}
                >
                  {idx < 2 ? "阶段一" : idx === 2 ? "阶段三" : "阶段四"}
                </span>
              </div>

              {/* 右侧状态指示 */}
              {active && (
                <div style={{ marginLeft: "auto", flexShrink: 0 }}>
                  <div
                    style={{
                      width: 8,
                      height: 8,
                      borderRadius: "50%",
                      background: isFull ? node.color : "#d9d9d9",
                      transition: "background 0.3s ease",
                    }}
                  />
                </div>
              )}
            </div>

            {/* 连接线 + 标签 */}
            {idx < NODES.length - 1 && (
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  height: 36,
                  justifyContent: "center",
                }}
              >
                <div
                  style={{
                    width: 1,
                    height: 14,
                    borderLeft: `2px dashed ${active ? node.color + "50" : "#f0f0f0"}`,
                  }}
                />
                <span
                  style={{
                    fontSize: 10,
                    color: active ? "#a0a0a0" : "#e0e0e0",
                    lineHeight: "14px",
                  }}
                >
                  {CONNECTION_LABELS[idx]}
                </span>
                <div
                  style={{
                    width: 1,
                    height: 14,
                    borderLeft: `2px dashed ${active ? node.color + "50" : "#f0f0f0"}`,
                  }}
                />
              </div>
            )}
          </React.Fragment>
        );
      })}

      {/* 模式说明 — 底部摘要 */}
      <div
        style={{
          marginTop: 20,
          padding: "12px 20px",
          background: isFull ? "#f8f7ff" : "#f9f9f9",
          borderRadius: 8,
          fontSize: 12,
          color: "#8c8c8c",
          textAlign: "center",
          lineHeight: 1.8,
          width: "100%",
          maxWidth: 320,
          border: `1px solid ${isFull ? "#eee8ff" : "#f0f0f0"}`,
        }}
      >
        {isFull ? (
          <>
            深度分析将调动 <b style={{ color: "#533afd" }}>4位</b> AI 分析师
            经过多空辩论与风险评估，预计 <b>3-5分钟</b> 产出完整报告
          </>
        ) : (
          <>
            快速分析由技术面与基本面 <b style={{ color: "#533afd" }}>2位</b> 分析师协作
            约 <b>30-60秒</b> 完成
          </>
        )}
      </div>
    </div>
  );
};

export default AgentTopologyPreview;
