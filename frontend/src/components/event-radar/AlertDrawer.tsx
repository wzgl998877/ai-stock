/** 预警 Drawer */

import React, { useEffect, useState } from "react";
import { Drawer, List, Tag, Button, Typography, Empty, message } from "antd";
import { eventRadarService } from "../../services/eventRadarService";

const { Text } = Typography;

interface AlertDrawerProps {
  visible: boolean;
  onClose: () => void;
  onViewDetail: (impactId: number) => void;
  onMarkRead: () => void;
}

const AlertDrawer: React.FC<AlertDrawerProps> = ({
  visible,
  onClose,
  onViewDetail,
  onMarkRead,
}) => {
  const [alerts, setAlerts] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (visible) {
      setLoading(true);
      eventRadarService
        .getAlerts()
        .then((data) => setAlerts(data.alerts || []))
        .catch(() => message.error("加载预警失败"))
        .finally(() => setLoading(false));
    }
  }, [visible]);

  const handleMarkRead = async (alertId: number) => {
    try {
      await eventRadarService.markAlertRead(alertId);
      setAlerts((prev) => prev.filter((a) => a.id !== alertId));
      onMarkRead();
    } catch {
      message.error("标记失败");
    }
  };

  const priorityColors: Record<string, string> = {
    P0: "red",
    P1: "orange",
  };

  return (
    <Drawer
      title="影响预警"
      placement="right"
      width={380}
      open={visible}
      onClose={onClose}
    >
      {alerts.length === 0 ? (
        <Empty description="暂无未读预警" />
      ) : (
        <List
          loading={loading}
          dataSource={alerts}
          renderItem={(alert) => (
            <List.Item
              key={alert.id}
              actions={[
                <Button
                  size="small"
                  type="link"
                  onClick={() => {
                    onClose();
                    onViewDetail(alert.user_impact_id);
                  }}
                >
                  查看
                </Button>,
                <Button
                  size="small"
                  type="link"
                  onClick={() => handleMarkRead(alert.id)}
                >
                  已读
                </Button>,
              ]}
            >
              <List.Item.Meta
                title={
                  <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <Tag color={priorityColors[alert.priority]} style={{ margin: 0 }}>
                      {alert.priority}
                    </Tag>
                    <Text style={{ fontSize: 13 }}>{alert.title}</Text>
                  </div>
                }
                description={
                  <Text style={{ fontSize: 12, color: "#94a3b8" }}>
                    {alert.summary}
                  </Text>
                }
              />
            </List.Item>
          )}
        />
      )}
    </Drawer>
  );
};

export default AlertDrawer;
