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

interface ImpactItem {
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

interface EventRadarState {
  activeImpacts: ImpactItem[];
  archivedImpacts: ImpactItem[];
  stats: ImpactStats | null;
  currentDetail: any | null;
  alerts: AlertItem[];
  unreadCount: number;
  config: RadarConfig | null;
  stockImpacts: StockImpact[];
  loading: boolean;
  error: string | null;

  setActiveImpacts: (impacts: ImpactItem[]) => void;
  setArchivedImpacts: (impacts: ImpactItem[]) => void;
  setStats: (stats: ImpactStats) => void;
  setCurrentDetail: (detail: any) => void;
  setAlerts: (alerts: AlertItem[]) => void;
  setUnreadCount: (count: number) => void;
  setConfig: (config: RadarConfig) => void;
  setStockImpacts: (impacts: StockImpact[]) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  reset: () => void;
}

const initialState = {
  activeImpacts: [],
  archivedImpacts: [],
  stats: null,
  currentDetail: null,
  alerts: [],
  unreadCount: 0,
  config: null,
  stockImpacts: [],
  loading: false,
  error: null,
};

export const useEventRadarStore = create<EventRadarState>((set) => ({
  ...initialState,

  setActiveImpacts: (impacts) => set({ activeImpacts: impacts }),
  setArchivedImpacts: (impacts) => set({ archivedImpacts: impacts }),
  setStats: (stats) => set({ stats }),
  setCurrentDetail: (detail) => set({ currentDetail: detail }),
  setAlerts: (alerts) => set({ alerts }),
  setUnreadCount: (count) => set({ unreadCount: count }),
  setConfig: (config) => set({ config }),
  setStockImpacts: (impacts) => set({ stockImpacts: impacts }),
  setLoading: (loading) => set({ loading }),
  setError: (error) => set({ error }),
  reset: () => set(initialState),
}));
