/** 事件雷达主页面 — 重构版 */

import React, { useEffect, useState, useCallback, useRef } from "react";
import { Button, Spin, Empty } from "antd";
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
  const tabsRef = useRef<HTMLDivElement>(null);
  const [underlineStyle, setUnderlineStyle] = useState({ left: 0, width: 0 });

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

  // 标签页配置
  const tabs = [
    { label: "正在影响", value: "active", count: activeImpacts.length },
    { label: "今日已影响", value: "archived", count: archivedImpacts.length },
  ];

  // 滑动下划线位置
  useEffect(() => {
    requestAnimationFrame(() => {
      if (!tabsRef.current) return;
      const tabElements = tabsRef.current.querySelectorAll("[data-tab]");
      const activeIndex = tabs.findIndex((t) => t.value === statusFilter);
      if (activeIndex >= 0 && tabElements[activeIndex]) {
        const el = tabElements[activeIndex] as HTMLElement;
        setUnderlineStyle({ left: el.offsetLeft, width: el.offsetWidth });
      }
    });
  }, [statusFilter, activeImpacts.length, archivedImpacts.length]);

  return (
    <div style={{ background: "#F7F9FC", padding: 24, height: "100%", overflowY: "auto" }}>
      <div style={{ maxWidth: 1400, margin: "0 auto" }}>
        {/* Header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
          <div>
            <div style={{ fontSize: 20, fontWeight: 700, color: "#0f172a" }}>事件影响雷达</div>
            <div style={{ fontSize: 13, color: "#94a3b8", marginTop: 2 }}>AI 实时监控影响你投资的事件</div>
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

        {/* 仪表盘 */}
        {stats && <ImpactStatsCard stats={stats} />}

        {/* 标签页 + 滑动下划线 */}
        <div
          ref={tabsRef}
          style={{ display: "flex", borderBottom: "2px solid #e5edf5", marginBottom: 16, position: "relative" }}
        >
          {tabs.map((tab) => (
            <div
              key={tab.value}
              data-tab={tab.value}
              onClick={() => setStatusFilter(tab.value)}
              style={{
                padding: "12px 24px",
                cursor: "pointer",
                fontSize: 14,
                fontWeight: statusFilter === tab.value ? 600 : 400,
                color: statusFilter === tab.value ? "#2A6DFF" : "#64748b",
                transition: "color 0.2s",
                userSelect: "none",
                display: "flex",
                alignItems: "center",
                gap: 6,
              }}
            >
              {tab.label}
              {tab.count > 0 && (
                <span
                  style={{
                    padding: "1px 8px",
                    borderRadius: 10,
                    fontSize: 12,
                    background: statusFilter === tab.value ? "rgba(42,109,255,0.1)" : "#f1f5f9",
                    color: statusFilter === tab.value ? "#2A6DFF" : "#94a3b8",
                  }}
                >
                  {tab.count}
                </span>
              )}
            </div>
          ))}
          <div
            style={{
              position: "absolute",
              bottom: -2,
              height: 2,
              background: "#2A6DFF",
              borderRadius: 1,
              transition: "left 0.3s ease, width 0.3s ease",
              left: underlineStyle.left,
              width: underlineStyle.width,
            }}
          />
        </div>

        {/* 事件列表 — 双列网格 */}
        {loading && !displayedImpacts.length ? (
          <div style={{ textAlign: "center", padding: "80px 0" }}>
            <Spin size="large" />
            <div style={{ marginTop: 16, color: "#2A6DFF", fontSize: 13, fontWeight: 500 }}>AI 正在扫描市场...</div>
          </div>
        ) : error ? (
          <div style={{ textAlign: "center", padding: "80px 0" }}>
            <div style={{ color: "#E74C3C", marginBottom: 12 }}>{error}</div>
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
          <div style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(min(100%, 480px), 1fr))",
            gap: 16,
            alignItems: "start",
          }}>
            {displayedImpacts.map((impact) => (
              <ImpactEventCard
                key={impact.id}
                impact={impact}
                onViewDetail={handleViewDetail}
              />
            ))}
          </div>
        )}

        {/* 免责声明 */}
        <div style={{
          marginTop: 24,
          padding: "10px 16px",
          background: "#ffffff",
          borderRadius: 16,
          boxShadow: "0 1px 3px rgba(0,0,0,0.04), 0 1px 2px rgba(0,0,0,0.02)",
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
    </div>
  );
};

export default EventRadarPage;
