import { EventType } from "./types";

// === 事件类型配置 ===
export const EVENT_TYPES: { value: EventType; label: string }[] = [
  { value: EventType.GEO_POLITICAL, label: "地缘政治" },
  { value: EventType.POLICY, label: "政策法规" },
  { value: EventType.EARNINGS, label: "财报季报" },
  { value: EventType.SUPPLY_CHAIN, label: "产业链分析" },
  { value: EventType.OTHER, label: "其他" },
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
