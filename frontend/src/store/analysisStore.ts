/** 分析状态管理 (Zustand) */

import { create } from "zustand";
import { AnalysisStatus } from "../domain/types";

interface AnalysisState {
  status: AnalysisStatus;
  result: string; // 累积的分析内容 (Markdown)
  title: string;
  summary: string;
  industries: string[];
  error: string | null;

  // Actions
  startAnalysis: () => void;
  appendContent: (chunk: string) => void;
  setTitle: (title: string) => void;
  setSummary: (summary: string) => void;
  setIndustries: (industries: string[]) => void;
  setError: (error: string) => void;
  reset: () => void;
  done: () => void;
}

const initialState = {
  status: AnalysisStatus.IDLE,
  result: "",
  title: "",
  summary: "",
  industries: [],
  error: null,
};

export const useAnalysisStore = create<AnalysisState>((set) => ({
  ...initialState,

  startAnalysis: () =>
    set({
      status: AnalysisStatus.STREAMING,
      result: "",
      title: "",
      summary: "",
      industries: [],
      error: null,
    }),

  appendContent: (chunk) =>
    set((state) => ({ result: state.result + chunk })),

  setTitle: (title) => set({ title }),

  setSummary: (summary) => set({ summary }),

  setIndustries: (industries) => set({ industries }),

  setError: (error) => set({ status: AnalysisStatus.ERROR, error }),

  done: () => set({ status: AnalysisStatus.DONE }),

  reset: () => set(initialState),
}));
