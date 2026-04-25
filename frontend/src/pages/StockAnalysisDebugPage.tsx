/**
 * StockAnalysisDebugPage -- 个股分析调试页面（写死数据，不调用后端）
 *
 * 用于快速调试 UI 效果，通过 URL 参数切换不同状态：
 *   /stock-analysis-debug?idle       -> 初始配置态
 *   /stock-analysis-debug?running    -> 分析进行中（深度模式，全部阶段有数据）
 *   /stock-analysis-debug?done       -> 分析完成态
 *   /stock-analysis-debug?quick-done -> 快速分析完成态
 */

import React, { useCallback, useEffect, useState } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { Button, Typography, Card, Steps, Spin, Alert, Space, Divider, Badge, Tag, Modal } from "antd";
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
} from "@ant-design/icons";
import StockSearchInput from "../components/stock-analysis/StockSearchInput";
import SystemStatusBar from "../components/stock-analysis/SystemStatusBar";
import AgentTopologyPreview from "../components/stock-analysis/AgentTopologyPreview";
import ModeSelectionCards from "../components/stock-analysis/ModeSelectionCards";
import HistoryQuickEntry from "../components/stock-analysis/HistoryQuickEntry";
import AgentProgressPanel from "../components/stock-analysis/AgentProgressPanel";
import AgentReportCard from "../components/stock-analysis/AgentReportCard";
import DebateTimeline from "../components/stock-analysis/DebateTimeline";
import DecisionCard from "../components/stock-analysis/DecisionCard";
import AnalysisHistoryList from "../components/stock-analysis/AnalysisHistoryList";
import AnalysisComparison from "../components/stock-analysis/AnalysisComparison";
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
    "- 增持：6 家\  - 中性：3 家\  - 卖出：0 家\n" +
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
// 调试页面组件
// ============================================================

const StockAnalysisDebugPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const store = useStockAnalysisStore();
  const [collapsedPhases, setCollapsedPhases] = useState<string[]>([]);
  const [showDebugBar] = useState(true);

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
      // 保持 idle 态
      store.reset();
      store.setStock("600519", "贵州茅台");
      store.setMode(mode === "quick" ? AnalysisMode.QUICK : AnalysisMode.FULL);
    } else if (debugMode === "running") {
      // 模拟 running 态 - 全部阶段有数据
      store.startAnalysis();
      // 模拟全部 agent 状态为 done
      const statuses = mode === "quick" ? MOCK_AGENT_STATUSES_QUICK : MOCK_AGENT_STATUSES_FULL;
      for (const [agent, status] of Object.entries(statuses)) {
        store.updateAgentStatus({ agent, phase: "analysts", status: status as "running" | "done" | "failed" });
      }
      // 模拟 agent 报告
      const reports = mode === "quick" ? MOCK_AGENT_REPORTS_QUICK : MOCK_AGENT_REPORTS_FULL;
      for (const [agent, summary] of Object.entries(reports)) {
        store.addAgentReport(agent, summary);
      }
      // 模拟思维过程
      MOCK_THINKING_STEPS.forEach((step) => store.addThinkingStep(step));
      // 如果是 full 模式，设置辩论和决策
      if (mode === "full") {
        MOCK_DEBATES.forEach((debate) => store.addDebate(debate));
        store.setDecision(MOCK_DECISION);
        store.setCurrentPhase("risk");
      } else {
        store.setCurrentPhase("analysts");
      }
    } else if (debugMode === "done") {
      // 模拟 done 态 - 全部数据就绪
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
      // 设置为 done 态
      store.setAnalysisState("done");
    } else if (debugMode === "running-live") {
      // 模拟正在运行中（逐步显示数据）
      store.startAnalysis();
      // 只显示部分数据，模拟进行中
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
            decision={store.decision ?? undefined}
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
      <Button size="small" onClick={() => navigate("/stock-analysis-debug?debug=idle")}>
        Idle
      </Button>
      <Button size="small" onClick={() => navigate("/stock-analysis-debug?debug=running&mode=full")}>
        Running (深度)
      </Button>
      <Button size="small" onClick={() => navigate("/stock-analysis-debug?debug=done&mode=full")}>
        Done (深度)
      </Button>
      <Button size="small" onClick={() => navigate("/stock-analysis-debug?debug=done&mode=quick")}>
        Done (快速)
      </Button>
      <Button size="small" onClick={() => navigate("/stock-analysis-debug?debug=running-live&mode=full")}>
        Running (动画)
      </Button>
      <Divider type="vertical" style={{ borderColor: "#444" }} />
      <Button size="small" danger onClick={() => store.reset()}>
        Reset
      </Button>
    </div>
  );

  const topOffset = showDebugBar ? 44 : 0;

  // === Idle 态 ===
  if (isIdle) {
    return (
      <>
        {showDebugBar && renderDebugBar()}
        <div style={{ flex: 1, display: "flex", flexDirection: "column", padding: `${24 + topOffset}px 32px 24px`, minHeight: "100vh" }}>
          <SystemStatusBar />
          <div style={{ display: "flex", gap: 24, flex: 1, minHeight: 0, alignItems: "stretch" }}>
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
              <div style={{ marginBottom: 24 }}>
                <h1 style={{ fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif", fontWeight: 500, fontSize: 20, color: "#061b31", margin: 0, marginBottom: 4, letterSpacing: "-0.3px" }}>
                  分析配置
                </h1>
                <span style={{ fontSize: 13, color: "#8c8c8c" }}>
                  选择标的和分析模式
                </span>
              </div>
              <div style={{ marginBottom: 24 }}>
                <label style={{ fontSize: 13, fontWeight: 500, color: "#273951", display: "block", marginBottom: 8 }}>
                  分析标的
                </label>
                <StockSearchInput />
              </div>
              <div style={{ marginBottom: 24 }}>
                <label style={{ fontSize: 13, fontWeight: 500, color: "#273951", display: "block", marginBottom: 8 }}>
                  分析模式
                </label>
                <ModeSelectionCards value={store.analysisMode} onChange={store.setMode} />
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
                  <Text style={{ fontSize: 11, color: "#c0c6cf" }}>
                    本工具仅供投研参考，不构成任何投资建议
                  </Text>
                </div>
              </div>
            </div>
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
              <div style={{ marginBottom: 24 }}>
                <h1 style={{ fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif", fontWeight: 500, fontSize: 20, color: "#061b31", margin: 0, marginBottom: 4, letterSpacing: "-0.3px" }}>
                  Agent 协作拓扑
                </h1>
                <span style={{ fontSize: 13, color: "#8c8c8c" }}>
                  {store.analysisMode === AnalysisMode.FULL ? "深度模式：4位分析师 + 辩论 + 风评" : "快速模式：2位分析师协作"}
                </span>
              </div>
              <div style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" }}>
                <AgentTopologyPreview analysisMode={store.analysisMode} />
              </div>
              {store.stockCode && (
                <div style={{ marginTop: 16 }}>
                  <HistoryQuickEntry stockCode={store.stockCode} onSelect={(id) => navigate(`/stock-analysis?recordId=${id}`)} />
                </div>
              )}
            </div>
          </div>
        </div>
      </>
    );
  }

  // === Running / Done / Error 态 ===
  const phasesToShow = isQuickMode ? ["analysts"] : PHASE_ORDER;
  const showSidebar = true;

  return (
    <>
      {showDebugBar && renderDebugBar()}
      <div style={{ height: "100vh", display: "flex", flexDirection: "column", paddingTop: topOffset }}>
        {/* 顶部标题栏 */}
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
              <Tag color="blue" icon={<DatabaseOutlined />}>
                数据源: {store.dataSource}
              </Tag>
            )}
          </div>
          <Space>
            {isRunning && !isViewMode && (
              <Button onClick={() => store.setAnalysisState("done")} style={{ borderRadius: 4 }}>
                停止分析
              </Button>
            )}
            {(isDone || isError) && (
              <Button icon={<RedoOutlined />} onClick={handleReset} style={{ borderRadius: 4 }}>
                重新分析
              </Button>
            )}
          </Space>
        </div>

        {/* 阶段进度条 */}
        {(isRunning || isDone) && (
          <div style={{ padding: "8px 24px", borderBottom: "1px solid #e5edf5", flexShrink: 0, background: "#fafbfc" }}>
            <Steps
              current={isDone ? phasesToShow.length : Math.min(currentPhaseIndex, phasesToShow.length - 1)}
              status={isDone ? "finish" : "process"}
              size="small"
              items={phasesToShow.map((phase) => ({
                title: (
                  <span style={{ fontSize: 12, color: isDone ? "#15be53" : store.currentPhase === phase ? "#533afd" : "#64748d" }}>
                    {ANALYSIS_PHASE_LABELS[phase] || phase}
                  </span>
                ),
              }))}
            />
          </div>
        )}

        {/* 主内容区 */}
        <div style={{ flex: 1, overflow: "hidden", display: "flex", position: "relative" }}>
          {showSidebar && (
            <div style={{ width: 240, flexShrink: 0, borderRight: "1px solid #e5edf5", overflowY: "auto", padding: "8px 12px", background: "#fafbfc", paddingBottom: 48 }}>
              <Text style={{ fontSize: 12, color: "#64748d", display: "block", marginBottom: 8 }}>
                {isDone ? "分析回顾" : "分析进度"}
              </Text>
              <AgentProgressPanel />
            </div>
          )}

          <div style={{ flex: 1, overflowY: "auto", padding: "20px 24px", paddingBottom: 56 }}>
            {/* === Done 态 === */}
            {isDone && (
              <>
                {(store.title || store.summary || store.industries.length > 0) && (
                  <div style={{ marginBottom: 20 }}>
                    <SummaryCard title={store.title} summary={store.summary} industries={store.industries} stockName={store.stockName} stockCode={store.stockCode} analysisMode={store.analysisMode} dataSource={store.dataSource} />
                  </div>
                )}
                {store.decision && (
                  <div style={{ marginBottom: 20 }}>
                    <SectionHeader icon={<DollarOutlined />} title="投资决策" />
                    <DecisionCard decision={store.decision} />
                  </div>
                )}
                {Object.keys(store.agentReports).length > 0 && (
                  <div style={{ marginBottom: 20 }}>
                    <SectionHeader icon={<TeamOutlined />} title="分析师报告" />
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 12 }}>
                      {Object.entries(store.agentReports).map(([agent, summary]) => {
                        if (isQuickMode && agent !== "market_analyst" && agent !== "fundamentals_analyst") return null;
                        return <AgentReportCard key={agent} agent={agent} summary={summary} gridMode />;
                      })}
                    </div>
                  </div>
                )}
                {!isQuickMode && store.debates.length > 0 && (
                  <div style={{ marginBottom: 20 }}>
                    <SectionHeader icon={<SwapOutlined />} title="投资辩论" />
                    <DebateTimeline debates={store.debates} />
                  </div>
                )}
                {!isQuickMode && (
                  <div style={{ marginBottom: 20 }}>
                    <SectionHeader icon={<SafetyCertificateOutlined />} title="风险评估" />
                    <RiskAssessmentSection debates={store.debates} decision={store.decision ?? undefined} />
                  </div>
                )}
                {store.stockCode && (
                  <div style={{ marginTop: 8 }}>
                    <Divider style={{ margin: "8px 0 12px" }} />
                    <SectionHeader icon={<HistoryOutlined />} title="历史分析" />
                    <AnalysisHistoryList stockCode={store.stockCode} />
                  </div>
                )}
              </>
            )}

            {/* === Running 态 === */}
            {isRunning && (
              <>
                {Object.keys(store.agentStatuses).length === 0 && store.thinkingSteps.length === 0 && (
                  <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: "60px 0" }}>
                    <Spin size="large" />
                    <Text style={{ fontSize: 13, color: "#64748d", marginTop: 16 }}>
                      正在初始化分析流程...
                    </Text>
                  </div>
                )}
                {store.thinkingSteps.length > 0 && (
                  <div style={{ marginBottom: 16 }}>
                    <SectionHeader title="AI 思维过程" />
                    <ThinkingChain steps={store.thinkingSteps} completed={isDone} />
                  </div>
                )}
                {phasesToShow.map((phase) => {
                  const phaseLabel = ANALYSIS_PHASE_LABELS[phase] || phase;
                  const isCompleted = PHASE_ORDER.indexOf(phase) < PHASE_ORDER.indexOf(store.currentPhase);
                  const isUpcoming = PHASE_ORDER.indexOf(phase) > PHASE_ORDER.indexOf(store.currentPhase);
                  if (isUpcoming) return null;
                  if (isCompleted) {
                    const isPhaseCollapsed = collapsedPhases.includes(phase);
                    return (
                      <div key={phase} style={{ marginBottom: 12 }}>
                        <div
                          onClick={() => {
                            setCollapsedPhases((prev) =>
                              isPhaseCollapsed ? prev.filter((p) => p !== phase) : [...prev, phase]
                            );
                          }}
                          style={{ display: "flex", alignItems: "center", gap: 8, padding: "8px 12px", background: "#f9f9f9", borderRadius: 6, cursor: "pointer" }}
                        >
                          <span style={{ fontSize: 13, color: "#52c41a" }}>✓</span>
                          <Text style={{ fontSize: 12, color: "#52c41a", fontWeight: 500 }}>{phaseLabel}已完成</Text>
                          <Text style={{ fontSize: 11, color: "#bfbfbf" }}>{isPhaseCollapsed ? "点击展开" : "点击收起"}</Text>
                          <span style={{ fontSize: 10, color: "#bfbfbf", marginLeft: "auto", transform: isPhaseCollapsed ? "rotate(-90deg)" : "rotate(0)", transition: "transform 0.2s ease" }}>▾</span>
                        </div>
                        {!isPhaseCollapsed && (
                          <div style={{ marginTop: 8, paddingLeft: 8 }}>{renderPhaseContent(phase)}</div>
                        )}
                      </div>
                    );
                  }
                  return (
                    <div key={phase} style={{ marginBottom: 16 }}>
                      <SectionHeader title={phaseLabel} />
                      {renderPhaseContent(phase)}
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
              </>
            )}

            {isError && (
              <Alert type="error" message="分析失败" description={store.error} showIcon style={{ marginBottom: 16, borderRadius: 6 }} />
            )}
          </div>

          {/* 合规提示 */}
          <div style={{ position: "absolute", bottom: 0, left: showSidebar ? 240 : 0, right: 0, textAlign: "center", padding: "8px 0", background: "linear-gradient(transparent, #ffffff 30%)", pointerEvents: "none", zIndex: 10 }}>
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
        `}</style>
      </div>
    </>
  );
};

export default StockAnalysisDebugPage;
