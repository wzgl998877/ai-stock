/** 自选股影响列组件 */

import React from "react";
import { Tag, Popover, Typography, List } from "antd";

const { Text } = Typography;

interface WatchlistImpactColumnProps {
  impactCount: number;
  direction: string;
  recentImpacts: any[];
}

const WatchlistImpactColumn: React.FC<WatchlistImpactColumnProps> = ({
  impactCount,
  direction,
  recentImpacts,
}) => {
  if (impactCount === 0) {
    return <Text style={{ fontSize: 12, color: "#d1d5db" }}>-</Text>;
  }

  const colorMap: Record<string, string> = {
    positive: "green",
    negative: "red",
    neutral: "default",
  };

  const content = (
    <List
      size="small"
      dataSource={recentImpacts.slice(0, 5)}
      renderItem={(item: any) => (
        <List.Item style={{ padding: "4px 0", border: "none" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <Tag
              color={item.direction === "positive" ? "green" : item.direction === "negative" ? "red" : "default"}
              style={{ fontSize: 10, margin: 0 }}
            >
              {item.direction === "positive" ? "利好" : item.direction === "negative" ? "利空" : "中性"}
            </Tag>
            <Text style={{ fontSize: 12 }}>{item.event_title || "影响事件"}</Text>
          </div>
        </List.Item>
      )}
    />
  );

  return (
    <Popover content={content} title="近期影响事件" trigger="hover">
      <Tag
        color={colorMap[direction] || "default"}
        style={{ cursor: "pointer", fontSize: 11 }}
      >
        {impactCount} 条影响
      </Tag>
    </Popover>
  );
};

export default WatchlistImpactColumn;
