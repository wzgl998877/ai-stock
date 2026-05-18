/** 事件雷达状态管理 */

import { create } from "zustand";

interface MatchedStock {
  code: string;
  name: string;
  direction: string;
  confidence: number;
}

interface MatchedIndustry {
  name: string;
  direction: string;
}

export interface ImpactItem {
  id: number;
  event_id: number;
  title: string;
  summary: string | null;
  event_type: string | null;
  sentiment: string | null;
  importance: string | null;
  source_count: number;
  matched_stocks: MatchedStock[];
  matched_industries: MatchedIndustry[];
  priority: string;
  is_read: boolean;
  has_ai_insight: boolean;
  has_related_analysis: boolean;
  first_seen_at: string | null;
  source_name: string;
  source_url: string;
}

interface ImpactStats {
  today_total: number;
  today_positive: number;
  today_negative: number;
  today_neutral: number;
  affected_stocks_count: number;
  week_total: number;
}

interface AlertItem {
  id: number;
  priority: string;
  title: string;
  summary: string | null;
  user_impact_id: number;
  is_read: boolean;
  created_at: string | null;
}

interface RadarConfig {
  focused_industries: string[];
  event_types: string[];
  alert_sensitivity: string;
  quiet_hours_start: string | null;
  quiet_hours_end: string | null;
}

interface StockImpact {
  code: string;
  name: string;
  impact_count_24h: number;
  direction: string;
  recent_impacts: any[];
}

export type StatusFilter = "all" | "active" | "archived";
export type SentimentFilter = "all" | "positive" | "negative" | "neutral";

interface Pagination {
  limit: number;
  offset: number;
  hasMore: boolean;
}

interface EventRadarState {
  impacts: ImpactItem[];
  stats: ImpactStats | null;
  currentDetail: any | null;
  alerts: AlertItem[];
  unreadCount: number;
  config: RadarConfig | null;
  stockImpacts: StockImpact[];
  loading: boolean;
  loadingMore: boolean;
  error: string | null;
  statusFilter: StatusFilter;
  sentimentFilter: SentimentFilter;
  dateRange: [string, string] | null;
  pagination: Pagination;

  setImpacts: (impacts: ImpactItem[]) => void;
  appendImpacts: (impacts: ImpactItem[]) => void;
  setStats: (stats: ImpactStats) => void;
  setCurrentDetail: (detail: any) => void;
  setAlerts: (alerts: AlertItem[]) => void;
  setUnreadCount: (count: number) => void;
  setConfig: (config: RadarConfig) => void;
  setStockImpacts: (impacts: StockImpact[]) => void;
  setLoading: (loading: boolean) => void;
  setLoadingMore: (loading: boolean) => void;
  setError: (error: string | null) => void;
  setStatusFilter: (filter: StatusFilter) => void;
  setSentimentFilter: (filter: SentimentFilter) => void;
  setDateRange: (range: [string, string] | null) => void;
  setPagination: (pagination: Partial<Pagination>) => void;
  reset: () => void;
}

export const PAGE_SIZE = 20;

const initialState = {
  impacts: [],
  stats: null,
  currentDetail: null,
  alerts: [],
  unreadCount: 0,
  config: null,
  stockImpacts: [],
  loading: false,
  loadingMore: false,
  error: null,
  statusFilter: "all" as StatusFilter,
  sentimentFilter: "all" as SentimentFilter,
  dateRange: null,
  pagination: { limit: PAGE_SIZE, offset: 0, hasMore: true },
};

export const useEventRadarStore = create<EventRadarState>((set) => ({
  ...initialState,

  setImpacts: (impacts) => set({ impacts }),
  appendImpacts: (newImpacts) =>
    set((state) => {
      const existingIds = new Set(state.impacts.map((i) => i.id));
      const deduped = newImpacts.filter((i) => !existingIds.has(i.id));
      return {
        impacts: [...state.impacts, ...deduped],
        pagination: {
          ...state.pagination,
          hasMore: newImpacts.length >= state.pagination.limit,
        },
      };
    }),
  setStats: (stats) => set({ stats }),
  setCurrentDetail: (detail) => set({ currentDetail: detail }),
  setAlerts: (alerts) => set({ alerts }),
  setUnreadCount: (count) => set({ unreadCount: count }),
  setConfig: (config) => set({ config }),
  setStockImpacts: (impacts) => set({ stockImpacts: impacts }),
  setLoading: (loading) => set({ loading }),
  setLoadingMore: (loadingMore) => set({ loadingMore }),
  setError: (error) => set({ error }),
  setStatusFilter: (statusFilter) =>
    set({ statusFilter, impacts: [], pagination: { limit: PAGE_SIZE, offset: 0, hasMore: true } }),
  setSentimentFilter: (sentimentFilter) =>
    set({ sentimentFilter, impacts: [], pagination: { limit: PAGE_SIZE, offset: 0, hasMore: true } }),
  setDateRange: (dateRange) =>
    set({ dateRange, impacts: [], pagination: { limit: PAGE_SIZE, offset: 0, hasMore: true } }),
  setPagination: (partial) =>
    set((state) => ({ pagination: { ...state.pagination, ...partial } })),
  reset: () => set(initialState),
}));
