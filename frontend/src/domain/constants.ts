import { EventType } from "./types";

// === 事件类型配置 ===
export const EVENT_TYPES: { value: EventType; label: string }[] = [
  { value: EventType.GEO_POLITICAL, label: "地缘政治" },
  { value: EventType.POLICY, label: "政策法规" },
  { value: EventType.EARNINGS, label: "财报季报" },
  { value: EventType.SUPPLY_CHAIN, label: "产业链分析" },
];

// === 申万一级行业（31个） ===
export const SHENWAN_INDUSTRIES: string[] = [
  "农林牧渔",
  "基础化工",
  "钢铁",
  "有色金属",
  "电子",
  "汽车",
  "家用电器",
  "食品饮料",
  "纺织服装",
  "轻工制造",
  "医药生物",
  "公用事业",
  "交通运输",
  "房地产",
  "商贸零售",
  "社会服务",
  "银行",
  "非银金融",
  "综合",
  "建筑材料",
  "建筑装饰",
  "电力设备",
  "机械设备",
  "国防军工",
  "计算机",
  "传媒",
  "通信",
  "煤炭",
  "石油石化",
  "环保",
  "美容护理",
];

// === 新用户示例问题 ===
export const EXAMPLE_PROMPTS: { eventType: EventType; question: string }[] = [
  {
    eventType: EventType.GEO_POLITICAL,
    question: "美国对伊朗实施新一轮制裁，对A股有什么影响？",
  },
  {
    eventType: EventType.POLICY,
    question: "国家出台新能源汽车补贴政策，哪些行业会受益？",
  },
  {
    eventType: EventType.EARNINGS,
    question: "茅台季报净利润超预期20%，对白酒行业有什么影响？",
  },
];

// === 草稿本地存储 key 前缀 ===
export const DRAFT_KEY_PREFIX = "draft:analysis:";

// === 草稿保存阈值（字数） ===
export const DRAFT_MIN_LENGTH = 20;

// === 草稿防抖延迟（毫秒） ===
export const DRAFT_DEBOUNCE_MS = 1000;

// === 相似检测防抖延迟（毫秒） ===
export const SIMILARITY_DEBOUNCE_MS = 1000;

// === 默认分页大小 ===
export const DEFAULT_PAGE_SIZE = 20;

// === Agent 中文显示名映射 ===
export const AGENT_DISPLAY_NAMES: Record<string, string> = {
  market_analyst: "技术分析师",
  fundamentals_analyst: "基本面分析师",
  news_analyst: "新闻分析师",
  sentiment_analyst: "情绪分析师",
  bull_researcher: "看多研究员",
  bear_researcher: "看空研究员",
  research_manager: "研究主管",
  trader: "交易决策官",
  risky_debator: "激进派",
  safe_debator: "保守派",
  neutral_debator: "中立派",
  risk_judge: "风险裁决官",
};

// === Agent 角色形象化配置 ===
export interface AgentProfile {
  emoji: string;
  color: string;
  bgColor: string;
  borderColor: string;
  description: string;
  thinkingMessage: string;
}

export const AGENT_PROFILES: Record<string, AgentProfile> = {
  market_analyst: {
    emoji: "📊",
    color: "#3b82f6",
    bgColor: "#eff6ff",
    borderColor: "#bfdbfe",
    description: "扫描K线形态，分析均线系统与量价关系",
    thinkingMessage: "正在扫描K线形态，分析均线系统与量价关系...",
  },
  fundamentals_analyst: {
    emoji: "💰",
    color: "#15be53",
    bgColor: "#f0fdf4",
    borderColor: "#bbf7d0",
    description: "解读财务报表，评估估值水平与盈利能力",
    thinkingMessage: "正在解读财务报表，评估估值水平与盈利能力...",
  },
  news_analyst: {
    emoji: "📰",
    color: "#f59e0b",
    bgColor: "#fffbeb",
    borderColor: "#fde68a",
    description: "搜集近期新闻事件，评估信息面影响",
    thinkingMessage: "正在搜集近期新闻事件，评估信息面影响...",
  },
  sentiment_analyst: {
    emoji: "💭",
    color: "#a855f7",
    bgColor: "#faf5ff",
    borderColor: "#d8b4fe",
    description: "分析市场情绪指标，判断多空力量对比",
    thinkingMessage: "正在分析市场情绪指标，判断多空力量对比...",
  },
  bull_researcher: {
    emoji: "🐂",
    color: "#15be53",
    bgColor: "#f0fdf4",
    borderColor: "#bbf7d0",
    description: "从利好角度构建看多论证",
    thinkingMessage: "正在从利好角度构建看多论证...",
  },
  bear_researcher: {
    emoji: "🐻",
    color: "#ea2261",
    bgColor: "#fff1f2",
    borderColor: "#fecdd3",
    description: "从风险角度构建看空论证",
    thinkingMessage: "正在从风险角度构建看空论证...",
  },
  research_manager: {
    emoji: "⚖️",
    color: "#0891b2",
    bgColor: "#ecfeff",
    borderColor: "#a5f3fc",
    description: "综合多空观点，形成平衡判断",
    thinkingMessage: "正在综合多空观点，形成平衡判断...",
  },
  trader: {
    emoji: "📈",
    color: "#533afd",
    bgColor: "#f8f7ff",
    borderColor: "#d6d9fc",
    description: "基于分析结果，制定交易策略",
    thinkingMessage: "正在基于分析结果，制定交易策略...",
  },
  risky_debator: {
    emoji: "🔥",
    color: "#f59e0b",
    bgColor: "#fffbeb",
    borderColor: "#fde68a",
    description: "从高风险偏好视角评估收益空间",
    thinkingMessage: "正在从高风险偏好视角评估收益空间...",
  },
  safe_debator: {
    emoji: "🛡️",
    color: "#3b82f6",
    bgColor: "#eff6ff",
    borderColor: "#bfdbfe",
    description: "从安全边际角度评估下行风险",
    thinkingMessage: "正在从安全边际角度评估下行风险...",
  },
  neutral_debator: {
    emoji: "⚖️",
    color: "#a855f7",
    bgColor: "#faf5ff",
    borderColor: "#d8b4fe",
    description: "平衡激进与保守观点",
    thinkingMessage: "正在平衡激进与保守观点...",
  },
  risk_judge: {
    emoji: "👨‍⚖️",
    color: "#4f46e5",
    bgColor: "#eef2ff",
    borderColor: "#c7d2fe",
    description: "综合风险评估，给出最终风险定级",
    thinkingMessage: "正在综合风险评估，给出最终风险定级...",
  },
};

export const AGENT_PHASE_MAPPING: Record<string, string> = {
  market_analyst: "analysts",
  fundamentals_analyst: "analysts",
  news_analyst: "analysts",
  sentiment_analyst: "analysts",
  bull_researcher: "debate",
  bear_researcher: "debate",
  research_manager: "debate",
  trader: "trader",
  risky_debator: "risk",
  safe_debator: "risk",
  neutral_debator: "risk",
  risk_judge: "risk",
};

export const ANALYSIS_PHASE_LABELS: Record<string, string> = {
  analysts: "分析师阶段",
  debate: "投资辩论",
  trader: "交易决策",
  risk: "风险评估",
};

export const ANALYSIS_MODE_OPTIONS = [
  { value: "quick", label: "快速分析", desc: "仅技术面+基本面，约1分钟" },
  { value: "full", label: "深度分析", desc: "4位分析师+辩论+风险评估，约3-5分钟" },
];

export const DEFAULT_DEBATE_ROUNDS = 2;
export const DEFAULT_RISK_DEBATE_ROUNDS = 2;
