import { create } from 'zustand';

interface StockDrawerState {
  visible: boolean;
  stockCode: string | null;
  open: (code: string) => void;
  close: () => void;
}

export const useStockDrawerStore = create<StockDrawerState>((set) => ({
  visible: false,
  stockCode: null,

  open: (code: string) => {
    set({ visible: true, stockCode: code });
  },

  close: () => {
    set({ visible: false, stockCode: null });
  },
}));
