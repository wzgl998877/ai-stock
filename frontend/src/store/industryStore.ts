import { create } from 'zustand';
import { industryService } from '../services/industryService';

export interface Industry {
  code: string;
  name: string;
  display_order: number;
}

export interface IndustryStock {
  code: string;
  name: string;
  change_pct: number;
  pe_ttm: number;
  pb: number;
  revenue: number;
  net_profit: number;
  profit_growth_pct: number;
}

interface IndustryState {
  industries: Industry[];
  selectedIndustry: string | null;
  selectedIndustryName: string;
  avgChangePct: number;
  comparisonData: IndustryStock[];
  total: number;
  loading: boolean;
  tableLoading: boolean;
  error: string | null;
  tableError: string | null;

  fetchIndustries: () => Promise<void>;
  selectIndustry: (code: string, name: string) => Promise<void>;
}

export const useIndustryStore = create<IndustryState>((set, get) => ({
  industries: [],
  selectedIndustry: null,
  selectedIndustryName: '',
  avgChangePct: 0,
  comparisonData: [],
  total: 0,
  loading: false,
  tableLoading: false,
  error: null,
  tableError: null,

  fetchIndustries: async () => {
    set({ loading: true, error: null });
    try {
      const res = await industryService.getIndustries();
      set({ industries: res.data.items || [], loading: false });
    } catch (e: any) {
      set({ error: e.message || '加载行业列表失败', loading: false });
    }
  },

  selectIndustry: async (code: string, name: string) => {
    set({ selectedIndustry: code, selectedIndustryName: name, tableLoading: true, tableError: null });
    try {
      const res = await industryService.getIndustryStocks(code);
      set({
        comparisonData: res.data.items || [],
        avgChangePct: res.data.industry?.avg_change_pct || 0,
        total: res.data.total || 0,
        tableLoading: false,
      });
    } catch (e: any) {
      set({ tableError: e.message || '加载行业数据失败', tableLoading: false });
    }
  },
}));
