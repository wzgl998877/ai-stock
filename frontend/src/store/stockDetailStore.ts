import { create } from 'zustand';
import { stockDataService } from '../services/stockDataService';

// --- 类型定义 ---

export interface StockIndicatorItem {
  trade_date: string;
  ma5?: number | null;
  ma10?: number | null;
  ma20?: number | null;
  macd_dif?: number | null;
  macd_dea?: number | null;
  macd_bar?: number | null;
  kdj_k?: number | null;
  kdj_d?: number | null;
  kdj_j?: number | null;
}

export interface MinuteQuoteItem {
  time: string;
  price: number;
  volume: number;
  avg_price?: number;
}

export interface RelatedArticle {
  article_id: string;
  title: string;
  summary: string;
  saved_at: string;
}

export interface StockDetailBasic {
  code: string;
  name: string;
  exchange: string;
  industry_code: string;
  industry_name: string;
  list_date: string;
  total_market_cap: number;
  float_market_cap: number;
}

export interface StockDetailQuote {
  price: number;
  change_pct: number;
  change_amount: number;
  volume: number;
  amount: number;
  open_price: number;
  high_price: number;
  low_price: number;
  pre_close: number;
  pe_ttm: number;
  pb: number;
}

export interface StockDetailFinancial {
  revenue: number;
  revenue_growth_pct: number;
  net_profit: number;
  profit_growth_pct: number;
}

export type KlinePeriod = 'minute' | 'daily' | 'weekly' | 'monthly';

// --- A 股交易时段判断 ---

export function isMarketOpen(): boolean {
  const now = new Date();
  // 获取北京时间（UTC+8）
  const utc = now.getTime() + now.getTimezoneOffset() * 60000;
  const bj = new Date(utc + 8 * 3600000);
  const h = bj.getHours();
  const m = bj.getMinutes();
  const day = bj.getDay();
  // 周六(6)、周日(0)休市
  if (day === 0 || day === 6) return false;
  const t = h * 60 + m;
  // 上午 9:30 - 11:30，下午 13:00 - 15:00
  return (t >= 570 && t <= 690) || (t >= 780 && t <= 900);
}

interface StockDetailState {
  stockCode: string | null;
  basic: StockDetailBasic | null;
  quote: StockDetailQuote | null;
  financial: StockDetailFinancial | null;
  klineData: any[];
  minuteData: MinuteQuoteItem[];
  indicators: StockIndicatorItem[];
  relatedArticles: RelatedArticle[];
  loading: boolean;
  klineLoading: boolean;
  error: string | null;
  activePeriod: KlinePeriod;
  showMACD: boolean;
  showKDJ: boolean;

  fetchStockDetail: (code: string) => Promise<void>;
  fetchKlineData: (code: string, period: KlinePeriod) => Promise<void>;
  refreshMinuteData: (code: string) => Promise<void>;
  fetchIndicators: (code: string, period: string) => Promise<void>;
  fetchRelatedArticles: (code: string) => Promise<void>;
  setActivePeriod: (period: KlinePeriod) => void;
  toggleMACD: () => void;
  toggleKDJ: () => void;
  clear: () => void;
}

const initialState = {
  stockCode: null,
  basic: null,
  quote: null,
  financial: null,
  klineData: [],
  minuteData: [],
  indicators: [],
  relatedArticles: [],
  loading: false,
  klineLoading: false,
  error: null,
  activePeriod: 'daily' as KlinePeriod,
  showMACD: false,
  showKDJ: false,
};

export const useStockDetailStore = create<StockDetailState>((set, get) => ({
  ...initialState,

  fetchStockDetail: async (code: string) => {
    set({ loading: true, error: null, stockCode: code });
    try {
      const res = await stockDataService.getStockDetail(code);
      // detail API 返回扁平结构，拆分为 basic/quote/financial
      const d = res.data || {};
      set({
        basic: {
          code: d.stock_code || code,
          name: d.name || '',
          exchange: d.exchange || '',
          industry_code: d.industry_code || '',
          industry_name: d.industry || '',
          list_date: d.list_date || '',
          total_market_cap: d.total_market_cap,
          float_market_cap: d.float_market_cap,
        },
        quote: d.price != null ? {
          price: d.price,
          change_pct: d.change_pct,
          change_amount: d.change_amount,
          volume: d.volume,
          amount: d.amount,
          open_price: d.open_price,
          high_price: d.high_price,
          low_price: d.low_price,
          pre_close: d.pre_close,
          pe_ttm: d.pe_ttm,
          pb: d.pb,
        } : null,
        financial: d.revenue != null ? {
          revenue: d.revenue,
          revenue_growth_pct: null,
          net_profit: d.net_profit,
          profit_growth_pct: null,
        } : null,
        relatedArticles: d.related_articles || [],
        loading: false,
      });
      // 并发加载K线和相关文章
      get().fetchKlineData(code, get().activePeriod);
      get().fetchRelatedArticles(code);
    } catch (e: any) {
      set({ error: e.message || '加载失败', loading: false });
    }
  },

  fetchKlineData: async (code: string, period: KlinePeriod) => {
    set({ klineLoading: true, klineData: [], minuteData: [], indicators: [] });
    try {
      if (period === 'minute') {
        const res = await stockDataService.getStockMinute(code);
        set({ minuteData: res.data.items || [], klineLoading: false });
      } else {
        const res = await stockDataService.getStockDaily(code, { period });
        set({ klineData: res?.items || [], klineLoading: false });
        // 同时加载指标
        get().fetchIndicators(code, period);
      }
    } catch {
      set({ klineLoading: false });
    }
  },

  /** 静默刷新分时数据（轮询用，不设 loading 状态） */
  refreshMinuteData: async (code: string) => {
    try {
      const res = await stockDataService.getStockMinute(code);
      set({ minuteData: res.data.items || [] });
    } catch {
      // 静默失败，保留当前数据
    }
  },

  fetchIndicators: async (code: string, period: string) => {
    try {
      const res = await stockDataService.getStockIndicators(code, {
        period,
        indicators: 'ma,macd,kdj',
      });
      set({ indicators: res.data.items || [] });
    } catch {
      // 指标加载失败不影响K线显示
    }
  },

  fetchRelatedArticles: async (code: string) => {
    try {
      const res = await stockDataService.getStockRelatedArticles(code);
      set({ relatedArticles: res.data.items || [] });
    } catch {
      // 相关文章加载失败不影响主页面
    }
  },

  setActivePeriod: (period: KlinePeriod) => {
    set({ activePeriod: period });
    const code = get().stockCode;
    if (code) {
      get().fetchKlineData(code, period);
    }
  },

  toggleMACD: () => set((s) => ({ showMACD: !s.showMACD })),
  toggleKDJ: () => set((s) => ({ showKDJ: !s.showKDJ })),
  clear: () => set(initialState),
}));
