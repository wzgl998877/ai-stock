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
  fullContent: string;
  industries: string[];
  error: string;

  // 查看模式（从记录回看）
  viewMode: boolean;
  viewRecordId: string;

  // 上次分析中的股票（用于 idle 界面提示）
  lastAnalyzingStock: { code: string; name: string; recordId: string } | null;

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
  setFullContent: (content: string) => void;
  setIndustries: (industries: string[]) => void;
  setError: (error: string) => void;
  setQuickResult: (result: QuickAnalysisResult) => void;
  triggerHistoryRefresh: () => void;
  loadFromRecord: (data: {
    recordId: string;
    title: string;
    summary: string;
    fullContent?: string;
    industries: string[];
    agentReports: Record<string, string>;
    debates: DebateEvent[];
    decision: DecisionEvent | null;
    agentCompletedAt?: Record<string, number>;
    analysisMode?: AnalysisMode;
    status?: string;  // 记录实际状态：in_progress / completed / stopped
  }) => void;
  loadRunningState: (data: {
    currentPhase: string;
    agents: Record<string, { status: string; summary?: string; full_report?: string }>;
    debates: any[];
    decision: any;
    title: string;
    summary: string;
    industries: string[];
    fullContent?: string;
  }) => void;
  setAnalysisState: (state: "idle" | "running" | "done" | "error") => void;
  setCurrentPhase: (phase: string) => void;
  setLastAnalyzingStock: (stock: { code: string; name: string; recordId: string } | null) => void;
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
  fullContent: "",
  industries: [],
  error: "",
  viewMode: false,
  viewRecordId: "",
  lastAnalyzingStock: null,
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
      fullContent: "",
      industries: [],
      error: "",
      dataSource: "",
      viewMode: false,
      viewRecordId: "",
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
  setFullContent: (content) => set({ fullContent: content }),
  setIndustries: (industries) => set({ industries }),
  setError: (error) => set({ analysisState: "error", error }),

  setQuickResult: (result) => set({ quickAnalysisResult: result }),
  triggerHistoryRefresh: () => set((state) => ({ historyRefreshKey: state.historyRefreshKey + 1 })),

  loadFromRecord: (data) =>
    set({
      analysisState: data.status === "in_progress" || data.status === "running" ? "running" : "done",
      viewMode: true,
      viewRecordId: data.recordId,
      title: data.title || "",
      summary: data.summary || "",
      fullContent: data.fullContent || "",
      industries: data.industries || [],
      agentReports: data.agentReports || {},
      debates: data.debates || [],
      decision: data.decision || null,
      agentCompletedAt: data.agentCompletedAt || {},
      analysisMode: data.analysisMode || AnalysisMode.FULL,
    }),

  loadRunningState: (data: {
    currentPhase: string;
    agents: Record<string, { status: string; summary?: string; full_report?: string }>;
    debates: any[];
    decision: any;
    title: string;
    summary: string;
    industries: string[];
  }) =>
    set((state) => {
      const agentReports: Record<string, string> = { ...state.agentReports };
      const agentStatuses: Record<string, string> = {};
      for (const [key, val] of Object.entries(data.agents)) {
        if (val.summary || val.full_report) {
          agentReports[key] = val.summary || val.full_report || "";
        }
        agentStatuses[key] = val.status || "done";
      }
      return {
        currentPhase: data.currentPhase || state.currentPhase,
        agentReports,
        agentStatuses,
        debates: data.debates || state.debates,
        decision: data.decision || state.decision,
        title: data.title || state.title,
        summary: data.summary || state.summary,
        industries: data.industries || state.industries,
      };
    }),

  setAnalysisState: (state) => set({ analysisState: state }),
  setCurrentPhase: (phase) => set({ currentPhase: phase }),
  setLastAnalyzingStock: (stock) => set({ lastAnalyzingStock: stock }),

  reset: () => set((state) => ({
    ...initialState,
    lastAnalyzingStock: state.lastAnalyzingStock, // 保留上次分析股票信息
    stockCode: state.stockCode, // 保留已选股票代码
    stockName: state.stockName, // 保留已选股票名称
    validationValid: state.validationValid,
  })),
}));
