/**
 * StockAnalysisDebugPage -- 个股分析调试页面（写死数据，不调用后端）
 *
 * 用于快速调试 UI 效果，通过 URL 参数切换不同状态：
 *   /stock-analysis-debug?debug=idle          -> 初始配置态（增强版）
 *   /stock-analysis-debug?debug=running       -> 分析进行中（深度模式，全部阶段有数据）
 *   /stock-analysis-debug?debug=done&mode=full -> 分析完成态（深度）
 *   /stock-analysis-debug?debug=done&mode=quick -> 分析完成态（快速）
 *   /stock-analysis-debug?debug=running-live  -> 动画加载中
 */

import React, { useCallback, useEffect, useState } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { Button, Typography, Card, Steps, Spin, Alert, Space, Divider, Badge, Tag, Modal, Tabs, Progress } from "antd";
import {
  PlayCircleOutlined,
  RedoOutlined,
  StockOutlined,
  HistoryOutlined,
  SwapOutlined,
  DatabaseOutlined,
  TeamOutlined,
  DollarOutlined,
  SafetyCertificateOutlined,
  LineChartOutlined,
  FundOutlined,
  ReadOutlined,
  CheckCircleOutlined,
  SyncOutlined,
  ArrowUpOutlined,
  ArrowDownOutlined,
  ClockCircleOutlined,
  RightOutlined,
  FileTextOutlined,
  ThunderboltOutlined,
  ExperimentOutlined,
} from "@ant-design/icons";
import StockSearchInput from "../components/stock-analysis/StockSearchInput";
import SystemStatusBar from "../components/stock-analysis/SystemStatusBar";
import ModeSelectionCards from "../components/stock-analysis/ModeSelectionCards";
import AgentReportCard from "../components/stock-analysis/AgentReportCard";
import DebateTimeline from "../components/stock-analysis/DebateTimeline";
import DecisionCard from "../components/stock-analysis/DecisionCard";
import AnalysisHistoryList from "../components/stock-analysis/AnalysisHistoryList";
import RiskAssessmentSection from "../components/stock-analysis/RiskAssessmentSection";
import SummaryCard from "../components/stock-analysis/SummaryCard";
import SectionHeader from "../components/stock-analysis/SectionHeader";
import ThinkingChain from "../components/chat/ThinkingChain";
import { AGENT_PROFILES } from "../domain/constants";
import { useStockAnalysisStore } from "../store/stockAnalysisStore";
import { ANALYSIS_PHASE_LABELS } from "../domain/constants";
import { AnalysisMode } from "../domain/types";
import type { DebateEvent, DecisionEvent } from "../domain/types";

const { Text, Title } = Typography;

const PHASE_ORDER = ["analysts", "debate", "trader", "risk"];

// ============================================================
// Mock 数据
// ============================================================

/** 分析维度展示配置（只读，随模式切换） */
interface AnalysisDimDisplay {
  label: string;
  icon: React.ReactNode;
  color: string;
}

const FULL_DIMS: AnalysisDimDisplay[] = [
  { label: "技术面", icon: <LineChartOutlined />, color: "#3b82f6" },
  { label: "基本面", icon: <FundOutlined />, color: "#8b5cf6" },
  { label: "多空辩论", icon: <SwapOutlined />, color: "#f59e0b" },
  { label: "风险评估", icon: <SafetyCertificateOutlined />, color: "#ef4444" },
];

const QUICK_DIMS: AnalysisDimDisplay[] = FULL_DIMS.slice(0, 2);

/** 分析师待命卡片数据 */
interface AnalystReadyCard {
  icon: React.ReactNode;
  name: string;
  color: string;
  description: string;
  status: "ready" | "waiting";
}

const FULL_ANALYSTS: AnalystReadyCard[] = [
  { icon: <LineChartOutlined />, name: "技术面分析师", color: "#3b82f6", description: "分析K线形态、均线系统、MACD/KDJ信号", status: "ready" },
  { icon: <FundOutlined />, name: "基本面分析师", color: "#8b5cf6", description: "评估财务指标、估值水平、盈利能力", status: "ready" },
  { icon: <ReadOutlined />, name: "新闻舆情哨兵", color: "#f59e0b", description: "扫描 7 日新闻，识别利好/利空舆情信号", status: "waiting" },
  { icon: <SafetyCertificateOutlined />, name: "风险评估官", color: "#ef4444", description: "多维度量化风险，给出安全边际建议", status: "waiting" },
];

const QUICK_ANALYSTS: AnalystReadyCard[] = [
  { icon: <LineChartOutlined />, name: "技术面分析师", color: "#3b82f6", description: "分析K线形态、均线系统、MACD/KDJ信号", status: "ready" },
  { icon: <FundOutlined />, name: "基本面分析师", color: "#8b5cf6", description: "评估财务指标、估值水平、盈利能力", status: "ready" },
];

/** 最近分析 Mock */
const MOCK_RECENT_ANALYSES = [
  { id: "1", stockCode: "600519", stockName: "贵州茅台", mode: "full" as const, status: "completed" as const, date: "2026-04-24 15:32" },
  { id: "2", stockCode: "000858", stockName: "五粮液", mode: "quick" as const, status: "completed" as const, date: "2026-04-23 10:18" },
  { id: "3", stockCode: "300750", stockName: "宁德时代", mode: "full" as const, status: "in_progress" as const, date: "2026-04-22 09:45" },
];

/** 市场环境快照 Mock */
const MOCK_MARKET_INDICES = [
  { name: "上证指数", value: "3286.42", change: "+0.58%", up: true },
  { name: "深证成指", value: "10892.15", change: "+0.72%", up: true },
  { name: "创业板指", value: "2198.33", change: "-0.15%", up: false },
];

/** 数据就绪状态 Mock */
const MOCK_DATA_STATUS = {
  dailyRange: { label: "日线数据", value: "2024-04 ~ 2026-04", status: "ok" as const },
  financialQuarter: { label: "财务数据", value: "2025Q3", status: "ok" as const },
  newsCount: { label: "新闻舆情", value: "128 条（7日）", status: "ok" as const },
};

/** 阶段耗时 Mock */
const MOCK_PHASE_TIMINGS: Record<string, { started: string; duration: string; completed?: string }> = {
  analysts: { started: "15:32:08", duration: "45s", completed: "15:32:53" },
  debate: { started: "15:32:55", duration: "32s", completed: "15:33:27" },
  trader: { started: "15:33:29", duration: "18s", completed: "15:33:47" },
  risk: { started: "15:33:49", duration: "22s", completed: "15:34:11" },
};

/** Mock 实时日志 */
const MOCK_LIVE_LOGS = [
  { time: "15:32:08", type: "info" as const, msg: "初始化分析流程，加载 600519 数据" },
  { time: "15:32:09", type: "success" as const, msg: "日线数据加载完成（730条）" },
  { time: "15:32:10", type: "info" as const, msg: "技术面分析师开始工作..." },
  { time: "15:32:15", type: "success" as const, msg: "MACD/RSI/MA 指标计算完成" },
  { time: "15:32:20", type: "info" as const, msg: "基本面分析师开始工作..." },
  { time: "15:32:25", type: "success" as const, msg: "2025Q3 财报数据提取完成" },
  { time: "15:32:30", type: "info" as const, msg: "新闻舆情哨兵开始扫描..." },
  { time: "15:32:35", type: "success" as const, msg: "7日舆情数据采集完成（128条）" },
  { time: "15:32:40", type: "info" as const, msg: "市场情绪分析开始..." },
  { time: "15:32:45", type: "success" as const, msg: "资金流向/机构评级分析完成" },
  { time: "15:32:53", type: "success" as const, msg: "分析师阶段完成 ✓" },
  { time: "15:32:55", type: "warning" as const, msg: "多空辩论开始（Round 1/3）" },
  { time: "15:33:05", type: "info" as const, msg: "bull_researcher: 提价预期是核心催化剂" },
  { time: "15:33:10", type: "info" as const, msg: "bear_researcher: 量价背离是隐忧" },
  { time: "15:33:15", type: "info" as const, msg: "neutral_debator: 区分短期和长期逻辑" },
  { time: "15:33:20", type: "warning" as const, msg: "多空辩论 Round 2/3" },
  { time: "15:33:27", type: "success" as const, msg: "辩论阶段完成 ✓" },
  { time: "15:33:29", type: "info" as const, msg: "交易决策师开始综合研判..." },
  { time: "15:33:47", type: "success" as const, msg: "决策输出完成：分批建仓" },
  { time: "15:33:49", type: "warning" as const, msg: "风险评估开始..." },
  { time: "15:34:00", type: "info" as const, msg: "风险评分：35/100（低风险）" },
  { time: "15:34:11", type: "success" as const, msg: "分析全部完成 ✓" },
];

const MOCK_AGENT_REPORTS_FULL: Record<string, string> = {
  market_analyst:
    "## 技术面分析总结（贵州茅台 600519）\n" +
    "**核心观点：** 短期均线死叉，但中长期趋势仍向上。成交量萎缩表明抛压减轻，反弹窗口临近。\n" +
    "### 关键数据\n" +
    "- 当前价格：**1685.00 元**\n" +
    "- 20 日均线：1702.30 元\n" +
    "- 60 日均线：1623.50 元\n" +
    "- MACD：-3.21（死叉第 5 日）\n" +
    "- RSI(14)：42.3（接近超卖区）\n" +
    "### 技术形态判断\n" +
    "日线级别处于 60 日均线支撑上方，但短期跌破 20 日均线。量能持续萎缩，近 5 日平均成交量较前 20 日下降约 **23%**，表明多空双方均趋于谨慎。\n" +
    "### 支撑与阻力位（元）\n" +
    "- 第一支撑位：**1620**（60 日均线附近）\n" +
    "- 第二支撑位：**1550**（前期密集成交区）\n" +
    "- 第一阻力位：**1705**（20 日均线）\n" +
    "- 第二阻力位：**1750**（前高区域）\n" +
    "### 综合评估（1-10 分）\n" +
    "- 短期趋势：5/10（中性偏弱）\n" +
    "- 中期趋势：6.5/10（偏多）\n" +
    "- 长期趋势：7/10（偏多）\n" +
    "- 综合评分：**6.2/10**\n" +
    "> 技术面结论：中期偏多，短期需等待企稳信号。若价格在 1620 附近企稳反弹，可视为买入机会。",

  fundamentals_analyst:
    "## 基本面分析总结（贵州茅台 600519）\n" +
    "**核心观点：** 业绩增长稳健，估值处于历史中位偏上。白酒行业龙头地位稳固，长期逻辑清晰。\n" +
    "### 核心财务指标（2025Q3）\n" +
    "- 营业收入：**1246.8 亿元**（同比 +14.2%）\n" +
    "- 归母净利润：**685.3 亿元**（同比 +13.8%）\n" +
    "- 毛利率：**91.6%**（行业最高水平）\n" +
    "- ROE：**28.5%**（连续 5 年 >25%）\n" +
    "- 经营现金流：**723.6 亿元**\n" +
    "### 估值分析\n" +
    "- 当前 PE(TTM)：**31.2x**\n" +
    "- 近 5 年 PE 中位数：35.6x（当前低于中位数约 **12%**）\n" +
    "- 近 5 年 PE 分位数：38%\n" +
    "### 行业地位与竞争优势\n" +
    "茅台作为白酒行业绝对龙头，品牌护城河深厚。高端白酒市场份额约占 **45%**，具备持续提价能力。但需关注：1）消费降级趋势下的量价承压；2）渠道库存压力。\n" +
    "### 综合评估（1-10 分）\n" +
    "- 盈利能力：9/10（极强）\n" +
    "- 成长性：7/10（稳健）\n" +
    "- 估值合理性：6/10（合理偏贵）\n" +
    "- 综合评分：**7.3/10**\n" +
    "> 基本面结论：质地优秀，当前估值合理，长期持有价值明确。",

  news_analyst:
    "## 新闻与舆情分析总结（贵州茅台 600519）\n" +
    "**核心观点：** 近期舆情偏正面，主要围绕茅台提价预期与渠道改革。但需注意消费降级叙事的潜在风险。\n" +
    "### 近 7 日舆情概览（情感倾向）\n" +
    "- 正面：**62%**（提价预期、中秋备货、渠道改革）\n" +
    "- 中性：25%\n" +
    "- 负面：**13%**（消费降级、飞天茅台批价回落）\n" +
    "### 热点话题追踪（声量 Top3）\n" +
    "1. **茅台提价预期**（声量 3200+）：市场对茅台出厂价提价预期升温，多家券商认为提价概率超 **60%**\n" +
    "2. **中秋旺季备货**（声量 2800+）：经销商反馈今年中秋备货量同比增长约 **5-8%**\n" +
    "3. **渠道数字化改革**（声量 1500+）：茅台 i 茅台平台注册用户突破 **5000 万**\n" +
    "### 风险提示（负面舆情摘要）\n" +
    "- 飞天茅台批价从 2750 回落至 **2450** 附近，部分市场参与者担忧需求走弱。\n" +
    "- 消费降级叙事下，市场对高端白酒的长期增速预期有所下调。\n" +
    "### 综合评估（1-10 分）\n" +
    "- 舆情情感：7/10（偏正面）\n" +
    "- 舆情风险：4/10（较低）\n" +
    "- 综合评分：**6.5/10**",

  sentiment_analyst:
    "## 市场情绪分析总结（贵州茅台 600519）\n" +
    "**核心观点：** 市场情绪偏谨慎乐观。资金流向数据显示北向资金近 5 日净流入约 **8.2 亿元**。\n" +
    "### 情绪指标一览（满分 100）\n" +
    "- 社交媒体情绪指数：**65**（偏乐观）\n" +
    "- 专业机构情绪指数：**70**（偏乐观）\n" +
    "- 资金流向情绪指数：**62**（小幅流入）\n" +
    "- 综合情绪指数：**66**（偏乐观）\n" +
    "### 资金流向（近 5 日）\n" +
    "- 北向资金净流入：**+8.2 亿元**\n" +
    "- 主力净流出：-3.5 亿元（短期波动属正常）\n" +
    "### 机构评级（近 30 日）\n" +
    "- 买入：**18 家**\n" +
    "- 增持：6 家，中性：3 家，卖出：0 家\n" +
    "- 平均目标价：**1980 元**（较当前价格溢价约 **17.5%**）\n" +
    "### 综合评估（1-10 分）\n" +
    "- 市场情绪：6.6/10（偏乐观）\n" +
    "- 综合评分：**6.6/10**",
};

const MOCK_AGENT_REPORTS_QUICK: Record<string, string> = {
  market_analyst: MOCK_AGENT_REPORTS_FULL.market_analyst,
  fundamentals_analyst: MOCK_AGENT_REPORTS_FULL.fundamentals_analyst,
};

const MOCK_DEBATES: DebateEvent[] = [
  {
    speaker: "bull_researcher",
    round: 1,
    content: "**看多理由：** 提价预期是核心催化剂。茅台出厂价已近 3 年未调整，在当前通胀环境下提价空间约 10-15%。提价直接增厚利润约 **120-180 亿元/年**（按当前销量测算）。叠加中秋旺季，短期弹性可观。",
  },
  {
    speaker: "bear_researcher",
    round: 1,
    content: "**看空理由：** 提价逻辑存在前提矛盾。当前飞天茅台批价已从 2750 回落至 2450，说明终端需求并非无限。若在批价下行期强行提价出厂价，可能进一步压制经销商利润，加剧渠道库存积压。**量价背离**是最大的隐忧。",
  },
  {
    speaker: "neutral_debator",
    round: 1,
    content: "**中立视角：** 需区分短期和长期逻辑。短期看，批价回落确实压制提价窗口，但若消费数据企稳（9 月社零数据是关键），提价窗口可能重新打开。中长期看，茅台的品牌护城河和稀缺性仍然是 A 股中**确定性最高**的资产之一。",
  },
  {
    speaker: "bull_researcher",
    round: 2,
    content: "**回应看空：** 渠道库存并非结构性问题。茅台通过 i 茅台平台实现渠道扁平化，2025H2 直销占比已提升至 **48%**。经销商库存周期从过去的 30+ 天缩短至 **15-20 天**，风险大幅降低。提价后利润空间对经销商仍有吸引力。",
  },
  {
    speaker: "bear_researcher",
    round: 2,
    content: "**回应看多：** 直销占比提升虽好，但前提是总需求稳定。若宏观经济持续承压，高端白酒的消费场景（商务宴请、礼品）会首当其冲。参考 2013-2014 年，茅台批价曾从 2300 跌至 **850**，当前估值已隐含了过于乐观的预期。历史教训不可遗忘。",
  },
];

const MOCK_DECISION: DecisionEvent = {
  action: "分批建仓（逢跌买入）",
  target_price: 1980,
  stop_loss_price: 1750,
  confidence: 65,
  risk_score: 35,
  reasoning:
    "**综合研判：** 基本面与技术面共振偏多，但短期技术面死叉信号尚未完全消除，建议分批建仓。\n" +
    "\n**操作建议：**\n" +
    "- 第一笔（30%）：现价 1685 附近轻仓试水，止损位 1550（-8%）\n" +
    "- 第二笔（40%）：若股价回落至 1620（60 日均线）企稳，加仓至 70%\n" +
    "- 第三笔（30%）：突破 1705（20 日均线）且放量，完成建仓\n" +
    "\n**目标价与风控：**\n" +
    "- 短期目标价：**1800 元**（+6.8%，基于前高测算）\n" +
    "- 中期目标价：**1980 元**（+17.5%，基于券商平均目标价）\n" +
    "- 止损价：**1550 元**（-8%，跌破前期密集成交区）\n" +
    "- 预期风险收益比：**1:2.2**（止损 8% vs 中期目标 17.5%）\n" +
    "\n**核心风险提示：** 提价预期落空、宏观经济下行、消费超预期走弱。若飞天茅台批价跌破 2300，应重新评估策略。",
};

const MOCK_THINKING_STEPS = [
  { step: "classify", status: "done" as const, message: "识别分析类型：个股深度分析" },
  { step: "data_fetch", status: "done" as const, message: "获取 600519 行情数据（日线/周线/月线）" },
  { step: "technical_analysis", status: "done" as const, message: "技术面指标计算完成（MACD/RSI/MA）" },
  { step: "fundamental_analysis", status: "done" as const, message: "基本面数据提取完成（财务/估值）" },
  { step: "news_analysis", status: "done" as const, message: "新闻舆情采集完成（7日舆情，情感分析）" },
  { step: "sentiment_analysis", status: "done" as const, message: "市场情绪分析完成（资金流向/机构评级）" },
];

const MOCK_AGENT_STATUSES_FULL: Record<string, string> = {
  market_analyst: "done",
  fundamentals_analyst: "done",
  news_analyst: "done",
  sentiment_analyst: "done",
};

const MOCK_AGENT_STATUSES_QUICK: Record<string, string> = {
  market_analyst: "done",
  fundamentals_analyst: "done",
};

// ============================================================
// 小型子组件
// ============================================================

/** 分析维度芯片（只读展示，不可操作） */
const DimDisplayChip: React.FC<{ dim: AnalysisDimDisplay }> = ({ dim }) => (
  <div
    style={{
      display: "inline-flex",
      alignItems: "center",
      gap: 6,
      padding: "6px 14px",
      borderRadius: 20,
      border: `1.5px solid ${dim.color}40`,
      background: `${dim.color}08`,
      color: dim.color,
      fontSize: 13,
      fontWeight: 500,
      userSelect: "none",
    }}
  >
    {dim.icon}
    {dim.label}
  </div>
);

/** 分析师待命卡片 */
const AnalystReadyCardItem: React.FC<{ card: AnalystReadyCard }> = ({ card }) => (
  <div
    style={{
      display: "flex",
      alignItems: "flex-start",
      gap: 12,
      padding: "12px 16px",
      borderRadius: 10,
      border: "1px solid #f0f0f0",
      background: card.status === "ready" ? "#fafaff" : "#fafafa",
      transition: "all 0.2s ease",
    }}
  >
    <div
      style={{
        width: 36,
        height: 36,
        borderRadius: 8,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: card.status === "ready" ? `${card.color}15` : "#f0f0f0",
        color: card.status === "ready" ? card.color : "#d9d9d9",
        fontSize: 16,
        flexShrink: 0,
      }}
    >
      {card.icon}
    </div>
    <div style={{ flex: 1, minWidth: 0 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <span style={{ fontSize: 13, fontWeight: 500, color: "#1f2937" }}>{card.name}</span>
        <Tag
          color={card.status === "ready" ? "green" : "default"}
          style={{ fontSize: 10, padding: "0 6px", lineHeight: "18px", margin: 0 }}
        >
          {card.status === "ready" ? "待命中" : "等待上游数据"}
        </Tag>
      </div>
      <div style={{ fontSize: 12, color: "#8c8c8c", marginTop: 2, lineHeight: 1.5 }}>
        {card.description}
      </div>
    </div>
  </div>
);

/** 最近分析列表项 */
const RecentAnalysisItem: React.FC<{
  item: typeof MOCK_RECENT_ANALYSES[0];
  onClick: () => void;
}> = ({ item, onClick }) => {
  const statusColor = item.status === "completed" ? "success" : "processing";
  return (
    <div
      onClick={onClick}
      style={{
        display: "flex",
        alignItems: "center",
        gap: 12,
        padding: "10px 12px",
        borderRadius: 8,
        cursor: "pointer",
        transition: "background 0.15s ease",
      }}
      onMouseEnter={(e) => { (e.currentTarget as HTMLDivElement).style.background = "#f9f9f9"; }}
      onMouseLeave={(e) => { (e.currentTarget as HTMLDivElement).style.background = "transparent"; }}
    >
      <Badge status={statusColor as "success" | "processing"} />
      <div style={{ flex: 1 }}>
        <span style={{ fontSize: 13, fontWeight: 500, color: "#1f2937" }}>{item.stockName}</span>
        <span style={{ fontSize: 12, color: "#8c8c8c", marginLeft: 4 }}>({item.stockCode})</span>
      </div>
      <Tag color={item.mode === "full" ? "purple" : "blue"} style={{ fontSize: 10, margin: 0 }}>
        {item.mode === "full" ? "深度" : "快速"}
      </Tag>
      <span style={{ fontSize: 11, color: "#bfbfbf" }}>{item.date}</span>
    </div>
  );
};

/** 市场环境快照 */
const MarketSnapshot: React.FC = () => (
  <div style={{ display: "flex", gap: 8 }}>
    {MOCK_MARKET_INDICES.map((idx) => (
      <div
        key={idx.name}
        style={{
          flex: 1,
          padding: "10px 12px",
          borderRadius: 8,
          background: "#fafbfc",
          border: "1px solid #f0f0f0",
          textAlign: "center",
        }}
      >
        <div style={{ fontSize: 11, color: "#8c8c8c", marginBottom: 4 }}>{idx.name}</div>
        <div style={{ fontSize: 15, fontWeight: 600, color: "#1f2937", fontFeatureSettings: "'ss01' on" }}>
          {idx.value}
        </div>
        <div style={{ fontSize: 12, color: idx.up ? "#15be53" : "#ef4444", marginTop: 2 }}>
          {idx.up ? <ArrowUpOutlined /> : <ArrowDownOutlined />} {idx.change}
        </div>
      </div>
    ))}
  </div>
);

/** 数据就绪状态行 */
const DataStatusRow: React.FC = () => {
  const items = [
    { ...MOCK_DATA_STATUS.dailyRange, icon: <LineChartOutlined /> },
    { ...MOCK_DATA_STATUS.financialQuarter, icon: <FundOutlined /> },
    { ...MOCK_DATA_STATUS.newsCount, icon: <ReadOutlined /> },
  ];
  const allOk = items.every((i) => i.status === "ok");

  return (
    <div>
      <div style={{ display: "flex", flexDirection: "column", gap: 8, marginBottom: 10 }}>
        {items.map((item) => (
          <div key={item.label} style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ color: "#8c8c8c", fontSize: 12, width: 56 }}>{item.label}</span>
            <span style={{ fontSize: 13, color: "#1f2937", fontWeight: 500, flex: 1 }}>{item.value}</span>
            <CheckCircleOutlined style={{ fontSize: 12, color: "#52c41a" }} />
          </div>
        ))}
      </div>
      {!allOk && (
        <div style={{ display: "flex", alignItems: "center", gap: 6, padding: "8px 12px", background: "#fffbe6", borderRadius: 6, border: "1px solid #ffe58f" }}>
          <Text style={{ fontSize: 11, color: "#ad8b00" }}>数据不完整，分析结果可能受限</Text>
        </div>
      )}
    </div>
  );
};

// ============================================================
// Running 态专用子组件
// ============================================================

/** 阶段导航项 */
const PhaseNavItem: React.FC<{
  phase: string;
  status: "completed" | "running" | "upcoming";
  onClick: () => void;
  isActive: boolean;
  timing?: { started: string; duration: string };
  agentCount: number;
}> = ({ phase, status, onClick, isActive, timing, agentCount }) => {
  const colors = {
    completed: { bg: "#f6ffed", border: "#b7eb8f", icon: "#52c41a", text: "#52c41a" },
    running: { bg: "#f0f0ff", border: "#d6d0ff", icon: "#533afd", text: "#533afd" },
    upcoming: { bg: "#fafafa", border: "#f0f0f0", icon: "#d9d9d9", text: "#bfbfbf" },
  };
  const c = colors[status];

  return (
    <div
      onClick={onClick}
      style={{
        padding: "12px 14px",
        borderRadius: 10,
        border: `1.5px solid ${isActive ? c.border : "transparent"}`,
        background: isActive ? c.bg : "transparent",
        cursor: status === "upcoming" ? "default" : "pointer",
        transition: "all 0.2s ease",
        marginBottom: 6,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
        {/* 状态圆点 */}
        <div
          style={{
            width: 10,
            height: 10,
            borderRadius: "50%",
            background: c.icon,
            flexShrink: 0,
            ...(status === "running" ? { animation: "agentPulse 1.5s ease-in-out infinite" } : {}),
          }}
        />
        <span style={{ fontSize: 13, fontWeight: isActive ? 600 : 500, color: status === "upcoming" ? "#bfbfbf" : "#1f2937" }}>
          {ANALYSIS_PHASE_LABELS[phase] || phase}
        </span>
        {status === "completed" && <CheckCircleOutlined style={{ fontSize: 11, color: "#52c41a", marginLeft: "auto" }} />}
        {status === "running" && <span style={{ marginLeft: "auto", fontSize: 10, color: "#533afd" }}>进行中</span>}
      </div>
      {/* Agent 数量 & 耗时 */}
      <div style={{ display: "flex", justifyContent: "space-between", paddingLeft: 18 }}>
        <span style={{ fontSize: 11, color: "#8c8c8c" }}>{agentCount} 位 Agent</span>
        {timing && (
          <span style={{ fontSize: 11, color: "#bfbfbf" }}>
            <ClockCircleOutlined style={{ marginRight: 2, fontSize: 10 }} />
            {timing.duration}
          </span>
        )}
      </div>
    </div>
  );
};

/** 实时日志面板 */
const LiveLogPanel: React.FC<{ logs: typeof MOCK_LIVE_LOGS }> = ({ logs }) => (
  <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
    <div style={{ padding: "10px 14px", borderBottom: "1px solid #f0f0f0" }}>
      <span style={{ fontSize: 12, fontWeight: 500, color: "#273951" }}>
        <SyncOutlined spin style={{ marginRight: 4, color: "#533afd" }} />
        实时日志
      </span>
    </div>
    <div style={{ flex: 1, overflowY: "auto", padding: "8px 10px" }}>
      {logs.map((log, i) => {
        const typeColors = { info: "#8c8c8c", success: "#52c41a", warning: "#faad14" };
        const dotColors = { info: "#8c8c8c", success: "#52c41a", warning: "#faad14" };
        return (
          <div key={i} style={{ display: "flex", gap: 8, marginBottom: 6, alignItems: "flex-start" }}>
            <div style={{ width: 6, height: 6, borderRadius: "50%", background: dotColors[log.type], marginTop: 5, flexShrink: 0 }} />
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: 11, color: "#bfbfbb", marginBottom: 1 }}>{log.time}</div>
              <div style={{ fontSize: 12, color: typeColors[log.type], lineHeight: 1.5, wordBreak: "break-word" }}>{log.msg}</div>
            </div>
          </div>
        );
      })}
    </div>
  </div>
);

// ============================================================
// 调试页面组件
// ============================================================

const StockAnalysisDebugPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const store = useStockAnalysisStore();
  const [collapsedPhases, setCollapsedPhases] = useState<string[]>([]);
  const [showDebugBar] = useState(true);
  const [activePhase, setActivePhase] = useState<string>("analysts");
  const [doneActiveTab, setDoneActiveTab] = useState("overview");

  // 根据 URL 参数初始化 mock 数据
  useEffect(() => {
    const mode = searchParams.get("mode") || "full";
    const debugMode = searchParams.get("debug") || "done";

    // 预设股票信息
    store.setStock("600519", "贵州茅台");

    if (mode === "quick") {
      store.setMode(AnalysisMode.QUICK);
    } else {
      store.setMode(AnalysisMode.FULL);
    }

    if (debugMode === "idle") {
      store.reset();
      store.setStock("600519", "贵州茅台");
      store.setMode(mode === "quick" ? AnalysisMode.QUICK : AnalysisMode.FULL);
    } else if (debugMode === "running") {
      store.startAnalysis();
      const statuses = mode === "quick" ? MOCK_AGENT_STATUSES_QUICK : MOCK_AGENT_STATUSES_FULL;
      for (const [agent, status] of Object.entries(statuses)) {
        store.updateAgentStatus({ agent, phase: "analysts", status: status as "running" | "done" | "failed" });
      }
      const reports = mode === "quick" ? MOCK_AGENT_REPORTS_QUICK : MOCK_AGENT_REPORTS_FULL;
      for (const [agent, summary] of Object.entries(reports)) {
        store.addAgentReport(agent, summary);
      }
      MOCK_THINKING_STEPS.forEach((step) => store.addThinkingStep(step));
      if (mode === "full") {
        MOCK_DEBATES.forEach((debate) => store.addDebate(debate));
        store.setDecision(MOCK_DECISION);
        store.setCurrentPhase("risk");
      } else {
        store.setCurrentPhase("analysts");
      }
    } else if (debugMode === "done") {
      store.startAnalysis();
      const reports = mode === "quick" ? MOCK_AGENT_REPORTS_QUICK : MOCK_AGENT_REPORTS_FULL;
      const statuses = mode === "quick" ? MOCK_AGENT_STATUSES_QUICK : MOCK_AGENT_STATUSES_FULL;
      for (const [agent, summary] of Object.entries(reports)) {
        store.addAgentReport(agent, summary);
      }
      for (const [agent, status] of Object.entries(statuses)) {
        store.updateAgentStatus({ agent, phase: "analysts", status: status as "running" | "done" | "failed" });
      }
      if (mode === "full") {
        MOCK_DEBATES.forEach((debate) => store.addDebate(debate));
        store.setDecision(MOCK_DECISION);
      }
      store.setTitle(`贵州茅台（600519）${mode === "quick" ? "快速" : "深度"}分析报告`);
      store.setSummary(
        mode === "quick"
          ? "快速分析显示，贵州茅台技术面处于 60 日均线支撑上方，基本面向好但估值合理。综合评分 6.8/10，建议逢跌分批建仓。"
          : "综合分析显示，贵州茅台基本面稳健、舆情偏正面、多空辩论后提价预期仍存不确定性。技术面中期偏多，综合评分 6.5/10，建议分批建仓，目标价 1980 元。"
      );
      store.setIndustries(["白酒", "食品饮料", "消费"]);
      store.setDataSource("AKShare + Tushare + Wind");
      store.setAnalysisState("done");
    } else if (debugMode === "running-live") {
      store.startAnalysis();
      store.updateAgentStatus({ agent: "market_analyst", phase: "analysts", status: "running" });
      setTimeout(() => {
        store.updateAgentStatus({ agent: "market_analyst", phase: "analysts", status: "done" });
        store.addAgentReport("market_analyst", MOCK_AGENT_REPORTS_FULL.market_analyst);
      }, 1500);
      setTimeout(() => {
        store.updateAgentStatus({ agent: "fundamentals_analyst", phase: "analysts", status: "running" });
      }, 2500);
      setTimeout(() => {
        store.updateAgentStatus({ agent: "fundamentals_analyst", phase: "analysts", status: "done" });
        store.addAgentReport("fundamentals_analyst", MOCK_AGENT_REPORTS_FULL.fundamentals_analyst);
      }, 4000);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  const isIdle = store.analysisState === "idle";
  const isRunning = store.analysisState === "running";
  const isDone = store.analysisState === "done";
  const isError = store.analysisState === "error";
  const isQuickMode = store.analysisMode === AnalysisMode.QUICK;
  const isViewMode = store.viewMode;

  const handleStart = useCallback(() => {
    if (!store.stockCode || !store.stockName) return;
    store.startAnalysis();
  }, [store]);

  const handleReset = useCallback(() => {
    Modal.confirm({
      title: "确认重新分析？",
      content: "当前结果将保留在历史记录中。",
      okText: "确认",
      cancelText: "取消",
      onOk: () => {
        store.reset();
        store.setStock("600519", "贵州茅台");
      },
    });
  }, [store]);

  const currentPhaseIndex = PHASE_ORDER.indexOf(store.currentPhase);

  const renderPhaseContent = (phase: string) => {
    switch (phase) {
      case "analysts":
        if (Object.keys(store.agentReports).length === 0) {
          return (
            <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "16px 0" }}>
              <Spin size="small" />
              <Text style={{ fontSize: 13, color: "#8c8c8c" }}>等待分析师输出...</Text>
            </div>
          );
        }
        return (
          <div>
            {Object.entries(store.agentReports).map(([agent, summary]) => {
              if (isQuickMode && agent !== "market_analyst" && agent !== "fundamentals_analyst") return null;
              const profile = AGENT_PROFILES[agent];
              return (
                <AgentReportCard
                  key={agent}
                  agent={agent}
                  summary={summary}
                  isRunning={store.agentStatuses[agent] === "running"}
                  thinkingMessage={profile?.thinkingMessage}
                />
              );
            })}
          </div>
        );
      case "debate":
        if (store.debates.length === 0) {
          return (
            <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "16px 0" }}>
              <Spin size="small" />
              <Text style={{ fontSize: 13, color: "#8c8c8c" }}>等待辩论数据...</Text>
            </div>
          );
        }
        return <DebateTimeline debates={store.debates} />;
      case "trader":
        if (!store.decision) {
          return (
            <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "16px 0" }}>
              <Spin size="small" />
              <Text style={{ fontSize: 13, color: "#8c8c8c" }}>等待决策输出...</Text>
            </div>
          );
        }
        return <DecisionCard decision={store.decision} />;
      case "risk":
        return (
          <RiskAssessmentSection
            debates={store.debates}
          />
        );
      default:
        return null;
    }
  };

  // 调试工具栏
  const renderDebugBar = () => (
    <div
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        zIndex: 1000,
        background: "#1a1a2e",
        padding: "8px 16px",
        display: "flex",
        alignItems: "center",
        gap: 8,
        flexWrap: "wrap",
      }}
    >
      <Tag color="magenta" style={{ margin: 0 }}>DEBUG</Tag>
      <Text style={{ color: "#aaa", fontSize: 12 }}>当前状态:</Text>
      <Tag color={isIdle ? "default" : isRunning ? "processing" : isDone ? "success" : "error"}>
        {store.analysisState}
      </Tag>
      <Tag color={isQuickMode ? "orange" : "blue"}>
        {isQuickMode ? "快速" : "深度"}
      </Tag>
      <Divider type="vertical" style={{ borderColor: "#444" }} />
      <Text style={{ color: "#aaa", fontSize: 12 }}>切换场景:</Text>
      <Button size="small" onClick={() => navigate("/stock-analysis-debug?debug=idle")}>Idle</Button>
      <Button size="small" onClick={() => navigate("/stock-analysis-debug?debug=running&mode=full")}>Running (深度)</Button>
      <Button size="small" onClick={() => navigate("/stock-analysis-debug?debug=done&mode=full")}>Done (深度)</Button>
      <Button size="small" onClick={() => navigate("/stock-analysis-debug?debug=done&mode=quick")}>Done (快速)</Button>
      <Button size="small" onClick={() => navigate("/stock-analysis-debug?debug=running-live&mode=full")}>Running (动画)</Button>
      <Divider type="vertical" style={{ borderColor: "#444" }} />
      <Button size="small" danger onClick={() => store.reset()}>Reset</Button>
    </div>
  );

  const topOffset = showDebugBar ? 44 : 0;

  // === Idle 态（增强版） ===
  if (isIdle) {
    return (
      <>
        {showDebugBar && renderDebugBar()}
        <div style={{ flex: 1, display: "flex", flexDirection: "column", padding: `${24 + topOffset}px 32px 24px`, minHeight: "100vh" }}>
          <SystemStatusBar />
          <div style={{ display: "flex", gap: 24, flex: 1, minHeight: 0, alignItems: "stretch" }}>
            {/* ===== 左侧：分析配置卡片 ===== */}
            <div style={{
              flex: "0 0 44%",
              display: "flex",
              flexDirection: "column",
              background: "#fff",
              borderRadius: 12,
              border: "1px solid #f0f0f0",
              padding: "28px 28px 20px",
              boxShadow: "0 1px 3px rgba(0,0,0,0.04)",
            }}>
              <div style={{ marginBottom: 24, minHeight: 48 }}>
                <h1 style={{ fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif", fontWeight: 500, fontSize: 20, color: "#061b31", margin: 0, marginBottom: 4, letterSpacing: "-0.3px" }}>
                  分析配置
                </h1>
                <span style={{ fontSize: 13, color: "#8c8c8c" }}>选择标的和分析模式</span>
              </div>
              <div style={{ marginBottom: 24 }}>
                <label style={{ fontSize: 13, fontWeight: 500, color: "#273951", display: "block", marginBottom: 8 }}>分析标的</label>
                <StockSearchInput />
              </div>
              <div style={{ marginBottom: 24 }}>
                <label style={{ fontSize: 13, fontWeight: 500, color: "#273951", display: "block", marginBottom: 8 }}>分析模式</label>
                <ModeSelectionCards value={store.analysisMode} onChange={store.setMode} />
              </div>
              <div style={{ marginBottom: 24 }}>
                <label style={{ fontSize: 13, fontWeight: 500, color: "#273951", display: "block", marginBottom: 10 }}>
                  分析维度
                  <span style={{ fontWeight: 400, color: "#bfbfbf", marginLeft: 6, fontSize: 11 }}>
                    {isQuickMode ? "快速模式 · 2项" : "深度模式 · 4项"}
                  </span>
                </label>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                  {(isQuickMode ? QUICK_DIMS : FULL_DIMS).map((dim) => (
                    <DimDisplayChip key={dim.label} dim={dim} />
                  ))}
                </div>
              </div>
              <div style={{ marginBottom: 24 }}>
                <label style={{ fontSize: 13, fontWeight: 500, color: "#273951", display: "block", marginBottom: 10 }}>数据就绪状态</label>
                <DataStatusRow />
              </div>
              <div style={{ flex: 1 }} />
              <div>
                <Button
                  type="primary"
                  size="large"
                  block
                  disabled={!store.stockCode || !store.stockName}
                  onClick={handleStart}
                  icon={<PlayCircleOutlined />}
                  style={{ borderRadius: 8, fontWeight: 500, height: 48, fontSize: 15 }}
                >
                  开始分析
                </Button>
                <div style={{ textAlign: "center", marginTop: 10 }}>
                  <Text style={{ fontSize: 11, color: "#c0c6cf" }}>本工具仅供投研参考，不构成任何投资建议</Text>
                </div>
              </div>
            </div>

            {/* ===== 右侧：智能分析师协作面板 ===== */}
            <div style={{
              flex: "1 1 56%",
              display: "flex",
              flexDirection: "column",
              background: "#fff",
              borderRadius: 12,
              border: "1px solid #f0f0f0",
              padding: "28px 28px 20px",
              boxShadow: "0 1px 3px rgba(0,0,0,0.04)",
            }}>
              {/* 价值主张 — Hero 区域 */}
              <div style={{ marginBottom: 24, minHeight: 48 }}>
                <h1 style={{ fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif", fontWeight: 500, fontSize: 20, color: "#061b31", margin: 0, marginBottom: 4, letterSpacing: "-0.3px" }}>
                  AI 协作分析
                </h1>
                <span style={{ fontSize: 13, color: "#8c8c8c", lineHeight: 1.6, display: "block" }}>
                  多 Agent 协作，从技术面到风险评估，生成结构化投资分析报告
                </span>
              </div>

              {/* 分析师待命卡片 */}
              <div style={{ display: "flex", flexDirection: "column", gap: 10, marginBottom: 20 }}>
                {(isQuickMode ? QUICK_ANALYSTS : FULL_ANALYSTS).map((card) => (
                  <AnalystReadyCardItem key={card.name} card={card} />
                ))}
              </div>

              {/* 弹性填充 */}
              <div style={{ flex: 1 }} />

              {/* 底部：模式动态提示 + 快捷引导 */}
              <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                {/* 模式提示 */}
                <div style={{
                  padding: "14px 18px",
                  borderRadius: 10,
                  background: isQuickMode ? "#f0fdf4" : "#f8f7ff",
                  border: `1px solid ${isQuickMode ? "#bbf7d0" : "#e8e0ff"}`,
                  display: "flex",
                  alignItems: "center",
                  gap: 12,
                }}>
                  {isQuickMode ? (
                    <ThunderboltOutlined style={{ fontSize: 20, color: "#22c55e", flexShrink: 0 }} />
                  ) : (
                    <ExperimentOutlined style={{ fontSize: 20, color: "#533afd", flexShrink: 0 }} />
                  )}
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 600, color: isQuickMode ? "#166534" : "#3b1fde", marginBottom: 2 }}>
                      {isQuickMode ? "快速分析" : "深度分析"}
                    </div>
                    <div style={{ fontSize: 12, color: "#8c8c8c", lineHeight: 1.6 }}>
                      {isQuickMode
                        ? "2 位分析师协作 · 约 30-60 秒出结果"
                        : "4 位分析师 + 多空辩论 + 风险评估 · 约 3-5 分钟出完整报告"}
                    </div>
                  </div>
                </div>

                {/* 最近分析快捷入口 */}
                <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 2 }}>
                    <span style={{ fontSize: 11, fontWeight: 500, color: "#8c8c8c" }}>最近分析</span>
                    <Button size="small" type="link" style={{ fontSize: 11, padding: 0, height: "auto", color: "#8c8c8c" }}>
                      查看记录 →
                    </Button>
                  </div>
                  <div style={{ display: "flex", gap: 8 }}>
                    {MOCK_RECENT_ANALYSES.slice(0, 3).map((item) => (
                      <div
                        key={item.id}
                        onClick={() => {
                          if (item.status === "completed") {
                            navigate(`/stock-analysis?recordId=${item.id}`);
                          } else {
                            navigate(`/stock-analysis-debug?debug=running-live`);
                          }
                        }}
                        style={{
                          flex: 1,
                          padding: "8px 10px",
                          borderRadius: 8,
                          border: "1px solid #f0f0f0",
                          background: "#fafbfc",
                          cursor: "pointer",
                          transition: "all 0.15s ease",
                        }}
                        onMouseEnter={(e) => { (e.currentTarget as HTMLDivElement).style.background = "#f5f3ff"; (e.currentTarget as HTMLDivElement).style.borderColor = "#e0d8ff"; }}
                        onMouseLeave={(e) => { (e.currentTarget as HTMLDivElement).style.background = "#fafbfc"; (e.currentTarget as HTMLDivElement).style.borderColor = "#f0f0f0"; }}
                      >
                        <div style={{ display: "flex", alignItems: "center", gap: 4, marginBottom: 4 }}>
                          <Badge status={item.status === "completed" ? "success" : "processing"} />
                          <span style={{ fontSize: 12, fontWeight: 500, color: "#1f2937" }}>{item.stockName}</span>
                        </div>
                        <div style={{ fontSize: 10, color: "#bfbfbf" }}>{item.date}</div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </>
    );
  }

  // === Running / Done / Error 态 ===
  const phasesToShow = isQuickMode ? ["analysts"] : PHASE_ORDER;

  /** 获取阶段状态 */
  const getPhaseStatus = (phase: string): "completed" | "running" | "upcoming" => {
    if (isDone) return "completed";
    const idx = PHASE_ORDER.indexOf(phase);
    const curIdx = PHASE_ORDER.indexOf(store.currentPhase);
    if (idx < curIdx) return "completed";
    if (idx === curIdx) return "running";
    return "upcoming";
  };

  /** 获取阶段 Agent 数量 */
  const getPhaseAgentCount = (phase: string) => {
    switch (phase) {
      case "analysts": return isQuickMode ? 2 : 4;
      case "debate": return 3;
      case "trader": return 1;
      case "risk": return 4;
      default: return 0;
    }
  };

  return (
    <>
      {showDebugBar && renderDebugBar()}
      <div style={{ height: "100vh", display: "flex", flexDirection: "column", paddingTop: topOffset }}>
        {/* ===== 顶部标题栏 ===== */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "16px 24px", borderBottom: "1px solid #e5edf5", flexShrink: 0 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            {isQuickMode && (
              <Badge count="快速" style={{ background: "#533afd", fontSize: 10 }} offset={[0, 0]}>
                <StockOutlined style={{ fontSize: 20, color: "#533afd" }} />
              </Badge>
            )}
            {!isQuickMode && <StockOutlined style={{ fontSize: 20, color: "#533afd" }} />}
            <div>
              <Title level={4} style={{ margin: 0, fontWeight: 400, color: "#061b31" }}>
                {store.stockName}({store.stockCode}) {isQuickMode ? "快速" : "深度"}分析
              </Title>
              {store.title && (
                <Text style={{ fontSize: 13, color: "#64748d" }}>{store.title}</Text>
              )}
            </div>
            {store.dataSource && (
              <Tag color="blue" icon={<DatabaseOutlined />}>数据源: {store.dataSource}</Tag>
            )}
          </div>
          <Space>
            {isRunning && !isViewMode && (
              <Button onClick={() => store.setAnalysisState("done")} style={{ borderRadius: 4 }}>停止分析</Button>
            )}
            {(isDone || isError) && (
              <Button icon={<RedoOutlined />} onClick={handleReset} style={{ borderRadius: 4 }}>重新分析</Button>
            )}
          </Space>
        </div>

        {/* ===== 阶段进度条 ===== */}
        {(isRunning || isDone) && (
          <div style={{ padding: "12px 24px", borderBottom: "1px solid #e5edf5", flexShrink: 0, background: "#fafbfc" }}>
            <Steps
              current={isDone ? phasesToShow.length : Math.min(currentPhaseIndex, phasesToShow.length - 1)}
              status={isDone ? "finish" : "process"}
              size="small"
              items={phasesToShow.map((phase) => {
                const timing = MOCK_PHASE_TIMINGS[phase];
                return ({
                  title: (
                    <span style={{ fontSize: 12, fontFeatureSettings: "'ss01' on" }}>
                      <span style={{ color: isDone ? "#15be53" : store.currentPhase === phase ? "#533afd" : "#64748d", transition: "color 0.3s ease" }}>
                        {ANALYSIS_PHASE_LABELS[phase] || phase}
                      </span>
                      {timing && (
                        <span style={{ fontSize: 10, color: "#bfbfbf", marginLeft: 6 }}>
                          {timing.duration}
                        </span>
                      )}
                    </span>
                  ),
                  description: timing ? (
                    <span style={{ fontSize: 10, color: "#d9d9d9" }}>
                      {timing.started}{timing.completed ? ` ~ ${timing.completed}` : ''}
                    </span>
                  ) : undefined,
                });
              })}
            />
          </div>
        )}

        {/* ===== 主内容区 ===== */}
        <div style={{ flex: 1, overflow: "hidden", display: "flex", position: "relative" }}>
          {/* ===== Error 态 ===== */}
          {isError && (
            <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center" }}>
              <Alert type="error" message="分析失败" description={store.error} showIcon style={{ margin: "0 40px", borderRadius: 6 }} />
            </div>
          )}

          {/* ===== Running 态：三栏布局 ===== */}
          {isRunning && (
            <>
              {/* 左栏：阶段导航 */}
              <div style={{ width: 220, flexShrink: 0, borderRight: "1px solid #e5edf5", overflowY: "auto", padding: "16px 12px", background: "#fafbfc" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 16 }}>
                  <ThunderboltOutlined style={{ color: "#533afd", fontSize: 14 }} />
                  <span style={{ fontSize: 12, fontWeight: 600, color: "#273951" }}>分析阶段</span>
                  {store.thinkingSteps.length > 0 && (
                    <Badge count={store.thinkingSteps.length} style={{ background: "#e5edf5", color: "#64748d" }} />
                  )}
                </div>
                {phasesToShow.map((phase) => (
                  <PhaseNavItem
                    key={phase}
                    phase={phase}
                    status={getPhaseStatus(phase)}
                    isActive={activePhase === phase}
                    onClick={() => setActivePhase(phase)}
                    agentCount={getPhaseAgentCount(phase)}
                    timing={MOCK_PHASE_TIMINGS[phase]}
                  />
                ))}

                {/* AI 思维过程 */}
                {store.thinkingSteps.length > 0 && (
                  <>
                    <Divider style={{ margin: "12px 0" }} />
                    <div style={{ padding: "8px 12px" }}>
                      <div style={{ fontSize: 11, fontWeight: 500, color: "#8c8c8c", marginBottom: 8 }}>AI 思维链</div>
                      <ThinkingChain steps={store.thinkingSteps} completed={false} />
                    </div>
                  </>
                )}
              </div>

              {/* 中栏：当前阶段内容 */}
              <div style={{ flex: 1, overflowY: "auto", padding: "20px 24px", paddingBottom: 56 }}>
                {/* 加载初始态 */}
                {Object.keys(store.agentStatuses).length === 0 && store.thinkingSteps.length === 0 && (
                  <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: "60px 0" }}>
                    <Spin size="large" />
                    <Text style={{ fontSize: 13, color: "#64748d", marginTop: 16 }}>正在初始化分析流程...</Text>
                    <div style={{ width: 200, marginTop: 16 }}>
                      <Progress percent={30} showInfo={false} strokeColor="#533afd" />
                    </div>
                  </div>
                )}

                {/* 当前激活阶段内容 */}
                {activePhase && (
                  <div>
                    <SectionHeader title={ANALYSIS_PHASE_LABELS[activePhase] || activePhase} />
                    {renderPhaseContent(activePhase)}
                  </div>
                )}

                {/* 已完成阶段折叠列表 */}
                {phasesToShow.filter((p) => getPhaseStatus(p) === "completed").map((phase) => {
                  const phaseLabel = ANALYSIS_PHASE_LABELS[phase] || phase;
                  const isPhaseCollapsed = collapsedPhases.includes(phase);
                  return (
                    <div key={phase} style={{ marginBottom: 12 }}>
                      <div
                        onClick={() => {
                          setCollapsedPhases((prev) =>
                            isPhaseCollapsed ? prev.filter((p) => p !== phase) : [...prev, phase]
                          );
                        }}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: 10,
                          padding: "10px 14px",
                          background: "#fafbfc",
                          borderRadius: 8,
                          border: "1px solid #f0f0f0",
                          cursor: "pointer",
                          transition: "all 0.2s ease",
                        }}
                      >
                        <CheckCircleOutlined style={{ fontSize: 14, color: "#52c41a" }} />
                        <Text style={{ fontSize: 13, color: "#52c41a", fontWeight: 500 }}>{phaseLabel}已完成</Text>
                        <Text style={{ fontSize: 11, color: "#bfbfbf" }}>{isPhaseCollapsed ? "点击展开" : "点击收起"}</Text>
                        {MOCK_PHASE_TIMINGS[phase] && (
                          <span style={{ fontSize: 11, color: "#8c8c8c", marginLeft: "auto" }}>
                            耗时 {MOCK_PHASE_TIMINGS[phase].duration}
                          </span>
                        )}
                        <span style={{
                          fontSize: 10,
                          color: "#bfbfbf",
                          marginLeft: 4,
                          transform: isPhaseCollapsed ? "rotate(-90deg)" : "rotate(0)",
                          transition: "transform 0.2s ease",
                        }}>▾</span>
                      </div>
                      {!isPhaseCollapsed && (
                        <div style={{ marginTop: 8, paddingLeft: 4 }}>
                          {renderPhaseContent(phase)}
                        </div>
                      )}
                    </div>
                  );
                })}

                {store.content && !store.decision && (
                  <Card style={{ marginBottom: 16, borderRadius: 6, border: "1px solid #e5edf5" }} styles={{ body: { padding: "16px 20px" } }}>
                    <div style={{ fontSize: 14, color: "#061b31", lineHeight: 1.8, whiteSpace: "pre-wrap" }}>
                      {store.content}
                      <span style={{ display: "inline-block", width: 2, height: 16, background: "#533afd", marginLeft: 1, animation: "blink 1s infinite", verticalAlign: "middle" }} />
                    </div>
                  </Card>
                )}
              </div>

              {/* 右栏：实时日志 */}
              <div style={{ width: 260, flexShrink: 0, borderLeft: "1px solid #e5edf5", overflow: "hidden", display: "flex", flexDirection: "column", background: "#fafbfc" }}>
                <LiveLogPanel logs={MOCK_LIVE_LOGS} />
              </div>
            </>
          )}

          {/* ===== Done 态：总-分结构 ===== */}
          {isDone && (
            <>
              {/* 左栏：阶段回顾导航 */}
              <div style={{ width: 220, flexShrink: 0, borderRight: "1px solid #e5edf5", overflowY: "auto", padding: "16px 12px", background: "#fafbfc" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 16 }}>
                  <CheckCircleOutlined style={{ color: "#52c41a", fontSize: 14 }} />
                  <span style={{ fontSize: 12, fontWeight: 600, color: "#273951" }}>分析完成</span>
                </div>

                {/* 阶段回顾 */}
                <div style={{ marginBottom: 12 }}>
                  <div style={{ fontSize: 11, fontWeight: 500, color: "#8c8c8c", marginBottom: 8, textTransform: "uppercase", letterSpacing: "0.5px" }}>分析阶段</div>
                  {phasesToShow.map((phase) => {
                    const timing = MOCK_PHASE_TIMINGS[phase];
                    return (
                      <PhaseNavItem
                        key={phase}
                        phase={phase}
                        status="completed"
                        isActive={activePhase === phase}
                        onClick={() => setActivePhase(phase)}
                        agentCount={getPhaseAgentCount(phase)}
                        timing={timing}
                      />
                    );
                  })}
                </div>

                <Divider style={{ margin: "12px 0" }} />

                {/* 分析耗时 */}
                <div style={{ padding: "8px 12px" }}>
                  <div style={{ fontSize: 11, fontWeight: 500, color: "#8c8c8c", marginBottom: 8 }}>总耗时</div>
                  <div style={{ fontSize: 18, fontWeight: 700, color: "#533afd", fontFeatureSettings: "'ss01' on" }}>2分3秒</div>
                  <div style={{ fontSize: 11, color: "#bfbfbf", marginTop: 2 }}>15:32:08 ~ 15:34:11</div>
                </div>
              </div>

              {/* 中栏：内容区（Tab 组织） */}
              <div style={{ flex: 1, overflowY: "auto", padding: "20px 24px", paddingBottom: 56 }}>
                {/* 浓缩结论卡片（置顶） */}
                {store.decision && (
                  <div style={{ marginBottom: 20 }}>
                    <Card
                      style={{
                        borderRadius: 12,
                        border: "1px solid #e8e0ff",
                        background: "linear-gradient(135deg, #faf8ff 0%, #f5f0ff 100%)",
                      }}
                    >
                      <div style={{ display: "flex", gap: 24, alignItems: "flex-start" }}>
                        {/* 左侧：操作建议 */}
                        <div style={{ flex: 1 }}>
                          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
                            <DollarOutlined style={{ color: "#533afd", fontSize: 14 }} />
                            <span style={{ fontSize: 12, fontWeight: 600, color: "#533afd" }}>操作建议</span>
                          </div>
                          <div style={{ fontSize: 18, fontWeight: 600, color: "#061b31", marginBottom: 6 }}>
                            {store.decision.action}
                          </div>
                          <div style={{ display: "flex", gap: 16 }}>
                            <div>
                              <div style={{ fontSize: 11, color: "#8c8c8c", marginBottom: 2 }}>目标价</div>
                              <div style={{ fontSize: 16, fontWeight: 600, color: "#15be53" }}>{store.decision.target_price} 元</div>
                            </div>
                            <div>
                              <div style={{ fontSize: 11, color: "#8c8c8c", marginBottom: 2 }}>当前价</div>
                              <div style={{ fontSize: 16, fontWeight: 500, color: "#061b31" }}>1,685 元</div>
                            </div>
                            <div>
                              <div style={{ fontSize: 11, color: "#8c8c8c", marginBottom: 2 }}>预期收益</div>
                              <div style={{ fontSize: 16, fontWeight: 600, color: "#15be53" }}>+17.5%</div>
                            </div>
                          </div>
                        </div>

                        {/* 右侧：评分仪表盘 */}
                        <div style={{ display: "flex", gap: 20 }}>
                          <div style={{ textAlign: "center" }}>
                            <div style={{ position: "relative", width: 64, height: 64 }}>
                              <svg viewBox="0 0 36 36" style={{ transform: "rotate(-90deg)", width: 64, height: 64 }}>
                                <path
                                  d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                                  fill="none"
                                  stroke="#e8e8e8"
                                  strokeWidth="3"
                                />
                                <path
                                  d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                                  fill="none"
                                  stroke="#533afd"
                                  strokeWidth="3"
                                  strokeDasharray={`${store.decision.confidence}, 100`}
                                  strokeLinecap="round"
                                />
                              </svg>
                              <div style={{ position: "absolute", top: "50%", left: "50%", transform: "translate(-50%, -50%)", fontSize: 16, fontWeight: 700, color: "#533afd" }}>
                                {store.decision.confidence}
                              </div>
                            </div>
                            <div style={{ fontSize: 10, color: "#8c8c8c", marginTop: 2 }}>置信度</div>
                          </div>
                          <div style={{ textAlign: "center" }}>
                            <div style={{ position: "relative", width: 64, height: 64 }}>
                              <svg viewBox="0 0 36 36" style={{ transform: "rotate(-90deg)", width: 64, height: 64 }}>
                                <path
                                  d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                                  fill="none"
                                  stroke="#e8e8e8"
                                  strokeWidth="3"
                                />
                                <path
                                  d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                                  fill="none"
                                  stroke="#ef4444"
                                  strokeWidth="3"
                                  strokeDasharray={`${store.decision.risk_score}, 100`}
                                  strokeLinecap="round"
                                />
                              </svg>
                              <div style={{ position: "absolute", top: "50%", left: "50%", transform: "translate(-50%, -50%)", fontSize: 16, fontWeight: 700, color: "#ef4444" }}>
                                {store.decision.risk_score}
                              </div>
                            </div>
                            <div style={{ fontSize: 10, color: "#8c8c8c", marginTop: 2 }}>风险分</div>
                          </div>
                        </div>
                      </div>
                    </Card>
                  </div>
                )}

                {/* 摘要卡片（如有） */}
                {(store.title || store.summary || store.industries.length > 0) && (
                  <div style={{ marginBottom: 20 }}>
                    <SummaryCard
                      title={store.title}
                      summary={store.summary}
                      industries={store.industries}
                      stockName={store.stockName}
                      stockCode={store.stockCode}
                      analysisMode={store.analysisMode}
                      dataSource={store.dataSource}
                    />
                  </div>
                )}

                {/* Tab 详细区 */}
                <Tabs
                  activeKey={doneActiveTab}
                  onChange={setDoneActiveTab}
                  size="middle"
                  items={[
                    {
                      key: "overview",
                      label: <span><TeamOutlined style={{ marginRight: 4 }} />分析师报告</span>,
                      children: Object.keys(store.agentReports).length > 0 ? (
                        <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 12 }}>
                          {Object.entries(store.agentReports).map(([agent, summary]) => {
                            if (isQuickMode && agent !== "market_analyst" && agent !== "fundamentals_analyst") return null;
                            return <AgentReportCard key={agent} agent={agent} summary={summary} gridMode />;
                          })}
                        </div>
                      ) : (
                        <div style={{ textAlign: "center", padding: 40 }}>
                          <TeamOutlined style={{ fontSize: 32, color: "#d9d9d9", marginBottom: 8 }} />
                          <div style={{ fontSize: 13, color: "#8c8c8c" }}>暂无分析师报告</div>
                        </div>
                      ),
                    },
                    ...(isQuickMode ? [] : [
                      {
                        key: "debate",
                        label: <span><SwapOutlined style={{ marginRight: 4 }} />投资辩论</span>,
                        children: store.debates.length > 0 ? (
                          <DebateTimeline debates={store.debates} />
                        ) : (
                          <div style={{ textAlign: "center", padding: 40 }}>
                            <SwapOutlined style={{ fontSize: 32, color: "#d9d9d9", marginBottom: 8 }} />
                            <div style={{ fontSize: 13, color: "#8c8c8c" }}>暂无辩论记录</div>
                          </div>
                        ),
                      },
                      {
                        key: "risk",
                        label: <span><SafetyCertificateOutlined style={{ marginRight: 4 }} />风险评估</span>,
                        children: (
                          <RiskAssessmentSection debates={store.debates} />
                        ),
                      },
                    ]),
                    {
                      key: "detail",
                      label: <span><FileTextOutlined style={{ marginRight: 4 }} />完整报告</span>,
                      children: (
                        <div style={{ padding: "16px 0" }}>
                          {Object.entries(store.agentReports).map(([agent, summary]) => {
                            if (isQuickMode && agent !== "market_analyst" && agent !== "fundamentals_analyst") return null;
                            return <AgentReportCard key={agent} agent={agent} summary={summary} />;
                          })}
                        </div>
                      ),
                    },
                  ]}
                />

                {/* 历史分析 */}
                {store.stockCode && (
                  <div style={{ marginTop: 24 }}>
                    <Divider style={{ margin: "8px 0 12px" }} />
                    <SectionHeader icon={<HistoryOutlined />} title="历史分析" />
                    <AnalysisHistoryList stockCode={store.stockCode} />
                  </div>
                )}
              </div>
            </>
          )}

          {/* 合规提示 */}
          <div
            style={{
              position: "absolute",
              bottom: 0,
              left: (isRunning || isDone) ? (isQuickMode ? 220 : 220) : 0,
              right: isRunning ? 260 : 0,
              textAlign: "center",
              padding: "8px 0",
              background: "linear-gradient(transparent, #ffffff 30%)",
              pointerEvents: "none",
              zIndex: 10,
            }}
          >
            <Text style={{ fontSize: 11, color: "#c0c6cf" }}>
              本工具仅供投研参考，不构成任何投资建议
            </Text>
          </div>
        </div>

        <style>{`
          @keyframes blink {
            0%, 100% { opacity: 1; }
            50% { opacity: 0; }
          }
          @keyframes agentPulse {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.4; transform: scale(0.7); }
          }
        `}</style>
      </div>
    </>
  );
};

export default StockAnalysisDebugPage;
