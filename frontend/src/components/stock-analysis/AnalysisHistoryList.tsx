import React, { useEffect, useState } from "react";
import { Typography, Tag, Empty, Spin } from "antd";
import { ThunderboltOutlined, ExperimentOutlined } from "@ant-design/icons";
import { useNavigate, useSearchParams } from "react-router-dom";
import * as stockAnalysisService from "../../services/stockAnalysisService";
import type { AnalysisRecordListItem } from "../../domain/types";
import { toPercent } from "../../utils/textUtils";

const { Text } = Typography;

const ACTION_TAG_COLOR: Record<string, string> = {
  "买入": "#15be53",
  "卖出": "#ea2261",
  "持有": "#3b82f6",
  "观望": "#64748d",
};

const ACTION_TAG_BG: Record<string, string> = {
  "买入": "rgba(21,190,83,0.1)",
  "卖出": "rgba(234,34,97,0.1)",
  "持有": "rgba(59,130,246,0.1)",
  "观望": "rgba(100,116,141,0.1)",
};

interface AnalysisHistoryListProps {
  stockCode: string;
  onRefresh?: number;
}

const AnalysisHistoryList: React.FC<AnalysisHistoryListProps> = ({ stockCode, onRefresh }) => {
  const [items, setItems] = useState<AnalysisRecordListItem[]>([]);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  useEffect(() => {
    if (!stockCode) return;
    setLoading(true);
    stockAnalysisService
      .listAnalysisRecords({ stockCode, pageSize: 10 })
      .then((res) => {
        setItems(res.items || []);
      })
      .catch(() => setItems([]))
      .finally(() => setLoading(false));
  }, [stockCode, onRefresh]);

  if (loading) {
    return <Spin style={{ display: "block", margin: "20px auto" }} />;
  }

  if (items.length === 0) {
    return <Empty description="暂无历史分析记录" image={Empty.PRESENTED_IMAGE_SIMPLE} />;
  }

  const currentRecordId = searchParams.get("recordId");

  const handleClick = (id: string) => {
    navigate(`/stock-analysis?recordId=${id}`);
  };

  return (
    <div style={{ position: "relative", paddingLeft: 16 }}>
      {/* 时间线竖线 */}
      <div
        style={{
          position: "absolute",
          left: 5,
          top: 8,
          bottom: 8,
          width: 2,
          background: "linear-gradient(to bottom, #e2e8f0, #f1f5f9)",
          borderRadius: 1,
        }}
      />

      <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
        {items.map((item) => {
          const isCurrent = item.id === currentRecordId;
          return (
            <div
              key={item.id}
              onClick={() => handleClick(item.id)}
              style={{
                position: "relative",
                cursor: "pointer",
                padding: "8px 10px",
                borderRadius: 6,
                background: isCurrent ? "rgba(83,58,253,0.04)" : "transparent",
                border: isCurrent ? "1px solid rgba(83,58,253,0.12)" : "1px solid transparent",
                transition: "background 0.2s, border-color 0.2s",
              }}
              onMouseEnter={(e) => {
                if (!isCurrent) {
                  e.currentTarget.style.background = "rgba(0,0,0,0.02)";
                }
              }}
              onMouseLeave={(e) => {
                if (!isCurrent) {
                  e.currentTarget.style.background = "transparent";
                }
              }}
            >
              {/* 时间线圆点 */}
              <div
                style={{
                  position: "absolute",
                  left: -15,
                  top: 14,
                  width: 8,
                  height: 8,
                  borderRadius: 4,
                  background: isCurrent ? "#533afd" : "#cbd5e1",
                  border: isCurrent ? "2px solid rgba(83,58,253,0.3)" : "2px solid #fff",
                  boxShadow: isCurrent ? "0 0 0 2px rgba(83,58,253,0.15)" : "none",
                }}
              />

              {/* 第一行：日期 + 分析模式 */}
              <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 4 }}>
                <Text style={{ fontSize: 11, color: "#94a3b8", fontFeatureSettings: "'tnum'" }}>
                  {item.created_at?.slice(0, 16).replace("T", " ")}
                </Text>
                {item.analysis_mode === "quick" ? (
                  <Tag
                    icon={<ThunderboltOutlined />}
                    style={{
                      fontSize: 10,
                      lineHeight: "16px",
                      padding: "0 4px",
                      margin: 0,
                      borderRadius: 3,
                      color: "#f59e0b",
                      background: "rgba(245,158,11,0.08)",
                      border: "none",
                    }}
                  >
                    快速
                  </Tag>
                ) : (
                  <Tag
                    icon={<ExperimentOutlined />}
                    style={{
                      fontSize: 10,
                      lineHeight: "16px",
                      padding: "0 4px",
                      margin: 0,
                      borderRadius: 3,
                      color: "#533afd",
                      background: "rgba(83,58,253,0.08)",
                      border: "none",
                    }}
                  >
                    深度
                  </Tag>
                )}
              </div>

              {/* 第二行：标题 */}
              <Text
                style={{
                  fontSize: 13,
                  color: "#061b31",
                  display: "block",
                  marginBottom: 4,
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                }}
              >
                {item.title || `${item.stocks?.[0]?.name || ""}分析`}
              </Text>

              {/* 第三行：决策信息 */}
              {item.decision && (
                <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                  {item.decision.action && (
                    <span
                      style={{
                        fontSize: 11,
                        fontWeight: 500,
                        color: ACTION_TAG_COLOR[item.decision.action] || "#64748d",
                        background: ACTION_TAG_BG[item.decision.action] || "rgba(100,116,141,0.1)",
                        padding: "1px 6px",
                        borderRadius: 3,
                      }}
                    >
                      {item.decision.action}
                    </span>
                  )}
                  {item.decision.target_price > 0 && (
                    <Text style={{ fontSize: 11, color: "#273951", fontFeatureSettings: "'tnum'" }}>
                      目标 ¥{item.decision.target_price.toFixed(2)}
                    </Text>
                  )}
                  {item.decision.confidence > 0 && (
                    <Text style={{ fontSize: 11, color: "#64748d", fontFeatureSettings: "'tnum'" }}>
                      置信度 {toPercent(item.decision.confidence).toFixed(0)}%
                    </Text>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default AnalysisHistoryList;
