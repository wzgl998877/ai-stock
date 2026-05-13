/** 事件雷达主页面 — AI 金融终端风格 */

import React, { useEffect, useState, useCallback, useRef } from "react";
import { Button, Spin, Empty, Segmented } from "antd";
import { SettingOutlined, SyncOutlined } from "@ant-design/icons";
import { useEventRadarStore } from "../store/eventRadarStore";
import { eventRadarService } from "../services/eventRadarService";
import ImpactEventCard from "../components/event-radar/ImpactEventCard";
import ImpactStatsCard from "../components/event-radar/ImpactStatsCard";
import EventDetailDrawer from "../components/event-radar/EventDetailDrawer";
import RadarConfigModal from "../components/event-radar/RadarConfigModal";

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
    <div style={{ padding: "16px 20px", height: "100%", overflowY: "auto" }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <div>
          <div style={{ fontSize: 18, fontWeight: 700, color: "#0f172a" }}>事件影响雷达</div>
          <div style={{ fontSize: 13, color: "#94a3b8", marginTop: 2 }}>AI 实时监控影响你投资的事件</div>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <Button icon={<SyncOutlined />} onClick={loadData} loading={loading} size="middle">
            刷新
          </Button>
          <Button icon={<SettingOutlined />} onClick={() => setConfigVisible(true)} size="middle">
            设置
          </Button>
        </div>
      </div>

      {/* AI Status Bar */}
      {stats && <ImpactStatsCard stats={stats} />}

      {/* Tabs */}
      <div style={{ display: "flex", gap: 4, marginBottom: 12 }}>
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

      {/* Event List */}
      {loading && !displayedImpacts.length ? (
        <div style={{ textAlign: "center", padding: "80px 0" }}>
          <Spin size="large" />
          <div style={{ marginTop: 16, color: "#6366f1", fontSize: 13, fontWeight: 500 }}>AI 正在扫描市场...</div>
        </div>
      ) : error ? (
        <div style={{ textAlign: "center", padding: "80px 0" }}>
          <div style={{ color: "#dc2626", marginBottom: 12 }}>{error}</div>
          <Button onClick={loadData}>重试</Button>
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

      {/* Disclaimer */}
      <div style={{
        marginTop: 20,
        padding: "10px 16px",
        background: "#f8fafc",
        borderRadius: 6,
        border: "1px solid #f1f5f9",
        textAlign: "center",
        fontSize: 12,
        color: "#94a3b8",
      }}>
        以上为 AI 分析参考，不构成投资建议
      </div>

      {/* Drawers */}
      <EventDetailDrawer
        visible={detailVisible}
        impactId={selectedImpactId}
        onClose={() => setDetailVisible(false)}
      />
      <RadarConfigModal
        visible={configVisible}
        onClose={() => setConfigVisible(false)}
      />
    </div>
  );
};

export default EventRadarPage;
