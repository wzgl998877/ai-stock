/** 事件雷达主页面 — 三标签 + 情绪筛选 + RangePicker + 无限滚动 */

import React, { useEffect, useState, useCallback, useRef } from "react";
import { Button, Spin, Empty, DatePicker } from "antd";
import { SettingOutlined, SyncOutlined } from "@ant-design/icons";
import dayjs from "dayjs";
import "dayjs/locale/zh-cn";
import type { Dayjs } from "dayjs";

dayjs.locale("zh-cn");

import { useEventRadarStore, PAGE_SIZE } from "../store/eventRadarStore";
import type { StatusFilter, SentimentFilter } from "../store/eventRadarStore";
import { eventRadarService } from "../services/eventRadarService";
import ImpactEventCard from "../components/event-radar/ImpactEventCard";
import ImpactStatsCard from "../components/event-radar/ImpactStatsCard";
import EventDetailDrawer from "../components/event-radar/EventDetailDrawer";
import RadarConfigModal from "../components/event-radar/RadarConfigModal";

const { RangePicker } = DatePicker;

const STATUS_TABS: { label: string; value: StatusFilter }[] = [
  { label: "全部", value: "all" },
  { label: "进行中", value: "active" },
  { label: "已结束", value: "archived" },
];

const SENTIMENT_OPTIONS: { label: string; value: SentimentFilter; color: string }[] = [
  { label: "全部", value: "all", color: "#64748b" },
  { label: "利好", value: "positive", color: "#22c55e" },
  { label: "利空", value: "negative", color: "#ef4444" },
  { label: "中性", value: "neutral", color: "#94a3b8" },
];

const EventRadarPage: React.FC = () => {
  const {
    impacts,
    stats,
    loading,
    loadingMore,
    error,
    statusFilter,
    sentimentFilter,
    dateRange,
    pagination,
    setImpacts,
    appendImpacts,
    setStats,
    setLoading,
    setLoadingMore,
    setError,
    setStatusFilter,
    setSentimentFilter,
    setDateRange,
    setPagination,
  } = useEventRadarStore();

  const [detailVisible, setDetailVisible] = useState(false);
  const [selectedImpactId, setSelectedImpactId] = useState<number | null>(null);
  const [configVisible, setConfigVisible] = useState(false);
  const refreshTimer = useRef<ReturnType<typeof setInterval> | null>(null);
  const tabsRef = useRef<HTMLDivElement>(null);
  const sentinelRef = useRef<HTMLDivElement | null>(null);
  const observerRef = useRef<IntersectionObserver | null>(null);
  const [underlineStyle, setUnderlineStyle] = useState({ left: 0, width: 0 });

  // 用 ref 持有最新分页状态，避免 useCallback 依赖 pagination 导致循环
  const paginationRef = useRef(pagination);
  paginationRef.current = pagination;

  /** 构造请求参数（offset 由调用方显式传入） */
  const buildParams = useCallback(
    (offset: number): Record<string, any> => {
      const params: Record<string, any> = {
        status: statusFilter,
        limit: PAGE_SIZE,
        offset,
      };
      if (dateRange) {
        params.start_date = dateRange[0];
        params.end_date = dateRange[1];
      }
      if (sentimentFilter !== "all") {
        params.sentiment = sentimentFilter;
      }
      return params;
    },
    [statusFilter, sentimentFilter, dateRange],
  );

  /** 首次加载或刷新 */
  const loadFirstPage = useCallback(async () => {
    setLoading(true);
    setError(null);
    setPagination({ offset: 0, hasMore: true });
    try {
      const params = buildParams(0);
      const data = await eventRadarService.getImpacts(params);
      const items = data.impacts || [];
      setImpacts(items);
      setStats(data.stats || {});
      setPagination({
        offset: items.length,
        hasMore: items.length >= PAGE_SIZE,
      });
    } catch {
      setError("加载失败，请稍后重试");
    } finally {
      setLoading(false);
    }
  }, [buildParams, setImpacts, setStats, setLoading, setError, setPagination]);

  /** 加载更多（从 ref 读 offset，不触发重建） */
  const loadMore = useCallback(async () => {
    const { hasMore, offset } = paginationRef.current;
    if (!hasMore) return;
    setLoadingMore(true);
    try {
      const params = buildParams(offset);
      const data = await eventRadarService.getImpacts(params);
      const items = data.impacts || [];
      appendImpacts(items);
      setPagination({ offset: offset + items.length });
    } catch {
      // 静默失败
    } finally {
      setLoadingMore(false);
    }
  }, [buildParams, appendImpacts, setLoadingMore, setPagination]);

  // 筛选变化时重新加载
  useEffect(() => {
    loadFirstPage();
  }, [loadFirstPage]);

  // 交易时段 60 秒自动刷新
  useEffect(() => {
    const hour = new Date().getHours();
    if (hour >= 9 && hour < 15) {
      refreshTimer.current = setInterval(loadFirstPage, 60000);
    }
    return () => {
      if (refreshTimer.current) clearInterval(refreshTimer.current);
    };
  }, [loadFirstPage]);

  // IntersectionObserver 无限滚动
  useEffect(() => {
    if (observerRef.current) observerRef.current.disconnect();
    observerRef.current = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting) loadMore();
      },
      { rootMargin: "200px" },
    );
    const sentinel = sentinelRef.current;
    if (sentinel) observerRef.current.observe(sentinel);
    return () => { if (observerRef.current) observerRef.current.disconnect(); };
  }, [loadMore]);

  const handleViewDetail = (impactId: number) => {
    setSelectedImpactId(impactId);
    setDetailVisible(true);
  };

  // 滑动下划线位置
  useEffect(() => {
    requestAnimationFrame(() => {
      if (!tabsRef.current) return;
      const tabElements = tabsRef.current.querySelectorAll("[data-tab]");
      const activeIndex = STATUS_TABS.findIndex((t) => t.value === statusFilter);
      if (activeIndex >= 0 && tabElements[activeIndex]) {
        const el = tabElements[activeIndex] as HTMLElement;
        setUnderlineStyle({ left: el.offsetLeft, width: el.offsetWidth });
      }
    });
  }, [statusFilter]);

  // RangePicker 受控值
  const rangePickerValue: [Dayjs, Dayjs] | null = dateRange
    ? [dayjs(dateRange[0]), dayjs(dateRange[1])]
    : null;

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
            <Button icon={<SyncOutlined />} onClick={loadFirstPage} loading={loading}>
              刷新
            </Button>
            <Button icon={<SettingOutlined />} onClick={() => setConfigVisible(true)}>
              设置
            </Button>
          </div>
        </div>

        {/* 仪表盘 */}
        {stats && <ImpactStatsCard stats={stats} />}

        {/* 第一行：状态标签页 + RangePicker */}
        <div style={{ display: "flex", alignItems: "center", borderBottom: "2px solid #e5edf5", position: "relative" }}>
          <div ref={tabsRef} style={{ display: "flex" }}>
            {STATUS_TABS.map((tab) => (
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
                }}
              >
                {tab.label}
              </div>
            ))}
          </div>
          <div style={{ flex: 1 }} />
          <RangePicker
            value={rangePickerValue}
            onChange={(dates: [Dayjs | null, Dayjs | null] | null) => {
              if (dates && dates[0] && dates[1]) {
                setDateRange([dates[0].format("YYYY-MM-DD"), dates[1].format("YYYY-MM-DD")]);
              } else {
                setDateRange(null);
              }
            }}
            placeholder={["开始日期", "结束日期"]}
            allowClear
            size="small"
            style={{ width: 240 }}
          />
          {/* 滑动下划线 */}
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

        {/* 第二行：情绪筛选 */}
        <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "12px 0 16px" }}>
          <span style={{ fontSize: 13, color: "#94a3b8", marginRight: 4 }}>情绪：</span>
          {SENTIMENT_OPTIONS.map((opt) => (
            <span
              key={opt.value}
              onClick={() => setSentimentFilter(opt.value)}
              style={{
                display: "inline-block",
                padding: "2px 12px",
                borderRadius: 12,
                fontSize: 13,
                cursor: "pointer",
                userSelect: "none",
                fontWeight: sentimentFilter === opt.value ? 600 : 400,
                color: sentimentFilter === opt.value ? "#fff" : opt.color,
                background: sentimentFilter === opt.value ? opt.color : "transparent",
                border: `1px solid ${opt.color}`,
                transition: "all 0.2s",
              }}
            >
              {opt.label}
            </span>
          ))}
        </div>

        {/* 事件列表 */}
        {loading && !impacts.length ? (
          <div style={{ textAlign: "center", padding: "80px 0" }}>
            <Spin size="large" />
            <div style={{ marginTop: 16, color: "#2A6DFF", fontSize: 13, fontWeight: 500 }}>AI 正在扫描市场...</div>
          </div>
        ) : error ? (
          <div style={{ textAlign: "center", padding: "80px 0" }}>
            <div style={{ color: "#E74C3C", marginBottom: 12 }}>{error}</div>
            <Button onClick={loadFirstPage}>重试</Button>
          </div>
        ) : impacts.length === 0 ? (
          <Empty
            description="尚未检测到影响事件，系统正在持续监控中"
            style={{ padding: "60px 0" }}
          />
        ) : (
          <>
            <div style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(min(100%, 480px), 1fr))",
              gap: 16,
              alignItems: "start",
            }}>
              {impacts.map((impact) => (
                <ImpactEventCard
                  key={impact.id}
                  impact={impact}
                  onViewDetail={handleViewDetail}
                />
              ))}
            </div>

            {/* 哨兵 + 加载更多 */}
            <div ref={sentinelRef} style={{ height: 1 }} />
            {loadingMore && (
              <div style={{ textAlign: "center", padding: "24px 0" }}>
                <Spin />
                <div style={{ marginTop: 8, color: "#94a3b8", fontSize: 13 }}>加载更多...</div>
              </div>
            )}
            {!pagination.hasMore && impacts.length > 0 && (
              <div style={{ textAlign: "center", padding: "16px 0", color: "#94a3b8", fontSize: 13 }}>
                已加载全部
              </div>
            )}
          </>
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
