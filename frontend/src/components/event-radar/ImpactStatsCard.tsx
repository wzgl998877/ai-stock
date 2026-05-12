/** 影响概览统计组件 */

import React from "react";
import { Card, Statistic, Row, Col } from "antd";
import {
  ArrowUpOutlined,
  ArrowDownOutlined,
  CalendarOutlined,
} from "@ant-design/icons";

interface ImpactStatsCardProps {
  stats: {
    today_total: number;
    today_positive: number;
    today_negative: number;
    today_neutral: number;
    affected_stocks_count: number;
    week_total: number;
  };
}

const ImpactStatsCard: React.FC<ImpactStatsCardProps> = ({ stats }) => {
  return (
    <Card
      size="small"
      style={{ borderRadius: 6, marginBottom: 16 }}
      bodyStyle={{ padding: "12px 20px" }}
    >
      <Row gutter={16}>
        <Col span={6}>
          <Statistic
            title={<span style={{ fontSize: 12, color: "#94a3b8" }}>今日影响</span>}
            value={stats.today_total}
            suffix="条"
            valueStyle={{ fontSize: 20, color: "#061b31" }}
          />
        </Col>
        <Col span={6}>
          <Statistic
            title={<span style={{ fontSize: 12, color: "#94a3b8" }}>利好</span>}
            value={stats.today_positive}
            prefix={<ArrowUpOutlined />}
            valueStyle={{ fontSize: 20, color: "#15be53" }}
          />
        </Col>
        <Col span={6}>
          <Statistic
            title={<span style={{ fontSize: 12, color: "#94a3b8" }}>利空</span>}
            value={stats.today_negative}
            prefix={<ArrowDownOutlined />}
            valueStyle={{ fontSize: 20, color: "#ea2261" }}
          />
        </Col>
        <Col span={6}>
          <Statistic
            title={<span style={{ fontSize: 12, color: "#94a3b8" }}>本周累计</span>}
            value={stats.week_total}
            prefix={<CalendarOutlined />}
            valueStyle={{ fontSize: 20, color: "#533afd" }}
          />
        </Col>
      </Row>
    </Card>
  );
};

export default ImpactStatsCard;
