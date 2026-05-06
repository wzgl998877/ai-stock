import { create } from 'zustand';
import { watchlistService } from '../services/watchlistService';

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
  industry?: string;
  signal?: string;
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
}

export const useWatchlistStore = create<WatchlistState>((set) => ({
  groups: [],
  loading: false,
  error: null,

  fetchGroups: async () => {
    set({ loading: true, error: null });
    try {
      const res = await watchlistService.getGroups();
      set({ groups: res.data.groups || [], loading: false });
    } catch (e: any) {
      set({ error: e.message || '加载自选股失败', loading: false });
    }
  },

  createGroup: async (name: string) => {
    try {
      await watchlistService.createGroup(name);
      // 重新获取分组列表
      const res = await watchlistService.getGroups();
      set({ groups: res.data.groups || [] });
    } catch (e: any) {
      set({ error: e.message });
    }
  },

  renameGroup: async (groupId: number, name: string) => {
    try {
      await watchlistService.renameGroup(groupId, name);
      const res = await watchlistService.getGroups();
      set({ groups: res.data.groups || [] });
    } catch (e: any) {
      set({ error: e.message });
    }
  },

  deleteGroup: async (groupId: number) => {
    try {
      await watchlistService.deleteGroup(groupId);
      const res = await watchlistService.getGroups();
      set({ groups: res.data.groups || [] });
    } catch (e: any) {
      set({ error: e.message });
    }
  },

  addStock: async (groupId: number, stockCode: string, stockName: string) => {
    try {
      await watchlistService.addStock(groupId, stockCode, stockName);
      // 刷新分组数据
      const res = await watchlistService.getGroups();
      set({ groups: res.data.groups || [] });
    } catch (e: any) {
      set({ error: e.message });
    }
  },

  removeStock: async (groupId: number, stockCode: string) => {
    try {
      await watchlistService.removeStock(groupId, stockCode);
      const res = await watchlistService.getGroups();
      set({ groups: res.data.groups || [] });
    } catch (e: any) {
      set({ error: e.message });
    }
  },
}));
