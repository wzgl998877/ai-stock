// === 事件类型枚举 ===
export enum EventType {
  GEO_POLITICAL = "geopolitical",
  POLICY = "policy",
  EARNINGS = "earnings",
  SUPPLY_CHAIN = "supply_chain",
  OTHER = "other",
}

// === 提醒状态枚举 ===
export enum ReminderStatus {
  PENDING = "pending",
  REMINDED = "reminded",
  ARCHIVED = "archived",
}

// === 股票引用 ===
export interface StockReference {
  code: string;
  name: string;
  industry?: string;
}

// === 文章（列表项） ===
export interface IndustryRefItem {
  code: string;
  name: string;
  chain_level?: number | null;
}

export interface StockRefItem {
  code: string;
  name: string;
}

export interface ArticleListItem {
  id: string;
  title: string;
  summary: string;
  industries: IndustryRefItem[];
  stocks: StockRefItem[];
  event_type: EventType;
  created_at: string;
  highlight?: string;
}

// === 文章（详情） ===
export interface ArticleDetail {
  id: string;
  title: string;
  summary: string;
  content: string;
  event_type: EventType;
  raw_input: string;
  industries: IndustryRefItem[];
  stocks: StockRefItem[];
  chain_table: ChainTableEntry[] | null;
  created_at: string;
  updated_at: string;
}

// === 产业链传导表条目 ===
export interface ChainTableEntry {
  level: number;
  industry: string;
  logic: string;
  direction: "受益" | "受损";
  degree: "高" | "中" | "低";
  timing: string;
  stocks: StockReference[];
}

// === 大事提醒 ===
export interface Reminder {
  id: string;
  title: string;
  event_date: string;
  industry_tags: string[] | null;
  status: ReminderStatus;
  remind_3day_sent: boolean;
  remind_today_sent: boolean;
  created_at: string;
}

// === 分页响应 ===
export interface PaginatedResponse<T> {
  total: number;
  page: number;
  page_size: number;
  items: T[];
}

// === SSE 事件类型 ===
export type SSEEventType = "thinking" | "reasoning" | "content" | "title" | "summary" | "industries" | "error" | "done";

export interface SSEEvent {
  type: SSEEventType;
  data: string | string[] | ThinkingStepData;
}

// === 思维链步骤 ===
export interface ThinkingStepData {
  step: string;        // classify / search / retrieve / reasoning
  status: "running" | "done" | "failed";
  message: string;
}

// === Chat 会话 ===
export interface ChatSessionType {
  id: string;
  title: string;
  event_type: string | null;
  created_at: string;
  updated_at: string;
}

// === Chat 消息 ===
export interface ChatMessageType {
  id: string;
  role: "user" | "assistant";
  content: string;
  reasoning: string;                              // 模型推理思考过程
  thinking_steps: ThinkingStepData[] | null;
  event_type: string | null;
  created_at: string;
}

// === 保存文章请求 ===
export interface SaveArticleDTO {
  title: string;
  summary: string;
  content: string;
  event_type: string;
  raw_input: string;
  industry_codes: string[];
  stock_refs: StockReference[];
  chain_table: ChainTableEntry[] | null;
}

// === 相似文章 ===
export interface SimilarArticleDTO {
  id: string;
  title: string;
  similarity: number;
}

// === 文章列表响应 ===
export type ArticleListResponseDTO = PaginatedResponse<ArticleListItem>;

// === 文章详情 DTO ===
export type ArticleDetailDTO = ArticleDetail;

// === 分析状态 ===
export enum AnalysisStatus {
  IDLE = "idle",
  STREAMING = "streaming",
  DONE = "done",
  ERROR = "error",
}

// === 个股分析 Agent 类型 ===
export enum AgentType {
  MARKET_ANALYST = "market_analyst",
  FUNDAMENTALS_ANALYST = "fundamentals_analyst",
  NEWS_ANALYST = "news_analyst",
  SENTIMENT_ANALYST = "sentiment_analyst",
  BULL_RESEARCHER = "bull_researcher",
  BEAR_RESEARCHER = "bear_researcher",
  RESEARCH_MANAGER = "research_manager",
  TRADER = "trader",
  RISKY_DEBATOR = "risky_debator",
  SAFE_DEBATOR = "safe_debator",
  NEUTRAL_DEBATOR = "neutral_debator",
  RISK_JUDGE = "risk_judge",
}

export enum AnalysisPhase {
  ANALYSTS = "analysts",
  DEBATE = "debate",
  TRADER = "trader",
  RISK = "risk",
  DONE = "done",
}

export enum AnalysisMode {
  QUICK = "quick",
  FULL = "full",
}

export interface StockAnalysisConfig {
  stock_code: string;
  stock_name: string;
  analysis_mode: AnalysisMode;
  debate_rounds: number;
  risk_debate_rounds: number;
}

export interface AgentStatusEvent {
  agent: string;
  phase: string;
  status: "running" | "done" | "failed";
}

export interface DebateEvent {
  speaker: string;
  round: number;
  content: string;
}

export interface AgentReportEvent {
  agent: string;
  summary: string;
  full_report?: string;
}

export interface DecisionEvent {
  action: string;
  target_price: number;
  stop_loss_price: number;
  confidence: number;
  risk_score: number;
  reasoning: string;
}

export interface StockCandidate {
  code: string;
  name: string;
  market: string;
}

export interface StockValidationResult {
  valid: boolean;
  stock_code?: string;
  stock_name?: string;
  market?: string;
  multiple?: boolean;
  candidates?: StockCandidate[];
  message?: string;
  /** 数据来源："database" | "network" */
  source?: string;
}

// 扩展 SSE 事件类型
export type StockSSEEventType =
  | SSEEventType
  | "agent_status"
  | "agent_report"
  | "debate"
  | "decision";

export interface StockSSEEvent {
  type: StockSSEEventType;
  data: string | string[] | ThinkingStepData | AgentStatusEvent | AgentReportEvent | DebateEvent | DecisionEvent;
}

// === 分析记录 ===
export interface AnalysisDetailItem {
  agent_name: string;
  phase: string;
  status: string;
  summary: string;
  full_report: string;
  thinking_steps?: Record<string, unknown>[];
  debate_data?: Record<string, unknown>;
  completed_at: string | null;
}

export interface AnalysisDecision {
  action: string;
  target_price: number;
  stop_loss_price: number;
  confidence: number;
  risk_score: number;
  reasoning: string;
}

export interface AnalysisRecordListItem {
  id: string;
  title: string;
  summary: string;
  status: "in_progress" | "completed" | "stopped" | "pending" | "failed";
  analysis_mode: "quick" | "full";
  stocks: { code: string; name: string }[];
  industries: { code: string }[];
  progress: { completed: number; total: number };
  details: AnalysisDetailItem[];
  decision: AnalysisDecision | null;
  created_at: string;
  updated_at: string;
}

export interface AnalysisRecordDetail {
  id: string;
  title: string;
  summary: string;
  content: string;
  status: "in_progress" | "completed" | "stopped" | "pending" | "failed";
  analysis_mode: "quick" | "full";
  current_phase?: string;
  raw_input: string;
  stocks: { code: string; name: string }[];
  industries: { code: string }[];
  details: AnalysisDetailItem[];
  decision: AnalysisDecision | null;
  created_at: string;
  updated_at: string;
}

export interface AnalysisRecordListResponse {
  total: number;
  page: number;
  page_size: number;
  items: AnalysisRecordListItem[];
}
