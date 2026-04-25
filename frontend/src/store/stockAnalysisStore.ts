import { create } from "zustand";
import { AnalysisMode, type AgentStatusEvent, type DebateEvent, type DecisionEvent, type ThinkingStepData } from "../domain/types";

interface ContentBlock {
  agent: string;
  type: "content" | "reasoning";
  text: string;
}

interface QuickAnalysisResult {
  market_summary: string;
  fundamentals_summary: string;
  brief_advice: string;
}

interface StockAnalysisState {
  // 输入状态
  stockCode: string;
  stockName: string;
  dataSource: string;
  analysisMode: AnalysisMode;
  validationLoading: boolean;
  validationValid: boolean;

  // 分析状态
  analysisState: "idle" | "running" | "done" | "error";
  currentPhase: string;
  agentStatuses: Record<string, string>;  // agent -> pending/running/done/failed
  agentReports: Record<string, string>;   // agent -> summary
  agentCompletedAt: Record<string, number>; // agent -> 完成时间戳(ms)
  debates: DebateEvent[];
  decision: DecisionEvent | null;
  content: string;
  thinkingSteps: ThinkingStepData[];

  // 细粒度流式状态（US2）
  contentBlocks: ContentBlock[];
  phaseProgress: Record<string, number>;

  // 快速分析结果（US4）
  quickAnalysisResult: QuickAnalysisResult | null;

  // 历史刷新触发器（US3）
  historyRefreshKey: number;

  // 结果
  title: string;
  summary: string;
  industries: string[];
  error: string;

  // Actions
  setStock: (code: string, name: string) => void;
  setDataSource: (source: string) => void;
  setMode: (mode: AnalysisMode) => void;
  setValidation: (loading: boolean, valid: boolean) => void;
  startAnalysis: () => void;
  updateAgentStatus: (event: AgentStatusEvent) => void;
  addAgentReport: (agent: string, summary: string) => void;
  addThinkingStep: (step: ThinkingStepData) => void;
  addDebate: (event: DebateEvent) => void;
  setDecision: (decision: DecisionEvent) => void;
  appendContent: (text: string) => void;
  updateStreamingContent: (agent: string, type: "content" | "reasoning", text: string) => void;
  setTitle: (title: string) => void;
  setSummary: (summary: string) => void;
  setIndustries: (industries: string[]) => void;
  setError: (error: string) => void;
  setQuickResult: (result: QuickAnalysisResult) => void;
  triggerHistoryRefresh: () => void;
  reset: () => void;
}

const initialState = {
  stockCode: "",
  stockName: "",
  dataSource: "",
  analysisMode: AnalysisMode.FULL,
  validationLoading: false,
  validationValid: false,
  analysisState: "idle" as const,
  currentPhase: "",
  agentStatuses: {},
  agentReports: {},
  agentCompletedAt: {},
  debates: [],
  decision: null,
  content: "",
  thinkingSteps: [] as ThinkingStepData[],
  contentBlocks: [] as ContentBlock[],
  phaseProgress: {} as Record<string, number>,
  quickAnalysisResult: null as QuickAnalysisResult | null,
  historyRefreshKey: 0,
  title: "",
  summary: "",
  industries: [],
  error: "",
};

export const useStockAnalysisStore = create<StockAnalysisState>((set) => ({
  ...initialState,

  setStock: (code, name) => set({ stockCode: code, stockName: name, validationValid: !!code }),
  setDataSource: (source) => set({ dataSource: source }),
  setMode: (mode) => set({ analysisMode: mode }),
  setValidation: (loading, valid) => set({ validationLoading: loading, validationValid: valid }),

  startAnalysis: () =>
    set({
      analysisState: "running",
      currentPhase: "analysts",
      agentStatuses: {},
      agentReports: {},
      debates: [],
      decision: null,
      content: "",
      thinkingSteps: [],
      contentBlocks: [],
      phaseProgress: {},
      quickAnalysisResult: null,
      title: "",
      summary: "",
      industries: [],
      error: "",
      dataSource: "",
    }),

  updateAgentStatus: (event) =>
    set((state) => {
      const completedAt = event.status === "done" ? Date.now() : state.agentCompletedAt[event.agent];
      return {
        agentStatuses: { ...state.agentStatuses, [event.agent]: event.status },
        agentCompletedAt: { ...state.agentCompletedAt, [event.agent]: completedAt },
        currentPhase: event.phase || state.currentPhase,
      };
    }),

  addAgentReport: (agent, summary) =>
    set((state) => ({
      agentReports: { ...state.agentReports, [agent]: summary },
    })),

  addThinkingStep: (step) =>
    set((state) => {
      const existing = state.thinkingSteps.findIndex(
        (s) => s.step === step.step
      );
      if (existing >= 0) {
        const updated = [...state.thinkingSteps];
        updated[existing] = step;
        return { thinkingSteps: updated };
      }
      return { thinkingSteps: [...state.thinkingSteps, step] };
    }),

  addDebate: (event) =>
    set((state) => ({
      debates: [...state.debates, event],
    })),

  setDecision: (decision) => set({ decision }),
  appendContent: (text) => set((state) => ({ content: state.content + text })),

  updateStreamingContent: (agent, type, text) =>
    set((state) => ({
      contentBlocks: [...state.contentBlocks, { agent, type, text }],
    })),

  setTitle: (title) => set({ title }),
  setSummary: (summary) => set({ summary }),
  setIndustries: (industries) => set({ industries }),
  setError: (error) => set({ analysisState: "error", error }),

  setQuickResult: (result) => set({ quickAnalysisResult: result }),
  triggerHistoryRefresh: () => set((state) => ({ historyRefreshKey: state.historyRefreshKey + 1 })),

  reset: () => set(initialState),
}));
