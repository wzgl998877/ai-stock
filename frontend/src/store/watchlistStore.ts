import { create } from 'zustand';
import { watchlistService, stockQuoteService } from '../services/watchlistService';

export interface WatchlistGroup {
  id: number;
  name: string;
  is_default: boolean;
  display_order: number;
  stock_count: number;
  stocks: WatchlistStock[];
}

export interface WatchlistStock {
  code: string;
  name: string;
  price?: number;
  change_pct?: number;
  change_amount?: number;
  industry?: string;
  signal?: string;
  add_price?: number;
  add_time?: string;
}

interface WatchlistState {
  groups: WatchlistGroup[];
  loading: boolean;
  error: string | null;

  fetchGroups: () => Promise<void>;
  createGroup: (name: string) => Promise<void>;
  renameGroup: (groupId: number, name: string) => Promise<void>;
  deleteGroup: (groupId: number) => Promise<void>;
  addStock: (groupId: number, stockCode: string, stockName: string) => Promise<void>;
  removeStock: (groupId: number, stockCode: string) => Promise<void>;
  loadQuotes: () => Promise<void>;
}

export const useWatchlistStore = create<WatchlistState>((set, get) => ({
  groups: [],
  loading: false,
  error: null,

  fetchGroups: async () => {
    set({ loading: true, error: null });
    try {
      const res = await watchlistService.getGroups();
      set({ groups: res.data.groups || [], loading: false });
      // 加载行情数据
      await get().loadQuotes();
    } catch (e: any) {
      set({ error: e.message || '加载自选股失败', loading: false });
    }
  },

  loadQuotes: async () => {
    const { groups } = get();
    // 收集所有股票代码
    const codes = new Set<string>();
    for (const group of groups) {
      for (const stock of group.stocks) {
        codes.add(stock.code);
      }
    }
    if (codes.size === 0) return;

    try {
      const res = await stockQuoteService.getQuotesBatch(Array.from(codes));
      const quoteMap = new Map<string, any>();
      for (const item of res.data.items) {
        quoteMap.set(item.code, item);
      }

      // 更新 groups 中的行情数据
      const updatedGroups = groups.map((group) => ({
        ...group,
        stocks: group.stocks.map((stock) => {
          const quote = quoteMap.get(stock.code);
          if (!quote) return stock;
          return {
            ...stock,
            price: quote.price ?? stock.price,
            change_pct: quote.change_pct ?? stock.change_pct,
            change_amount: quote.change_amount ?? stock.change_amount,
            industry: quote.industry ?? stock.industry,
          };
        }),
      }));
      set({ groups: updatedGroups });
    } catch (e: any) {
      // 行情加载失败不阻塞主流程
      console.error('加载行情失败:', e);
    }
  },

  createGroup: async (name: string) => {
    try {
      await watchlistService.createGroup(name);
      const res = await watchlistService.getGroups();
      set({ groups: res.data.groups || [] });
      await get().loadQuotes();
    } catch (e: any) {
      set({ error: e.message });
    }
  },

  renameGroup: async (groupId: number, name: string) => {
    try {
      await watchlistService.renameGroup(groupId, name);
      const res = await watchlistService.getGroups();
      set({ groups: res.data.groups || [] });
      await get().loadQuotes();
    } catch (e: any) {
      set({ error: e.message });
    }
  },

  deleteGroup: async (groupId: number) => {
    try {
      await watchlistService.deleteGroup(groupId);
      const res = await watchlistService.getGroups();
      set({ groups: res.data.groups || [] });
      await get().loadQuotes();
    } catch (e: any) {
      set({ error: e.message });
    }
  },

  addStock: async (groupId: number, stockCode: string, stockName: string) => {
    try {
      await watchlistService.addStock(groupId, stockCode, stockName);
      const res = await watchlistService.getGroups();
      set({ groups: res.data.groups || [] });
      await get().loadQuotes();
    } catch (e: any) {
      set({ error: e.message });
    }
  },

  removeStock: async (groupId: number, stockCode: string) => {
    try {
      await watchlistService.removeStock(groupId, stockCode);
      const res = await watchlistService.getGroups();
      set({ groups: res.data.groups || [] });
      await get().loadQuotes();
    } catch (e: any) {
      set({ error: e.message });
    }
  },
}));
