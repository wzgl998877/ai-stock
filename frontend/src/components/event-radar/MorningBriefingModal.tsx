/** 晨报弹窗组件 */

import React from "react";
import { Modal, Typography, Card, Tag, List, Button } from "antd";
import { CalendarOutlined } from "@ant-design/icons";

const { Text, Paragraph } = Typography;

interface MorningBriefingModalProps {
  visible: boolean;
  briefing: any;
  onClose: () => void;
}

const MorningBriefingModal: React.FC<MorningBriefingModalProps> = ({
  visible,
  briefing,
  onClose,
}) => {
  if (!briefing) return null;

  const content = briefing.content || {};

  return (
    <Modal
      title={
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <CalendarOutlined />
          <span>今日影响晨报</span>
          <Text style={{ fontSize: 12, color: "#94a3b8" }}>
            {briefing.briefing_date}
          </Text>
        </div>
      }
      open={visible}
      onCancel={onClose}
      footer={[
        <Button key="close" onClick={onClose}>
          关闭
        </Button>,
        <Button key="action" type="primary" onClick={onClose}>
          开始今日分析
        </Button>,
      ]}
      width={600}
    >
      {/* AI 总结 */}
      {briefing.ai_summary && (
        <Card
          size="small"
          style={{
            marginBottom: 16,
            background: "linear-gradient(135deg, #f6f0ff 0%, #f0f4ff 100%)",
            border: "none",
          }}
        >
          <Paragraph style={{ margin: 0, fontSize: 14, fontWeight: 500 }}>
            {briefing.ai_summary}
          </Paragraph>
        </Card>
      )}

      {/* 影响事件列表 */}
      {content.impact_events?.length > 0 && (
        <div style={{ marginBottom: 16 }}>
          <Text strong style={{ fontSize: 13, display: "block", marginBottom: 8 }}>
            影响事件
          </Text>
          <List
            size="small"
            dataSource={content.impact_events}
            renderItem={(event: any) => (
              <List.Item style={{ padding: "6px 0" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <Tag color={event.sentiment === "positive" ? "green" : event.sentiment === "negative" ? "red" : "default"}>
                    {event.sentiment === "positive" ? "利好" : event.sentiment === "negative" ? "利空" : "中性"}
                  </Tag>
                  <Text>{event.title}</Text>
                </div>
              </List.Item>
            )}
          />
        </div>
      )}

      {/* 自选股概览 */}
      {content.portfolio_overview?.length > 0 && (
        <div style={{ marginBottom: 16 }}>
          <Text strong style={{ fontSize: 13, display: "block", marginBottom: 8 }}>
            自选股概览
          </Text>
          <List
            size="small"
            dataSource={content.portfolio_overview}
            renderItem={(stock: any) => (
              <List.Item style={{ padding: "6px 0" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <Text strong>{stock.name}</Text>
                  <Tag color={stock.direction === "positive" ? "green" : "red"}>
                    {stock.direction === "positive" ? "偏利好" : "偏利空"}
                  </Tag>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    {stock.news_count} 条相关
                  </Text>
                </div>
              </List.Item>
            )}
          />
        </div>
      )}

      {/* 今日关注 */}
      {content.today_focus?.length > 0 && (
        <div>
          <Text strong style={{ fontSize: 13, display: "block", marginBottom: 8 }}>
            今日关注
          </Text>
          <List
            size="small"
            dataSource={content.today_focus}
            renderItem={(item: any) => (
              <List.Item style={{ padding: "6px 0" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  {item.time && (
                    <Text style={{ fontSize: 12, color: "#533afd" }}>{item.time}</Text>
                  )}
                  <Text>{item.event}</Text>
                </div>
              </List.Item>
            )}
          />
        </div>
      )}

      <div style={{ marginTop: 16, padding: "8px 12px", background: "#f6f9fc", borderRadius: 6, textAlign: "center" }}>
        <Text style={{ fontSize: 12, color: "#98a2b3" }}>
          以上为 AI 分析参考，不构成投资建议
        </Text>
      </div>
    </Modal>
  );
};

export default MorningBriefingModal;
