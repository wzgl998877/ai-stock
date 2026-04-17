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
export type SSEEventType = "content" | "title" | "summary" | "industries" | "error" | "done";

export interface SSEEvent {
  type: SSEEventType;
  data: string | string[];
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
