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
  sentiment?: string | null;
}

// === 文章（列表项） ===
export interface IndustryRefItem {
  code: string;
  name: string;
  chain_level?: number | null;
  sentiment?: string | null;
}

export interface StockRefItem {
  code: string;
  name: string;
  sentiment?: string | null;
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
  session_type?: string;  // 'event_analysis' | 'stock_analysis'
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
  summary?: string;                               // AI生成的文章摘要（仅assistant）
  industries?: string[];                          // AI生成的行业标签（仅assistant）
  created_at: string;
}

// === 行业利好/利空标注 ===
export interface IndustrySentiment {
  name: string;
  sentiment: string;  // positive / negative
}

// === 保存文章请求 ===
export interface SaveArticleDTO {
  title: string;
  summary: string;
  content: string;
  event_type: string;
  raw_input: string;
  industry_codes: string[];
  industry_sentiments: IndustrySentiment[];
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
  expected_return: number;
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
  | "analysis_id"
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

// ============================================================================
// 缠论策略监控与信号回测（模块三）
// ============================================================================

/** 缠论周期：日线 / 30 分钟 */
export type ChanlunPeriod = "daily" | "m30";

/** 缠论信号类型：一/二/三类买、一/二/三类卖 */
export type SignalType = "buy1" | "buy2" | "buy3" | "sell1" | "sell2" | "sell3";

/** 自选股徽标状态 */
export type SignalStatus =
  | "monitored"           // 监控中且有近期信号
  | "monitored_nodata"    // 监控中但无信号
  | "disabled"            // 已关闭该周期监控
  | "insufficient_data";  // 数据不足

/** 信号结构级别 */
export type StructureLevel = "stroke" | "segment";

/** 单条信号摘要（徽标 Tooltip / K 线 markPoint 用） */
export interface SignalSummary {
  signal_type: SignalType | null;
  signal_time: string | null;
  confirmed_at: string | null;
  trigger_price: number | null;
  /** 新鲜度（后端计算）：false=历史信号（超出新鲜度窗口，前端置灰） */
  is_fresh?: boolean | null;
}

/** 自选股列表信号行（双周期） */
export interface WatchlistSignalItem {
  stock_code: string;
  stock_name: string;
  daily: SignalSummary | null;
  m30: SignalSummary | null;
  daily_status: SignalStatus;
  m30_status: SignalStatus;
}

/** 缠论结构端点 */
export interface StructurePoint {
  time: string;
  price: number;
}

/** 笔 */
export interface Stroke {
  start: StructurePoint;
  end: StructurePoint;
  direction: "up" | "down";
  confirmed: boolean;
}

/** 线段 */
export interface Segment {
  start: StructurePoint;
  end: StructurePoint;
  direction: "up" | "down";
  confirmed: boolean;
}

/** 中枢 */
export interface Zhongshu {
  zd: number;        // 中枢下沿
  zg: number;        // 中枢上沿
  dd: number;        // 最低点
  gg: number;        // 最高点
  enter_time: string;
  exit_time: string | null;
}

/** 单股结构快照（K 线渲染） */
export interface StructureData {
  strokes: Stroke[];
  segments: Segment[];
  zhongshu: Zhongshu[];
  last_kline_time: string;
  algo_version: string;
}

/** K 线买卖点标注（markPoint） */
export interface SignalMark {
  signal_type: SignalType;
  time: string;
  price: number;
  confirmed_at: string;
  level: 1 | 2 | 3;  // 一/二/三类
}

/** 信号历史记录 */
export interface SignalHistoryItem {
  signal_type: SignalType;
  period: ChanlunPeriod;
  structure_level: StructureLevel;
  signal_time: string;
  confirmed_at: string | null;
  trigger_price: number | null;
  algo_version: string;
  status: "confirmed" | "invalidated";
  invalidated_reason: string | null;
  /** 微信推送结果：success=已推送 / skipped=跳过(无token) / failed=发送失败 / null=未尝试 */
  push_status: "success" | "skipped" | "failed" | null;
  push_message_id: string | null;
  push_time: string | null;
}

/** 计算任务状态（日线 / m30） */
export interface RunStatusItem {
  last_run_at: string | null;
  duration_ms: number | null;
  total: number;
  success: number;
  failed: number;
  failed_detail: { stock_code: string; reason: string }[] | null;
  algo_version: string;
}

/** 计算任务状态响应（GET /run-status，双周期） */
export interface RunStatus {
  daily: RunStatusItem | null;
  m30: RunStatusItem | null;
  algo_version?: string;
}

/** 监控配置 */
export interface MonitorConfig {
  daily_enabled: boolean;
  m30_enabled: boolean;
}

// === 回测 ===
export type BacktestRange = "1y" | "3y" | "5y";
export type BacktestWindow = 5 | 10 | 20 | 60;

export interface BacktestReportListItem {
  report_id: number;
  range_label: BacktestRange;
  start_date: string;
  end_date: string;
  stock_count: number;
  signal_total: number;
  algo_version: string;
  status: "running" | "done" | "failed";
  create_time: string;
}

export interface BacktestSummaryCell {
  period: ChanlunPeriod;
  signal_type: SignalType;
  window: BacktestWindow;
  sample: number;
  win_rate: number;          // 0-1
  avg_return: number;
  median_return: number;
  profit_loss_ratio: number;
  note: "sample_insufficient" | "window_incomplete" | null;
}

export interface BacktestReportDetail {
  meta: {
    range_label: BacktestRange;
    stock_count: number;
    signal_total: number;
    excluded_invalidated: number;
    algo_version: string;
    benchmark_return: number | null;
    finished_at: string | null;
  };
  summary: BacktestSummaryCell[];
}

export interface BacktestSignalDetailItem {
  stock_code: string;
  signal_type: SignalType;
  signal_time: string;
  trigger_price: number | null;
  ret_5: number | null;
  ret_10: number | null;
  ret_20: number | null;
  ret_60: number | null;
  window_complete: boolean;
}

// === 缠论 SSE 事件 ===
export type StrategySSEEvent =
  | { event: "calc_started"; data: { period: ChanlunPeriod; total: number } }
  | { event: "calc_progress"; data: { stock_code: string; status: "done" | "skipped" | "failed"; reason: string | null } }
  | { event: "data_error"; data: { message: string } }
  | { event: "calc_completed"; data: { total: number; success: number; failed: number; duration_ms: number; algo_version: string } }
  | { event: "calc_error"; data: { message: string } }
  | { event: "backtest_started"; data: { range: BacktestRange; stock_count: number } }
  | { event: "backtest_progress"; data: { stock_code: string; signals_found: number } }
  | { event: "backtest_completed"; data: { report_id: number; signal_total: number; excluded_invalidated: number; duration_ms: number } }
  | { event: "backtest_error"; data: { message: string } };
