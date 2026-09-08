import { create } from 'zustand';
import { stockDataService } from '../services/stockDataService';
import { getStructure } from '../services/strategyService';
import type { ChanlunVersion, SignalMark, StructureData } from '../domain/types';

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
  revenue_growth_pct: number | null;   // 后端不一定提供，可能为 null
  net_profit: number;
  profit_growth_pct: number | null;
}

export type KlinePeriod = 'minute' | 'daily' | 'weekly' | 'monthly';

// A 股交易时段判断统一走 utils/marketTime（北京时区）；此处 re-export 保持向后兼容。
export { isMarketOpen } from '../utils/marketTime';

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
  showChanlun: boolean;
  signalMarks: SignalMark[];
  structureData: StructureData | null;
  highlightDate: string | null;
  /** 缠论结构图层口径（双版本并存，2026-09-08）；默认 v2 */
  structureVersion: ChanlunVersion;

  fetchStockDetail: (code: string) => Promise<void>;
  fetchKlineData: (code: string, period: KlinePeriod) => Promise<void>;
  refreshMinuteData: (code: string) => Promise<void>;
  fetchIndicators: (code: string, period: string) => Promise<void>;
  fetchRelatedArticles: (code: string) => Promise<void>;
  setActivePeriod: (period: KlinePeriod) => void;
  toggleMACD: () => void;
  toggleKDJ: () => void;
  toggleChanlun: () => void;
  fetchChanlunLayer: (code: string, period: KlinePeriod) => Promise<void>;
  setStructureVersion: (version: ChanlunVersion, code: string) => void;
  setHighlightDate: (date: string | null) => void;
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
  showChanlun: true,
  signalMarks: [],
  structureData: null,
  highlightDate: null,
  structureVersion: 'v2' as ChanlunVersion,
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
        // 同时加载指标与缠论结构图层（笔/线段/中枢 + 买卖点）
        get().fetchIndicators(code, period);
        get().fetchChanlunLayer(code, period);
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
  toggleChanlun: () => set((s) => ({ showChanlun: !s.showChanlun })),
  fetchChanlunLayer: async (code: string, period: KlinePeriod) => {
    // 缠论结构图层（笔/线段/中枢 + 买卖点标注）仅日 K 支持；周/月/分时见 T041
    if (period !== 'daily') {
      set({ signalMarks: [], structureData: null });
      return;
    }
    try {
      const { structure, signalMarks } = await getStructure(code, 'daily', get().structureVersion);
      set({ structureData: structure, signalMarks });
    } catch {
      // 结构加载失败不影响 K 线显示
      set({ signalMarks: [], structureData: null });
    }
  },
  setStructureVersion: (version: ChanlunVersion, code: string) => {
    if (get().structureVersion === version) return;
    set({ structureVersion: version });
    // 口径切换：按新版本重拉结构图层
    get().fetchChanlunLayer(code, get().activePeriod);
  },
  setHighlightDate: (date: string | null) => set({ highlightDate: date }),
  clear: () => set(initialState),
}));
