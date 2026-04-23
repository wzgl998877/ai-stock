/** AnalysisModeSelector -- 分析模式选择器 */

import React from "react";
import { Radio, Typography, Space, Tooltip } from "antd";
import { BulbOutlined, ThunderboltOutlined, QuestionCircleOutlined } from "@ant-design/icons";
import { ANALYSIS_MODE_OPTIONS } from "../../domain/constants";
import { useStockAnalysisStore } from "../../store/stockAnalysisStore";
import { AnalysisMode } from "../../domain/types";

const { Text } = Typography;

const MODE_TOOLTIPS: Record<string, string> = {
  quick: "仅运行技术面+基本面分析师，不包含辩论和风险评估环节",
  full: "运行4位分析师 + 看多看空辩论 + 交易决策 + 风险评估辩论",
};

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
              {opt.value === "quick" ? "快速分析" : "深度分析"}
              <Tooltip title={MODE_TOOLTIPS[opt.value] || ""}>
                <QuestionCircleOutlined style={{ fontSize: 11, color: "#94a3b8", marginLeft: 4 }} />
              </Tooltip>
            </Text>
            <Text
              style={{
                fontSize: 11,
                color: "#94a3b8",
                lineHeight: "16px",
              }}
            >
              {opt.value === "quick" ? "仅技术面+基本面，约30-60秒" : "4位分析师+辩论+风险评估，约3-5分钟"}
            </Text>
          </Space>
        </Radio.Button>
      ))}
    </Radio.Group>
  );
};

export default AnalysisModeSelector;
