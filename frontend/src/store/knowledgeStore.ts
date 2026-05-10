/** 知识库状态管理 (Zustand) */

import { create } from "zustand";
import type { ArticleListItem } from "../domain/types";

export type ViewMode = "timeline" | "industry" | "stock";

interface KnowledgeState {
  // 视图状态
  view: ViewMode;
  selectedIndustry: string | null;
  selectedStock: string | null;
  searchKeyword: string;

  // 数据
  articles: ArticleListItem[];
  total: number;
  page: number;
  pageSize: number;
  loading: boolean;

  // 行业/股票列表（用于侧边栏）
  industries: { code: string; name: string; article_count: number }[];
  stocks: { code: string; name: string; article_count: number }[];

  // Actions
  setView: (view: ViewMode) => void;
  setSelectedIndustry: (code: string | null) => void;
  setSelectedStock: (code: string | null) => void;
  setSearchKeyword: (keyword: string) => void;
  setArticles: (articles: ArticleListItem[], total: number) => void;
  setPage: (page: number) => void;
  setLoading: (loading: boolean) => void;
  setIndustries: (industries: { code: string; name: string; article_count: number }[]) => void;
  setStocks: (stocks: { code: string; name: string; article_count: number }[]) => void;
  reset: () => void;
}

const initialState = {
  view: "timeline" as ViewMode,
  selectedIndustry: null,
  selectedStock: null,
  searchKeyword: "",
  articles: [],
  total: 0,
  page: 1,
  pageSize: 20,
  loading: false,
  industries: [],
  stocks: [],
};

export const useKnowledgeStore = create<KnowledgeState>((set) => ({
  ...initialState,

  setView: (view) => set({ view, page: 1, articles: [], selectedIndustry: null, selectedStock: null }),
  setSelectedIndustry: (code) => set({ selectedIndustry: code, page: 1, articles: [] }),
  setSelectedStock: (code) => set({ selectedStock: code, page: 1, articles: [] }),
  setSearchKeyword: (keyword) => set({ searchKeyword: keyword, page: 1 }),
  setArticles: (articles, total) => set({ articles, total }),
  setPage: (page) => set({ page }),
  setLoading: (loading) => set({ loading }),
  setIndustries: (industries) => set({ industries }),
  setStocks: (stocks) => set({ stocks }),
  reset: () => set(initialState),
}));
