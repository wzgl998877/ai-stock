import api from "./api";

export interface StockBasicInfo {
  code: string;
  name: string;
  exchange: string | null;
  market_type: string | null;
  list_date: string | null;
  is_active: boolean;
  data_source: string;
}

export interface StockQuote {
  code: string;
  price: number | null;
  change_pct: number | null;
  change_amount: number | null;
  volume: number | null;
  amount: number | null;
  open_price: number | null;
  high_price: number | null;
  low_price: number | null;
  pre_close: number | null;
  quote_time: string | null;
  data_source: string;
}

export interface StockDailyItem {
  trade_date: string;
  open: number | null;
  high: number | null;
  low: number | null;
  close: number | null;
  volume: number | null;
  amount: number | null;
  pct_chg: number | null;
  data_source: string;
}

export interface StockFinancialItem {
  report_date: string;
  roe: number | null;
  net_profit: number | null;
  revenue: number | null;
  eps: number | null;
  gross_margin: number | null;
  debt_ratio: number | null;
  data_source: string;
}

export const stockDataService = {
  async getStockBasic(code: string): Promise<StockBasicInfo> {
    const res = await api.get(`/api/v1/stocks/${code}`);
    return res.data.data;
  },

  async getStockQuote(code: string): Promise<StockQuote> {
    const res = await api.get(`/api/v1/stocks/${code}/quote`);
    return res.data.data;
  },

  async getStockDaily(
    code: string,
    params?: { start_date?: string; end_date?: string; period?: string },
  ): Promise<{ code: string; period: string; items: StockDailyItem[] }> {
    const res = await api.get(`/api/v1/stocks/${code}/daily`, { params });
    return res.data.data;
  },

  async getStockFinancial(code: string): Promise<{ code: string; items: StockFinancialItem[] }> {
    const res = await api.get(`/api/v1/stocks/${code}/financial`);
    return res.data.data;
  },

  // --- 模块二新增接口 ---

  async getStockMinute(code: string) {
    const res = await api.get(`/api/v1/stocks/${code}/minute`);
    return res.data;
  },

  async getStockIndicators(code: string, params?: {
    period?: string;
    indicators?: string;
    start_date?: string;
    end_date?: string;
  }) {
    const res = await api.get(`/api/v1/stocks/${code}/indicators`, { params });
    return res.data;
  },

  async getStockDetail(code: string) {
    const res = await api.get(`/api/v1/stocks/${code}/detail`);
    return res.data;
  },

  async getStockRelatedArticles(code: string, limit?: number) {
    const res = await api.get(`/api/v1/stocks/${code}/related-articles`, {
      params: limit ? { limit } : undefined,
    });
    return res.data;
  },

  async searchStocks(query: string, limit?: number) {
    const res = await api.get('/api/v1/stocks/search', {
      params: { q: query, limit: limit || 20 },
    });
    return res.data;
  },

  async getAllStocks() {
    const res = await api.get('/api/v1/stocks/all');
    return res.data;
  },
};
