/** AnalysisModeSelector -- 分析模式选择器 */

import React from "react";
import { Radio, Typography, Space } from "antd";
import { BulbOutlined, ThunderboltOutlined } from "@ant-design/icons";
import { ANALYSIS_MODE_OPTIONS } from "../../domain/constants";
import { useStockAnalysisStore } from "../../store/stockAnalysisStore";

const { Text } = Typography;

const AnalysisModeSelector: React.FC = () => {
  const { analysisMode, setMode } = useStockAnalysisStore();

  return (
    <Radio.Group
      value={analysisMode}
      onChange={(e) => setMode(e.target.value)}
      style={{ display: "flex", gap: 12 }}
    >
      {ANALYSIS_MODE_OPTIONS.map((opt) => (
        <Radio.Button
          key={opt.value}
          value={opt.value}
          style={{
            borderRadius: 6,
            height: 56,
            display: "flex",
            alignItems: "center",
            padding: "0 20px",
            borderColor: analysisMode === opt.value ? "#533afd" : "#e5edf5",
            background: analysisMode === opt.value ? "#f0efff" : "#ffffff",
            transition: "all 0.2s",
          }}
        >
          <Space direction="vertical" size={0}>
            <Text
              style={{
                fontSize: 14,
                fontWeight: 400,
                color: analysisMode === opt.value ? "#533afd" : "#061b31",
                fontFeatureSettings: "'ss01' on",
                lineHeight: "20px",
              }}
            >
              {opt.value === "quick" ? (
                <ThunderboltOutlined style={{ marginRight: 4 }} />
              ) : (
                <BulbOutlined style={{ marginRight: 4 }} />
              )}
              {opt.label}
            </Text>
            <Text
              style={{
                fontSize: 11,
                color: "#94a3b8",
                lineHeight: "16px",
              }}
            >
              {opt.desc}
            </Text>
          </Space>
        </Radio.Button>
      ))}
    </Radio.Group>
  );
};

export default AnalysisModeSelector;
