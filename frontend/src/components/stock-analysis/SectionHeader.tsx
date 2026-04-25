import React from "react";
import { Typography } from "antd";

const { Text } = Typography;

interface SectionHeaderProps {
  icon?: React.ReactNode;
  title: string;
  extra?: React.ReactNode;
}

const SectionHeader: React.FC<SectionHeaderProps> = ({ icon, title, extra }) => {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        paddingBottom: 8,
        marginBottom: 12,
        borderBottom: "1px solid #f6f9fc",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
        {icon && <span style={{ color: "#533afd", fontSize: 14 }}>{icon}</span>}
        <Text
          style={{
            fontSize: 13,
            fontWeight: 400,
            color: "#061b31",
            fontFeatureSettings: "'ss01' on",
          }}
        >
          {title}
        </Text>
      </div>
      {extra}
    </div>
  );
};

export default SectionHeader;
