/** 事件雷达主页面 */

import React, { useEffect, useState, useCallback, useRef } from "react";
import { Typography, Spin, Empty, Button, Segmented } from "antd";
import { SettingOutlined, SyncOutlined } from "@ant-design/icons";
import { useEventRadarStore } from "../store/eventRadarStore";
import { eventRadarService } from "../services/eventRadarService";
import ImpactEventCard from "../components/event-radar/ImpactEventCard";
import ImpactStatsCard from "../components/event-radar/ImpactStatsCard";
import EventDetailDrawer from "../components/event-radar/EventDetailDrawer";
import RadarConfigModal from "../components/event-radar/RadarConfigModal";

const { Title, Text } = Typography;

const EventRadarPage: React.FC = () => {
  const {
    activeImpacts,
    archivedImpacts,
    stats,
    loading,
    error,
    setActiveImpacts,
    setArchivedImpacts,
    setStats,
    setLoading,
    setError,
  } = useEventRadarStore();

  const [statusFilter, setStatusFilter] = useState<string>("active");
  const [detailVisible, setDetailVisible] = useState(false);
  const [selectedImpactId, setSelectedImpactId] = useState<number | null>(null);
  const [configVisible, setConfigVisible] = useState(false);
  const refreshTimer = useRef<ReturnType<typeof setInterval> | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await eventRadarService.getImpacts({ status: "all" });
      setActiveImpacts(data.active_impacts || []);
      setArchivedImpacts(data.archived_impacts || []);
      setStats(data.stats || {});
    } catch {
      setError("加载失败，请稍后重试");
    } finally {
      setLoading(false);
    }
  }, [setActiveImpacts, setArchivedImpacts, setStats, setLoading, setError]);

  useEffect(() => {
    loadData();

    // 交易时段 60 秒自动刷新
    const now = new Date();
    const hour = now.getHours();
    if (hour >= 9 && hour < 15) {
      refreshTimer.current = setInterval(loadData, 60000);
    }

    return () => {
      if (refreshTimer.current) clearInterval(refreshTimer.current);
    };
  }, [loadData]);

  const handleViewDetail = (impactId: number) => {
    setSelectedImpactId(impactId);
    setDetailVisible(true);
  };

  const displayedImpacts =
    statusFilter === "active"
      ? activeImpacts
      : statusFilter === "archived"
      ? archivedImpacts
      : [...activeImpacts, ...archivedImpacts];

  return (
    <div style={{ padding: 24, maxWidth: 900, margin: "0 auto" }}>
      {/* 标题栏 */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <div>
          <Title level={4} style={{ margin: 0 }}>事件影响雷达</Title>
          <Text style={{ fontSize: 13, color: "#94a3b8" }}>
            系统正在监控影响你投资的财经事件
          </Text>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <Button icon={<SyncOutlined />} onClick={loadData} loading={loading}>
            刷新
          </Button>
          <Button icon={<SettingOutlined />} onClick={() => setConfigVisible(true)}>
            设置
          </Button>
        </div>
      </div>

      {/* 统计卡片 */}
      {stats && <ImpactStatsCard stats={stats} />}

      {/* 分段切换 */}
      <div style={{ marginBottom: 12 }}>
        <Segmented
          value={statusFilter}
          onChange={(v) => setStatusFilter(v as string)}
          options={[
            { label: `正在影响 (${activeImpacts.length})`, value: "active" },
            { label: `今日已影响 (${archivedImpacts.length})`, value: "archived" },
            { label: "全部", value: "all" },
          ]}
        />
      </div>

      {/* 事件列表 */}
      {loading && !displayedImpacts.length ? (
        <div style={{ textAlign: "center", padding: "80px 0" }}>
          <Spin size="large" />
        </div>
      ) : error ? (
        <div style={{ textAlign: "center", padding: "80px 0", color: "#ea2261" }}>
          <Text type="danger">{error}</Text>
          <br />
          <Button onClick={loadData} style={{ marginTop: 8 }}>重试</Button>
        </div>
      ) : displayedImpacts.length === 0 ? (
        <Empty
          description={
            activeImpacts.length === 0 && archivedImpacts.length === 0
              ? "尚未检测到影响事件，系统正在持续监控中"
              : "该分类下暂无事件"
          }
          style={{ padding: "60px 0" }}
        />
      ) : (
        <div>
          {displayedImpacts.map((impact) => (
            <ImpactEventCard
              key={impact.id}
              impact={impact}
              onViewDetail={handleViewDetail}
            />
          ))}
        </div>
      )}

      {/* 底部声明 */}
      <div
        style={{
          marginTop: 24,
          padding: "10px 16px",
          background: "#f6f9fc",
          borderRadius: 6,
          textAlign: "center",
        }}
      >
        <Text style={{ fontSize: 12, color: "#98a2b3" }}>
          以上为 AI 分析参考，不构成投资建议
        </Text>
      </div>

      {/* Drawer */}
      <EventDetailDrawer
        visible={detailVisible}
        impactId={selectedImpactId}
        onClose={() => setDetailVisible(false)}
      />

      {/* 配置弹窗 */}
      <RadarConfigModal
        visible={configVisible}
        onClose={() => setConfigVisible(false)}
      />
    </div>
  );
};

export default EventRadarPage;
