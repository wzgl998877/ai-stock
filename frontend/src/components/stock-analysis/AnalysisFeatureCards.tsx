import React, { useState } from "react";
import { Typography } from "antd";
import {
  StockOutlined,
  FundOutlined,
  SwapOutlined,
  SafetyCertificateOutlined,
} from "@ant-design/icons";

const { Text } = Typography;

const FEATURES = [
  {
    icon: <StockOutlined />,
    title: "技术面分析",
    desc: "K线形态、均线趋势、量价关系",
    color: "#3b82f6",
    bg: "#eff6ff",
  },
  {
    icon: <FundOutlined />,
    title: "基本面分析",
    desc: "财务指标、估值水平、盈利能力",
    color: "#15be53",
    bg: "#f0fdf4",
  },
  {
    icon: <SwapOutlined />,
    title: "多空辩论",
    desc: "看多看空双方论证，避免单一偏见",
    color: "#f59e0b",
    bg: "#fffbeb",
  },
  {
    icon: <SafetyCertificateOutlined />,
    title: "风险评估",
    desc: "激进/保守/中立三维风险评价",
    color: "#a855f7",
    bg: "#faf5ff",
  },
];

const FeatureCard: React.FC<{
  icon: React.ReactNode;
  title: string;
  desc: string;
  color: string;
  bg: string;
}> = ({ icon, title, desc, color, bg }) => {
  const [hovered, setHovered] = useState(false);

  return (
    <div
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        flex: 1,
        minWidth: 120,
        background: hovered ? bg : "#fafbfc",
        border: `1px solid ${hovered ? "#b9b9f9" : "#e5edf5"}`,
        borderRadius: 6,
        padding: "20px 16px",
        textAlign: "center",
        cursor: "default",
        transition: "all 0.25s ease",
        transform: hovered ? "translateY(-1px)" : "none",
        boxShadow: hovered ? "0 4px 16px rgba(83,58,253,0.08)" : "none",
      }}
    >
      <div style={{ color, fontSize: 24, marginBottom: 8 }}>{icon}</div>
      <Text
        style={{
          display: "block",
          fontSize: 13,
          fontWeight: 400,
          color: "#061b31",
          marginBottom: 4,
          fontFeatureSettings: "'ss01' on",
        }}
      >
        {title}
      </Text>
      <Text
        style={{
          display: "block",
          fontSize: 11,
          color: "#64748d",
          lineHeight: 1.5,
          fontFeatureSettings: "'ss01' on",
        }}
      >
        {desc}
      </Text>
    </div>
  );
};

const AnalysisFeatureCards: React.FC = () => {
  return (
    <div style={{ display: "flex", gap: 12 }}>
      {FEATURES.map((f) => (
        <FeatureCard key={f.title} {...f} />
      ))}
    </div>
  );
};

export default AnalysisFeatureCards;
