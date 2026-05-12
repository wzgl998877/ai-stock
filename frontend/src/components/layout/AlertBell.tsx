/** 铃铛预警图标组件 */

import React, { useEffect, useState, useCallback } from "react";
import { Badge, Tooltip } from "antd";
import { BellOutlined } from "@ant-design/icons";
import { eventRadarService } from "../../services/eventRadarService";
import AlertDrawer from "../event-radar/AlertDrawer";

const AlertBell: React.FC = () => {
  const [unreadCount, setUnreadCount] = useState(0);
  const [drawerVisible, setDrawerVisible] = useState(false);

  const fetchCount = useCallback(async () => {
    try {
      const data = await eventRadarService.getUnreadCount();
      setUnreadCount(data.count || 0);
    } catch {
      // 静默失败
    }
  }, []);

  useEffect(() => {
    fetchCount();
    const timer = setInterval(fetchCount, 60000);
    return () => clearInterval(timer);
  }, [fetchCount]);

  return (
    <>
      <Tooltip title="影响预警" placement="bottom">
        <Badge count={unreadCount} overflowCount={5} offset={[0, 0]}>
          <BellOutlined
            onClick={() => setDrawerVisible(true)}
            style={{
              fontSize: 18,
              color: unreadCount > 0 ? "#533afd" : "#64748d",
              cursor: "pointer",
              padding: 6,
              borderRadius: 6,
              transition: "color 0.2s, background 0.2s",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.color = "#533afd";
              e.currentTarget.style.background = "#f6f9fc";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.color = unreadCount > 0 ? "#533afd" : "#64748d";
              e.currentTarget.style.background = "transparent";
            }}
          />
        </Badge>
      </Tooltip>

      <AlertDrawer
        visible={drawerVisible}
        onClose={() => setDrawerVisible(false)}
        onViewDetail={() => {
          setDrawerVisible(false);
        }}
        onMarkRead={fetchCount}
      />
    </>
  );
};

export default AlertBell;
