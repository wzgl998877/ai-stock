import React from "react";
import { Typography, Tag, Space } from "antd";
import { StockOutlined, ThunderboltOutlined } from "@ant-design/icons";
import { AnalysisMode } from "../../domain/types";

const { Text, Paragraph } = Typography;

interface SummaryCardProps {
  title: string;
  summary: string;
  industries: string[];
  stockName: string;
  stockCode: string;
  analysisMode: AnalysisMode;
  dataSource?: string;
}

const SummaryCard: React.FC<SummaryCardProps> = ({
  title,
  summary,
  industries,
  stockName,
  stockCode,
  analysisMode,
  dataSource,
}) => {
  return (
    <div
      style={{
        background: "#f8f7ff",
        border: "1px solid #e5edf5",
        borderLeft: "3px solid #533afd",
        borderRadius: 6,
        padding: "16px 20px",
      }}
    >
      {/* 标题行 */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10 }}>
        <Text
          style={{
            fontSize: 16,
            fontWeight: 400,
            color: "#061b31",
            fontFeatureSettings: "'ss01' on",
          }}
        >
          {title || `${stockName}(${stockCode})${analysisMode === AnalysisMode.QUICK ? "快速" : "深度"}分析`}
        </Text>
        <Space size={8}>
          <Tag
            icon={analysisMode === AnalysisMode.QUICK ? <ThunderboltOutlined /> : <StockOutlined />}
            style={{
              fontSize: 10,
              borderRadius: 4,
              background: "#f0efff",
              color: "#533afd",
              border: "1px solid #d6d9fc",
              margin: 0,
            }}
          >
            {analysisMode === AnalysisMode.QUICK ? "快速" : "深度"}
          </Tag>
          {dataSource && (
            <Tag
              style={{
                fontSize: 10,
                borderRadius: 4,
                background: "#f8fafc",
                color: "#64748d",
                border: "1px solid #e5edf5",
                margin: 0,
              }}
            >
              {dataSource}
            </Tag>
          )}
        </Space>
      </div>

      {/* 摘要 */}
      {summary && (
        <Paragraph
          style={{
            fontSize: 13,
            color: "#273951",
            lineHeight: 1.7,
            margin: 0,
            marginBottom: industries.length > 0 ? 10 : 0,
            fontFeatureSettings: "'ss01' on",
          }}
        >
          {summary}
        </Paragraph>
      )}

      {/* 行业标签 */}
      {industries.length > 0 && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
          {industries.map((ind) => (
            <Tag
              key={ind}
              style={{
                fontSize: 11,
                borderRadius: 4,
                background: "#ffffff",
                color: "#533afd",
                border: "1px solid #d6d9fc",
                margin: 0,
              }}
            >
              {ind}
            </Tag>
          ))}
        </div>
      )}
    </div>
  );
};

export default SummaryCard;
