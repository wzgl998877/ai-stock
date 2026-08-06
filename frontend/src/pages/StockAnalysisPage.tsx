/** StockAnalysisPage -- 个股分析主页面（含可视化+历史+快速模式） */

import React, { useCallback, useEffect, useRef, useState } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { Button, Typography, Card, Steps, Spin, Alert, Space, Divider, Badge, Tag, Modal, Tabs, Progress } from "antd";
import {
  PlayCircleOutlined,
  RedoOutlined,
  StockOutlined,
  SwapOutlined,
  DatabaseOutlined,
  TeamOutlined,
  DollarOutlined,
  SafetyCertificateOutlined,
  LineChartOutlined,
  FundOutlined,
  ReadOutlined,
  CheckCircleOutlined,
  FileTextOutlined,
  ThunderboltOutlined,
  ExperimentOutlined,
} from "@ant-design/icons";
import StockSearchInput from "../components/stock-analysis/StockSearchInput";
import SystemStatusBar from "../components/stock-analysis/SystemStatusBar";
import ModeSelectionCards from "../components/stock-analysis/ModeSelectionCards";
import AgentProgressPanel from "../components/stock-analysis/AgentProgressPanel";
import AgentReportCard from "../components/stock-analysis/AgentReportCard";
import AgentReportDrawer from "../components/stock-analysis/AgentReportDrawer";
import DebateTimeline from "../components/stock-analysis/DebateTimeline";

import AnalysisHistoryList from "../components/stock-analysis/AnalysisHistoryList";
import AnalysisComparison from "../components/stock-analysis/AnalysisComparison";
import RiskAssessmentSection from "../components/stock-analysis/RiskAssessmentSection";
import SummaryCard from "../components/stock-analysis/SummaryCard";
import SectionHeader from "../components/stock-analysis/SectionHeader";
import ThinkingChain from "../components/chat/ThinkingChain";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { AGENT_PROFILES, AGENT_DISPLAY_NAMES, PHASE_AGENT_ORDER } from "../domain/constants";
import { useStockAnalysisStore } from "../store/stockAnalysisStore";
import * as stockAnalysisService from "../services/stockAnalysisService";
import { getAnalysisRecord } from "../services/stockAnalysisService";
import { stockDataService } from "../services/stockDataService";
import { toPercent } from "../utils/textUtils";
import {
  ANALYSIS_PHASE_LABELS,
} from "../domain/constants";
import { AnalysisMode } from "../domain/types";
import type { StockSSEEvent, AgentStatusEvent, DebateEvent, DecisionEvent, AgentReportEvent, ThinkingStepData } from "../domain/types";

const { Text, Title } = Typography;

/** 分析阶段顺序 */
const PHASE_ORDER = ["analysts", "debate", "trader", "risk"];

/** 各模式下各阶段的 agent 列表（与后端 QUICK_MODE_AGENTS / FULL_MODE_AGENTS 一致） */
const PHASE_AGENTS_FULL: Record<string, string[]> = {
  analysts: ["market_analyst", "fundamentals_analyst", "news_analyst", "sentiment_analyst"],
  debate: ["bull_researcher", "bear_researcher", "research_manager"],
  trader: ["trader"],
  risk: ["risky_debator", "safe_debator", "neutral_debator", "risk_judge"],
};
const PHASE_AGENTS_QUICK: Record<string, string[]> = {
  analysts: ["market_analyst", "fundamentals_analyst"],
  trader: ["trader"],
};
const PHASE_ORDER_QUICK = ["analysts", "trader"];

// ============================================================
// 分析维度展示配置（只读，随模式切换）
// ============================================================

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
  { icon: <ReadOutlined />, name: "新闻舆情哨兵", color: "#f59e0b", description: "扫描 7 日新闻，识别利好/利空舆情信号", status: "ready" },
  { icon: <SafetyCertificateOutlined />, name: "风险评估官", color: "#ef4444", description: "多维度量化风险，给出安全边际建议", status: "ready" },
];

const QUICK_ANALYSTS: AnalystReadyCard[] = [
  { icon: <LineChartOutlined />, name: "技术面分析师", color: "#3b82f6", description: "分析K线形态、均线系统、MACD/KDJ信号", status: "ready" },
  { icon: <FundOutlined />, name: "基本面分析师", color: "#8b5cf6", description: "评估财务指标、估值水平、盈利能力", status: "ready" },
];

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

// ============================================================
// Running 态专用子组件
// ============================================================

/** 假进度条 — 每个 Agent 开始时从 0% 缓慢增长到 90%，完成后跳 100% */
const FakeProgress: React.FC<{ agentName: string; agentDone: boolean; agentKey: string }> = ({ agentName, agentDone, agentKey }) => {
  const [percent, setPercent] = useState(0);
  const agentKeyRef = useRef(agentKey);

  const profile = AGENT_PROFILES[agentKey];

  // Agent 切换时重置进度
  useEffect(() => {
    if (agentKey !== agentKeyRef.current) {
      agentKeyRef.current = agentKey;
      setPercent(0);
    }
  }, [agentKey]);

  // 假进度：0 → 90%，每次 +1~3%
  useEffect(() => {
    if (agentDone) {
      setPercent(100);
      return;
    }
    const timer = setInterval(() => {
      setPercent((prev) => {
        if (prev >= 90) return prev;
        const inc = Math.floor(Math.random() * 3) + 1;
        return Math.min(prev + inc, 90);
      });
    }, 800 + Math.random() * 600);
    return () => clearInterval(timer);
  }, [agentDone]);

  return (
    <div style={{
      marginBottom: 20,
      padding: "20px 24px",
      background: "linear-gradient(135deg, #faf8ff 0%, #f5f0ff 100%)",
      borderRadius: 12,
      border: "1px solid #e8e0ff",
      position: "relative",
      overflow: "hidden",
    }}>
      {/* 装饰性背景光晕 */}
      <div style={{
        position: "absolute",
        top: -20,
        right: -20,
        width: 120,
        height: 120,
        borderRadius: "50%",
        background: `${profile?.color || "#533afd"}08`,
        pointerEvents: "none",
      }} />

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div style={{
            width: 32,
            height: 32,
            borderRadius: 8,
            background: `${profile?.color || "#533afd"}15`,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: 16,
            flexShrink: 0,
          }}>
            {profile?.emoji || "🤖"}
          </div>
          <div>
            <Text style={{ fontSize: 14, fontWeight: 600, color: "#1f2937", display: "block" }}>
              {agentName}工作中
            </Text>
            <Text style={{ fontSize: 12, color: "#8c8c8c" }}>
              {agentDone ? "分析完成" : "正在深度分析数据..."}
            </Text>
          </div>
        </div>
        <Text style={{
          fontSize: 24,
          fontWeight: 700,
          color: agentDone ? "#15be53" : profile?.color || "#533afd",
          fontFeatureSettings: "'tnum'",
          lineHeight: 1,
        }}>
          {percent}%
        </Text>
      </div>
      <Progress
        percent={percent}
        status={agentDone ? "success" : "active"}
        showInfo={false}
        strokeColor={agentDone ? "#15be53" : { "0%": profile?.color || "#533afd", "100%": profile?.bgColor || "#8b5cf6" }}
        trailColor="#e8e0ff"
        size="small"
        style={{ marginBottom: 0 }}
      />
    </div>
  );
};

/** 阶段导航项 */
const PhaseNavItem: React.FC<{
  phase: string;
  status: "completed" | "running" | "upcoming";
  onClick: () => void;
  isActive: boolean;
  agentCount: number;
}> = ({ phase, status, onClick, isActive, agentCount }) => {
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
        padding: "14px 16px",
        borderRadius: 10,
        border: `1.5px solid ${isActive ? c.border : "transparent"}`,
        background: isActive ? c.bg : "transparent",
        cursor: status === "upcoming" ? "default" : "pointer",
        transition: "all 0.2s ease",
        marginBottom: 8,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 4 }}>
        <div
          style={{
            width: 14,
            height: 14,
            borderRadius: "50%",
            background: c.icon,
            flexShrink: 0,
            ...(status === "running" ? { animation: "agentPulse 1.5s ease-in-out infinite" } : {}),
          }}
        />
        <span style={{ fontSize: 15, fontWeight: isActive ? 600 : 500, color: status === "upcoming" ? "#bfbfbf" : "#1f2937" }}>
          {ANALYSIS_PHASE_LABELS[phase] || phase}
        </span>
        {status === "completed" && <CheckCircleOutlined style={{ fontSize: 14, color: "#52c41a", marginLeft: "auto" }} />}
        {status === "running" && <span style={{ marginLeft: "auto", fontSize: 12, color: "#533afd", fontWeight: 500 }}>进行中</span>}
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", paddingLeft: 24 }}>
        <span style={{ fontSize: 12, color: "#8c8c8c" }}>{agentCount} 位 Agent</span>
      </div>
    </div>
  );
};

/** 获取阶段 Agent 数量 */
const getPhaseAgentCount = (phase: string, isQuick: boolean) => {
  const map = isQuick ? PHASE_AGENTS_QUICK : PHASE_AGENTS_FULL;
  return (map[phase] || []).length;
};

// ============================================================
// 页面组件
// ============================================================

const StockAnalysisPage: React.FC = () => {
  const store = useStockAnalysisStore();
  const navigate = useNavigate();
  const abortRef = useRef<AbortController | null>(null);
  const pollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const pollRecordIdRef = useRef<string>("");
  const loadVersionRef = useRef<number>(0);  // loadRecord 竞态保护：递增版本号
  const [comparisonOpen, setComparisonOpen] = useState(false);
  const [historyItems] = useState<any[]>([]);
  const [starting, setStarting] = useState(false);
  const [searchParams] = useSearchParams();
  const [activePhase, setActivePhase] = useState<string>("analysts");
  const [doneActiveTab, setDoneActiveTab] = useState("overview");
  const [phaseTransition, setPhaseTransition] = useState<{ from: string; to: string } | null>(null);
  const prevPhaseRef = useRef<string>("");

  // 记录当前分析中的股票（从接口拉取）
  const [currentAnalyzing, setCurrentAnalyzing] = useState<{ code: string; name: string; recordId: string } | null>(null);

  // 当前股价（用于计算预期收益）
  const [currentPrice, setCurrentPrice] = useState<number | null>(null);

  // 分析完成且有目标价时，获取当前股价用于预期收益计算
  useEffect(() => {
    if (store.analysisState !== "done" || !store.stockCode || !store.decision?.target_price) {
      setCurrentPrice(null);
      return;
    }
    stockDataService.getStockQuote(store.stockCode).then((quote) => {
      if (quote?.price) {
        setCurrentPrice(quote.price);
      }
    }).catch(() => {
      // 获取股价失败不影响展示
    });
  }, [store.analysisState, store.stockCode, store.decision?.target_price]);

  // 预期收益计算

  // 预期收益计算
  const expectedReturn = (() => {
    if (!store.decision?.target_price || !currentPrice || currentPrice <= 0) return null;
    return ((store.decision.target_price - currentPrice) / currentPrice * 100);
  })();

  // idle 时从接口拉取正在分析中的记录
  useEffect(() => {
    if (!store.analysisState || store.analysisState !== "idle") return;

    const fetchAnalyzing = async () => {
      try {
        const res = await stockAnalysisService.listAnalysisRecords({ status: "in_progress", page: 1, pageSize: 1 });
        if (res.items && res.items.length > 0) {
          const item = res.items[0];
          const stock = item.stocks?.[0];
          if (stock) {
            setCurrentAnalyzing({
              code: stock.code,
              name: stock.name,
              recordId: item.id,
            });
          }
        } else {
          setCurrentAnalyzing(null);
        }
      } catch {
        setCurrentAnalyzing(null);
      }
    };

    fetchAnalyzing();
    // 每 3 秒轮询一次，保持状态同步
    const timer = setInterval(fetchAnalyzing, 3000);
    return () => clearInterval(timer);
  }, [store.analysisState]);

  // 页面挂载时：如果有 recordId 则加载记录，否则强制 reset 到 idle（确保每次进入都是新分析入口）
  useEffect(() => {
    const recordId = searchParams.get("recordId");
    if (recordId) {
      // 停止旧轮询
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current);
        pollTimerRef.current = null;
      }
      pollRecordIdRef.current = "";  // 使飞行中的旧轮询响应失效

      // 立即清空显示数据，防止切换记录时闪现旧数据
      // 同时设置 analysisState 为 done，防止异步加载期间闪现 idle 入口页
      useStockAnalysisStore.setState({
        analysisState: "done",
        viewMode: true,
        viewRecordId: recordId,  // 立即设置，防止轮询干扰
        title: "",
        summary: "",
        fullContent: "",
        industries: [],
        agentReports: {},
        agentFullReports: {},
        agentStatuses: {},
        agentCompletedAt: {},
        debates: [],
        decision: null,
        content: "",
        thinkingSteps: [],
        contentBlocks: [],
        error: "",
      });

      // 从记录加载模式
      const version = ++loadVersionRef.current;  // 递增版本号，过期响应会被丢弃
      const loadRecord = async () => {
        try {
          const record = await getAnalysisRecord(recordId);

          // 竞态保护：如果版本号已过期（用户点击了另一条记录），丢弃本次响应
          if (loadVersionRef.current !== version) return;

          // 从 details 数组构建 agentReports、agentFullReports、agentStatuses
          const agentReports: Record<string, string> = {};
          const agentFullReports: Record<string, string> = {};
          const agentCompletedAt: Record<string, number> = {};
          const agentStatuses: Record<string, string> = {};
          const debates: DebateEvent[] = [];

          for (const d of record.details || []) {
            agentStatuses[d.agent_name] = d.status || "pending";
            if (d.summary) {
              agentReports[d.agent_name] = d.summary;
            }
            if (d.full_report) {
              agentFullReports[d.agent_name] = d.full_report;
            }
            if (d.completed_at) {
              agentCompletedAt[d.agent_name] = new Date(d.completed_at).getTime();
            }
            // 提取辩论数据：将 debate_data 转换为 DebateEvent 格式 {speaker, round, content}
            if (d.debate_data) {
              const dd = d.debate_data as Record<string, unknown>;
              const round = (dd.round as number) || 0;
              // 投资辩论
              if (dd.bull_argument) {
                debates.push({ speaker: "bull_researcher", round, content: dd.bull_argument as string });
              }
              if (dd.bear_argument) {
                debates.push({ speaker: "bear_researcher", round, content: dd.bear_argument as string });
              }
              // 风险辩论
              if (dd.risky_view) {
                debates.push({ speaker: "risky_debator", round, content: dd.risky_view as string });
              }
              if (dd.safe_view) {
                debates.push({ speaker: "safe_debator", round, content: dd.safe_view as string });
              }
              if (dd.neutral_view) {
                debates.push({ speaker: "neutral_debator", round, content: dd.neutral_view as string });
              }
            }
            // 非辩论阶段 agent 的报告也加入 debates（供 DebateTimeline/RiskAssessmentSection 使用）
            if (d.phase === "debate" && (d.agent_name === "research_manager") && d.full_report) {
              debates.push({ speaker: d.agent_name, round: 0, content: d.full_report });
            }
            if (d.phase === "risk" && d.agent_name === "risk_judge" && d.full_report) {
              debates.push({ speaker: d.agent_name, round: 0, content: d.full_report });
            }
          }

          // 设置股票信息
          const stockInfo = record.stocks?.[0];

          // 从 industries 提取名称列表
          const industryNames = (record.industries || []).map(i => i.code);

          // 使用后端返回的 current_phase，仅在缺失时推断
          let currentPhase: string;
          if (record.current_phase) {
            currentPhase = record.current_phase;
          } else if (record.status === "completed" || record.status === "stopped") {
            currentPhase = "done";
          } else {
            // 兜底推断
            const hasRunning = Object.values(agentStatuses).some(s => s === "running");
            if (hasRunning) {
              const details = record.details || [];
              const runningDetail = details.find(d => d.status === "running");
              currentPhase = runningDetail?.phase || "analysts";
            } else {
              const details = record.details || [];
              const doneDetails = details.filter(d => d.status === "done");
              if (doneDetails.length > 0) {
                currentPhase = doneDetails[doneDetails.length - 1].phase || "analysts";
              } else {
                currentPhase = "analysts";
              }
            }
          }

          store.loadFromRecord({
            recordId: record.id,
            stockCode: stockInfo?.code,
            stockName: stockInfo?.name,
            title: record.title,
            summary: record.summary,
            fullContent: record.content,
            industries: industryNames,
            agentReports,
            agentFullReports,
            agentStatuses,
            debates,
            decision: record.decision as any,
            agentCompletedAt,
            analysisMode: record.analysis_mode as AnalysisMode,
            currentPhase,
            status: record.status,
          });
        } catch (err) {
          console.error("加载分析记录失败:", err);
        }
      };
      loadRecord();
    } else {
      // 无 recordId → 强制 reset 到 idle（每次进入都是新分析入口）
      store.reset();
      // FR-017：支持 ?code= 预填（来自信号徽标「AI 深度分析」等入口）
      const code = searchParams.get("code");
      if (code) {
        stockAnalysisService
          .validateStock(code)
          .then((res) => {
            if (res.valid && res.stock_code) {
              useStockAnalysisStore.getState().setStock(res.stock_code, res.stock_name || "");
            }
          })
          .catch(() => {
            /* 预填失败不阻断入口，用户可手动搜索 */
          });
      }
    }
  }, [searchParams]);

  const isIdle = store.analysisState === "idle";
  const isRunning = store.analysisState === "running";
  const isDone = store.analysisState === "done";
  const isError = store.analysisState === "error";
  const isQuickMode = store.analysisMode === AnalysisMode.QUICK;

  // Fetch data source info when stock code changes
  useEffect(() => {
    if (!store.stockCode) return;
    stockDataService.getStockBasic(store.stockCode)
      .then((info) => {
        if (info?.data_source) {
          store.setDataSource(info.data_source);
        }
      })
      .catch(() => {
        // Silently fail — data may not be synced yet
      });
  }, [store.stockCode, store.setDataSource]);

  // 轮询机制：分析进行中时定期拉取最新进度
  useEffect(() => {
    if (!isRunning || !store.viewRecordId) return;

    // 清除旧定时器
    if (pollTimerRef.current) clearInterval(pollTimerRef.current);

    pollRecordIdRef.current = store.viewRecordId;

    // 立即拉一次
    const reqRecordId = store.viewRecordId;  // 记住请求时的 recordId
    stockAnalysisService.getAnalysisProgress(reqRecordId)
      .then((progress) => {
        // 竞态保护：如果用户已切换到其他记录，丢弃本次响应
        if (pollRecordIdRef.current !== reqRecordId) return;
        const st = useStockAnalysisStore.getState();
        st.loadRunningState({
          currentPhase: progress.current_phase || "analysts",
          agents: progress.agents || {},
          debates: progress.debates || [],
          decision: progress.decision,
          title: progress.title || "",
          summary: progress.summary || "",
          industries: progress.industries || [],
        });
        if (progress.status === "done" || progress.status === "stopped") {
          // 获取完整报告内容 + agent fullReports
          getAnalysisRecord(pollRecordIdRef.current)
            .then((record) => {
              if (!record) return;
              const s = useStockAnalysisStore.getState();
              if (record.content) {
                s.setFullContent(record.content);
              }
              const fullReports: Record<string, string> = { ...s.agentFullReports };
              for (const d of record.details || []) {
                if (d.full_report) {
                  fullReports[d.agent_name] = d.full_report;
                }
              }
              useStockAnalysisStore.setState({ agentFullReports: fullReports });
            })
            .catch(() => {});
          useStockAnalysisStore.setState({ analysisState: "done" });
          useStockAnalysisStore.getState().triggerHistoryRefresh();
          setCurrentAnalyzing(null);
        }
      })
      .catch(() => {
        // 静默失败
      });

    // 每 3 秒轮询
    pollTimerRef.current = setInterval(() => {
      const pollId = pollRecordIdRef.current;  // 记住本次轮询的 recordId
      if (!pollId) return;
      stockAnalysisService.getAnalysisProgress(pollId)
        .then((progress) => {
          // 竞态保护：如果用户已切换到其他记录，丢弃本次响应
          if (pollRecordIdRef.current !== pollId) return;
          const st = useStockAnalysisStore.getState();
          st.loadRunningState({
            currentPhase: progress.current_phase || "analysts",
            agents: progress.agents || {},
            debates: progress.debates || [],
            decision: progress.decision,
            title: progress.title || "",
            summary: progress.summary || "",
            industries: progress.industries || [],
          });
          if (progress.status === "done" || progress.status === "stopped") {
            // 获取完整报告内容 + agent fullReports
            getAnalysisRecord(pollRecordIdRef.current)
              .then((record) => {
                if (!record) return;
                const s = useStockAnalysisStore.getState();
                if (record.content) {
                  s.setFullContent(record.content);
                }
                const fullReports: Record<string, string> = { ...s.agentFullReports };
                for (const d of record.details || []) {
                  if (d.full_report) {
                    fullReports[d.agent_name] = d.full_report;
                  }
                }
                useStockAnalysisStore.setState({ agentFullReports: fullReports });
              })
              .catch(() => {});
            useStockAnalysisStore.setState({ analysisState: "done" });
            useStockAnalysisStore.getState().triggerHistoryRefresh();
            setCurrentAnalyzing(null);
            if (pollTimerRef.current) clearInterval(pollTimerRef.current);
          }
        })
        .catch(() => {
          // 静默失败
        });
    }, 3000);

    return () => {
      if (pollTimerRef.current) clearInterval(pollTimerRef.current);
    };
  }, [isRunning, store.viewRecordId]);

  /** 发起分析 */
  const handleStart = useCallback(async () => {
    if (!store.stockCode || !store.stockName) return;

    setStarting(true);
    await new Promise((r) => setTimeout(r, 300));

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    store.startAnalysis();
    setStarting(false);

    try {
      const session = await stockAnalysisService.createStockAnalysisSession({
        stock_code: store.stockCode,
        stock_name: store.stockName,
        analysis_mode: store.analysisMode,
      });

      // 获取最近创建的分析记录 ID，用于轮询恢复
      try {
        const recent = await stockAnalysisService.checkRecentAnalysis(store.stockCode, 1);
        if (recent.has_recent && recent.article_id) {
          useStockAnalysisStore.setState({ viewRecordId: recent.article_id });
          pollRecordIdRef.current = recent.article_id;
        }
      } catch {
        // 静默失败，不影响正常流程
      }

      await stockAnalysisService.streamStockAnalysis(
        session.id,
        {
          stock_code: store.stockCode,
          stock_name: store.stockName,
          analysis_mode: store.analysisMode,
          content: `请对${store.stockName}(${store.stockCode})进行${store.analysisMode === "full" ? "深度" : "快速"}分析`,
        },
        (event: StockSSEEvent) => {
          const st = useStockAnalysisStore.getState();
          switch (event.type) {
            case "analysis_id":
              useStockAnalysisStore.setState({ viewRecordId: event.data as string });
              pollRecordIdRef.current = event.data as string;
              break;
            case "agent_status":
              st.updateAgentStatus(event.data as AgentStatusEvent);
              // 阶段完成时触发过渡
              if ((event.data as AgentStatusEvent).status === "done") {
                const phase = (event.data as AgentStatusEvent).phase;
                if (phase && phase !== st.currentPhase) {
                  const prev = st.currentPhase;
                  setPhaseTransition({ from: prev, to: phase });
                  setActivePhase(phase);
                  st.setCurrentPhase(phase);
                  setTimeout(() => setPhaseTransition(null), 3000);
                }
              }
              break;
            case "thinking":
              st.addThinkingStep(event.data as ThinkingStepData);
              break;
            case "agent_report":
              {
                const report = event.data as AgentReportEvent;
                st.addAgentReport(report.agent, report.summary, report.full_report);
              }
              break;
            case "debate": {
              // 后端 SSE 发送 {agent, argument}，前端 DebateEvent 需要 {speaker, content}
              const dd = event.data as unknown as Record<string, unknown>;
              st.addDebate({
                speaker: (dd.agent || dd.speaker) as string,
                round: (dd.round as number) || 0,
                content: (dd.argument || dd.content || "") as string,
              });
              break;
            }
            case "decision":
              st.setDecision(event.data as DecisionEvent);
              break;
            case "content":
              st.appendContent(event.data as string);
              break;
            case "title":
              st.setTitle(event.data as string);
              break;
            case "summary":
              st.setSummary(event.data as string);
              break;
            case "industries":
              st.setIndustries(event.data as string[]);
              break;
            case "done":
              if (pollTimerRef.current) clearInterval(pollTimerRef.current);
              // 获取完整报告内容 + agent fullReports
              {
                const recordId = useStockAnalysisStore.getState().viewRecordId;
                if (recordId) {
                  getAnalysisRecord(recordId)
                    .then((record) => {
                      if (!record) return;
                      const s = useStockAnalysisStore.getState();
                      if (record.content) {
                        s.setFullContent(record.content);
                      }
                      // 从 details 补充 agentFullReports（SSE 只推了 summary，没推 full_report）
                      const fullReports: Record<string, string> = { ...s.agentFullReports };
                      for (const d of record.details || []) {
                        if (d.full_report) {
                          fullReports[d.agent_name] = d.full_report;
                        }
                      }
                      useStockAnalysisStore.setState({ agentFullReports: fullReports });
                    })
                    .catch(() => {});
                }
              }
              useStockAnalysisStore.setState({ analysisState: "done" });
              useStockAnalysisStore.getState().triggerHistoryRefresh();
              break;
            case "error":
              st.setError(event.data as string);
              break;
          }
        },
        controller.signal
      );
    } catch (err) {
      if ((err as Error).name === "AbortError") return;
      store.setError(err instanceof Error ? err.message : "分析失败");
    }
  }, [store]);

  const handleStop = useCallback(() => {
    Modal.confirm({
      title: "确认停止当前分析？",
      content: "已生成部分将保留在分析记录中。",
      okText: "确认停止",
      cancelText: "继续分析",
      onOk: async () => {
        abortRef.current?.abort();
        if (pollTimerRef.current) clearInterval(pollTimerRef.current);
        // 通知后端停止分析任务
        const recordId = useStockAnalysisStore.getState().viewRecordId;
        if (recordId) {
          try {
            await stockAnalysisService.stopAnalysis(recordId);
          } catch {
            // 静默处理，后端可能已停止
          }
        }
        useStockAnalysisStore.setState({ analysisState: "done" });
      },
    });
  }, []);

  const handleReset = useCallback(() => {
    Modal.confirm({
      title: "确认重新分析？",
      content: "当前结果将保留在历史记录中。",
      okText: "确认",
      cancelText: "取消",
      onOk: () => {
        if (pollTimerRef.current) clearInterval(pollTimerRef.current);
        store.reset();
      },
    });
  }, [store]);

  const phasesToShow = isQuickMode ? PHASE_ORDER_QUICK : PHASE_ORDER;
  const phaseAgents = isQuickMode ? PHASE_AGENTS_QUICK : PHASE_AGENTS_FULL;

  const currentPhaseIndex = phasesToShow.indexOf(store.currentPhase);

  // 阶段变化时显示过渡提示
  useEffect(() => {
    if (!isRunning || !store.currentPhase) return;
    const prev = prevPhaseRef.current;
    const curr = store.currentPhase;
    if (prev && prev !== curr) {
      setPhaseTransition({ from: prev, to: curr });
      // 自动切换到当前阶段
      setActivePhase(curr);
      // 3秒后清除过渡提示
      const timer = setTimeout(() => setPhaseTransition(null), 3000);
      return () => clearTimeout(timer);
    }
    prevPhaseRef.current = curr;
  }, [store.currentPhase, isRunning]);

  /** 按阶段渲染内容 */
  const renderPhaseContent = (phase: string) => {
    switch (phase) {
      case "analysts":
        if (Object.keys(store.agentReports).length === 0) {
          return null;
        }
        return (
          <div>
            {PHASE_AGENT_ORDER.analysts
              .filter((agent) => isQuickMode ? agent === "market_analyst" || agent === "fundamentals_analyst" : true)
              .filter((agent) => store.agentReports[agent] || store.agentStatuses[agent])
              .map((agent) => {
                const profile = AGENT_PROFILES[agent];
                return (
                  <AgentReportCard
                    key={agent}
                    agent={agent}
                    summary={store.agentReports[agent] || ""}
                    isRunning={store.agentStatuses[agent] === "running"}
                    thinkingMessage={profile?.thinkingMessage}
                  />
                );
              })}
          </div>
        );

      case "debate":
        if (store.debates.length > 0) {
          return <DebateTimeline debates={store.debates} />;
        }
        // 复用 done 态空状态布局
        return (
          <div style={{ textAlign: "center", padding: 40 }}>
            <SwapOutlined style={{ fontSize: 32, color: "#d9d9d9", marginBottom: 12 }} />
            <div style={{ fontSize: 13, color: "#8c8c8c" }}>
              {getPhaseStatus("debate") === "running" ? "辩论即将开始..." : "等待分析师报告完成"}
            </div>
          </div>
        );

      case "trader": {
        const traderSummary = store.agentReports["trader"];
        const traderRunning = store.agentStatuses["trader"] === "running";
        // 复用 done 态 AgentReportCard 布局
        if (traderSummary) {
          return <AgentReportCard agent="trader" summary={traderSummary} />;
        }
        if (traderRunning) {
          return (
            <AgentReportCard
              agent="trader"
              summary=""
              isRunning={true}
              thinkingMessage="正在基于投资计划生成交易建议..."
            />
          );
        }
        return (
          <div style={{ textAlign: "center", padding: 40 }}>
            <DollarOutlined style={{ fontSize: 32, color: "#d9d9d9", marginBottom: 12 }} />
            <div style={{ fontSize: 13, color: "#8c8c8c" }}>
              {getPhaseStatus("trader") === "running" ? "交易决策准备中..." : "等待上游分析完成"}
            </div>
          </div>
        );
      }

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

  /** 获取阶段状态 — 基于该阶段内 agent 的完成状态判断 */
  const getPhaseStatus = (phase: string): "completed" | "running" | "upcoming" => {
    const agents = phaseAgents[phase] || [];
    if (agents.length === 0) return "upcoming";

    const allDone = agents.every((a) => store.agentStatuses[a] === "done");
    const anyRunning = agents.some((a) => store.agentStatuses[a] === "running");

    if (allDone) return "completed";
    if (anyRunning || store.currentPhase === phase) return "running";
    return "upcoming";
  };

  // === Idle 态（增强版） ===
  if (isIdle) {
    // 外层 AppLayout 有 56px 的 Header，这里减去
    const panelStyle: React.CSSProperties = {
      display: "flex",
      flexDirection: "column",
      background: "#fff",
      borderRadius: 12,
      border: "1px solid #f0f0f0",
      padding: "24px 24px 18px",
      boxShadow: "0 1px 3px rgba(0,0,0,0.04)",
    };
    // 两个面板底部区域统一高度，确保按钮与提示框对齐
    const bottomStyle: React.CSSProperties = {
      marginTop: "auto",
      minHeight: 72,
      display: "flex",
      flexDirection: "column",
      justifyContent: "flex-end",
    };

    return (
      <div style={{ height: "calc(100vh - 56px)", display: "flex", flexDirection: "column", padding: "24px 32px", overflow: "hidden" }}>
        <SystemStatusBar />

        <div style={{ display: "flex", gap: 24, flex: 1, minHeight: 0, alignItems: "stretch" }}>
          {/* ===== 左侧：分析配置卡片 ===== */}
          <div style={{ ...panelStyle, flex: "0 0 44%" }}>
            <div style={{ marginBottom: 20 }}>
              <h1 style={{ fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif", fontWeight: 500, fontSize: 18, color: "#061b31", margin: 0, marginBottom: 4, letterSpacing: "-0.3px" }}>
                分析配置
              </h1>
              <span style={{ fontSize: 12, color: "#8c8c8c" }}>选择标的和分析模式</span>
            </div>

            {/* 当前分析中的股票提示 */}
            {currentAnalyzing && (
              <div style={{
                padding: "10px 14px",
                borderRadius: 8,
                background: "linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%)",
                border: "1px solid #fde68a",
                marginBottom: 16,
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
              }}>
                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <Spin size="small" />
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 600, color: "#92400e" }}>
                      正在分析：{currentAnalyzing.name}({currentAnalyzing.code})
                    </div>
                    <div style={{ fontSize: 11, color: "#a16207", marginTop: 2 }}>
                      分析进行中，点击查看实时进度
                    </div>
                  </div>
                </div>
                <Button
                  size="small"
                  type="primary"
                  onClick={() => navigate(`/stock-analysis?recordId=${currentAnalyzing.recordId}`)}
                  style={{ borderRadius: 4, flexShrink: 0 }}
                >
                  查看进度
                </Button>
              </div>
            )}

            {/* 标的搜索 */}
            <div style={{ marginBottom: 16 }}>
              <label style={{ fontSize: 12, fontWeight: 500, color: "#273951", display: "block", marginBottom: 6 }}>分析标的</label>
              <StockSearchInput />
            </div>

            {/* 模式选择卡片 */}
            <div style={{ marginBottom: 16 }}>
              <label style={{ fontSize: 12, fontWeight: 500, color: "#273951", display: "block", marginBottom: 6 }}>分析模式</label>
              <ModeSelectionCards value={store.analysisMode} onChange={store.setMode} />
            </div>

            {/* 分析维度（只读，随模式切换） */}
            <div style={{ marginBottom: 16 }}>
              <label style={{ fontSize: 12, fontWeight: 500, color: "#273951", display: "block", marginBottom: 6 }}>
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

            {/* 底部：开始按钮 + 合规提示 */}
            <div style={bottomStyle}>
              <Button
                type="primary"
                size="large"
                block
                disabled={!store.stockCode || !store.stockName || store.validationLoading}
                onClick={handleStart}
                loading={starting}
                icon={!starting ? <PlayCircleOutlined /> : undefined}
                style={{ borderRadius: 8, fontWeight: 500, height: 44, fontSize: 15 }}
              >
                {starting ? "正在调动分析师..." : "开始分析"}
              </Button>
              <div style={{ textAlign: "center", marginTop: 8 }}>
                <Text style={{ fontSize: 11, color: "#c0c6cf" }}>本工具仅供投研参考，不构成任何投资建议</Text>
              </div>
            </div>
          </div>

          {/* ===== 右侧：AI 协作分析面板 ===== */}
          <div style={{ ...panelStyle, flex: "1 1 56%" }}>
            {/* 价值主张 */}
            <div style={{ marginBottom: 20 }}>
              <h1 style={{ fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif", fontWeight: 500, fontSize: 18, color: "#061b31", margin: 0, marginBottom: 4, letterSpacing: "-0.3px" }}>
                AI 协作分析
              </h1>
              <span style={{ fontSize: 12, color: "#8c8c8c", lineHeight: 1.5, display: "block" }}>
                多 Agent 协作，从技术面到风险评估，生成结构化投资分析报告
              </span>
            </div>

            {/* 分析师待命卡片 */}
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {(isQuickMode ? QUICK_ANALYSTS : FULL_ANALYSTS).map((card) => (
                <AnalystReadyCardItem key={card.name} card={card} />
              ))}
            </div>

            {/* 底部：模式动态提示（与左侧按钮对齐） */}
            <div style={bottomStyle}>
              <div style={{
                padding: "10px 16px",
                borderRadius: 10,
                background: isQuickMode ? "#f0fdf4" : "#f8f7ff",
                border: `1px solid ${isQuickMode ? "#bbf7d0" : "#e8e0ff"}`,
                display: "flex",
                alignItems: "center",
                gap: 10,
              }}>
                {isQuickMode ? (
                  <ThunderboltOutlined style={{ fontSize: 18, color: "#22c55e", flexShrink: 0 }} />
                ) : (
                  <ExperimentOutlined style={{ fontSize: 18, color: "#533afd", flexShrink: 0 }} />
                )}
                <div>
                  <div style={{ fontSize: 13, fontWeight: 600, color: isQuickMode ? "#166534" : "#3b1fde", marginBottom: 2 }}>
                    {isQuickMode ? "快速分析" : "深度分析"}
                  </div>
                  <div style={{ fontSize: 12, color: "#8c8c8c", lineHeight: 1.5 }}>
                    {isQuickMode
                      ? "2 位分析师协作 · 约 30-60 秒出结果"
                      : "4 位分析师 + 多空辩论 + 风险评估 · 约 3-5 分钟出完整报告"}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // === Running / Done / Error 态 ===
  return (
    <div style={{ height: "100vh", display: "flex", flexDirection: "column" }}>
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
            <Title level={4} style={{ margin: 0, fontWeight: 400, color: "#061b31", fontFeatureSettings: "'ss01' on" }}>
              {store.stockName}({store.stockCode}) {isQuickMode ? "快速" : "深度"}分析
            </Title>
            {store.title && (
              <Text style={{ fontSize: 13, color: "#64748d", fontFeatureSettings: "'ss01' on" }}>{store.title}</Text>
            )}
          </div>
          {store.dataSource && (
            <Tag color="blue" icon={<DatabaseOutlined />}>数据源: {store.dataSource}</Tag>
          )}
        </div>
        <Space>
          {isRunning && (
            <Button onClick={handleStop} style={{ borderRadius: 4 }}>停止分析</Button>
          )}
          {(isDone || isError) && (
            <Button icon={<RedoOutlined />} onClick={handleReset} style={{ borderRadius: 4 }}>重新分析</Button>
          )}
        </Space>
      </div>

      {/* ===== 阶段进度条 ===== */}
      {(isRunning || isDone) && (
        <div style={{ padding: "8px 24px", borderBottom: "1px solid #e5edf5", flexShrink: 0, background: "#fafbfc" }}>
          <Steps
            current={isDone ? phasesToShow.length : Math.min(currentPhaseIndex, phasesToShow.length - 1)}
            status={isDone ? "finish" : "process"}
            size="small"
            className="analysis-phase-steps"
            items={phasesToShow.map((phase) => ({
              title: (
                <span className="step-label" style={{ fontSize: 12, fontFeatureSettings: "'ss01' on", color: isDone ? "#15be53" : store.currentPhase === phase ? "#533afd" : "#64748d", transition: "color 0.3s ease" }}>
                  {ANALYSIS_PHASE_LABELS[phase] || phase}
                </span>
              ),
            }))}
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
            {/* 阶段完成过渡提示 */}
            {phaseTransition && (
              <div style={{
                position: "absolute",
                top: 0,
                left: 280,
                right: 280,
                zIndex: 100,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                padding: "8px 0",
                background: "linear-gradient(180deg, #f0fdf4 0%, transparent 100%)",
                pointerEvents: "none",
              }}>
                <div style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  padding: "6px 16px",
                  borderRadius: 20,
                  background: "#fff",
                  border: "1px solid #bbf7d0",
                  boxShadow: "0 2px 8px rgba(0,0,0,0.08)",
                }}>
                  <CheckCircleOutlined style={{ fontSize: 14, color: "#52c41a" }} />
                  <span style={{ fontSize: 12, color: "#166534", fontWeight: 500 }}>
                    {ANALYSIS_PHASE_LABELS[phaseTransition.from] || phaseTransition.from} 已完成，正在进入 {ANALYSIS_PHASE_LABELS[phaseTransition.to] || phaseTransition.to}...
                  </span>
                </div>
              </div>
            )}

            {/* 左栏：阶段导航 */}
            <div style={{ width: 300, flexShrink: 0, borderRight: "1px solid #e5edf5", overflowY: "auto", padding: "16px 14px", background: "#fafbfc" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 18 }}>
                <ThunderboltOutlined style={{ color: "#533afd", fontSize: 16 }} />
                <span style={{ fontSize: 14, fontWeight: 600, color: "#273951" }}>分析阶段</span>
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
                  agentCount={getPhaseAgentCount(phase, isQuickMode)}
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
            <div style={{ flex: 1, overflowY: "auto", padding: "20px 24px", paddingBottom: 56, maxWidth: 900, margin: "0 auto" }}>
              {/* 动态假进度条 — 展示当前激活阶段中正在运行的 agent */}
              {(() => {
                const currentPhaseAgents = phaseAgents[activePhase] || [];
                const runningAgent = currentPhaseAgents.find((a) => store.agentStatuses[a] === "running");
                // 没有 running 的，取第一个未 done 的 agent
                const activeAgent = runningAgent || currentPhaseAgents.find((a) => store.agentStatuses[a] !== "done");
                if (activeAgent && store.agentStatuses[activeAgent] !== "done") {
                  const agentName = AGENT_DISPLAY_NAMES[activeAgent] || activeAgent;
                  const agentDone = store.agentStatuses[activeAgent] === "done";
                  return <FakeProgress agentName={agentName} agentDone={agentDone} agentKey={activeAgent} />;
                }
                return null;
              })()}

              {/* 当前激活阶段内容 */}
              {activePhase && (
                <div>
                  <SectionHeader title={ANALYSIS_PHASE_LABELS[activePhase] || activePhase} />
                  {renderPhaseContent(activePhase)}
                </div>
              )}

              {/* 分析内容文本（兜底展示） */}
              {store.content && !store.decision && (
                <Card style={{ marginBottom: 16, borderRadius: 6, border: "1px solid #e5edf5" }} styles={{ body: { padding: "16px 20px" } }}>
                  <div style={{ fontSize: 14, color: "#061b31", lineHeight: 1.8, whiteSpace: "pre-wrap", fontFeatureSettings: "'ss01' on" }}>
                    {store.content}
                    <span style={{ display: "inline-block", width: 2, height: 16, background: "#533afd", marginLeft: 1, animation: "blink 1s infinite", verticalAlign: "middle" }} />
                  </div>
                </Card>
              )}
            </div>

            {/* 右栏：Agent 进度（原侧边栏保留） */}
            <div style={{ width: 300, flexShrink: 0, borderLeft: "1px solid #e5edf5", overflowY: "auto", padding: "10px 14px", background: "#fafbfc", paddingBottom: 48 }}>
              <Text style={{ fontSize: 14, fontWeight: 600, color: "#273951", display: "block", marginBottom: 10 }}>
                分析进度
              </Text>
              <AgentProgressPanel />
            </div>
          </>
        )}

        {/* ===== Done 态：总-分结构 ===== */}
        {isDone && (
          <>
            {/* 左栏：阶段回顾导航 */}
            <div style={{ width: 280, flexShrink: 0, borderRight: "1px solid #e5edf5", overflowY: "auto", padding: "16px 12px", background: "#fafbfc" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 16 }}>
                <CheckCircleOutlined style={{ color: "#52c41a", fontSize: 14 }} />
                <span style={{ fontSize: 12, fontWeight: 600, color: "#273951" }}>分析完成</span>
              </div>

              {/* 阶段回顾 */}
              <div style={{ marginBottom: 12 }}>
                <div style={{ fontSize: 11, fontWeight: 500, color: "#8c8c8c", marginBottom: 8, textTransform: "uppercase", letterSpacing: "0.5px" }}>分析阶段</div>
                {phasesToShow.map((phase) => (
                  <PhaseNavItem
                    key={phase}
                    phase={phase}
                    status="completed"
                    isActive={activePhase === phase}
                    onClick={() => setActivePhase(phase)}
                    agentCount={getPhaseAgentCount(phase, isQuickMode)}
                  />
                ))}
              </div>

              {/* 历史分析 */}
              {store.stockCode && (
                <>
                  <Divider style={{ margin: "12px 0" }} />
                  <div style={{ padding: "8px 12px" }}>
                    <div style={{ fontSize: 11, fontWeight: 500, color: "#8c8c8c", marginBottom: 8 }}>历史分析</div>
                    <AnalysisHistoryList stockCode={store.stockCode} onRefresh={store.historyRefreshKey} />
                  </div>
                </>
              )}
            </div>

            {/* 中栏：内容区（Tab 组织） */}
            <div style={{ flex: 1, overflowY: "auto", padding: "20px 24px", paddingBottom: 56, maxWidth: 900, margin: "0 auto" }}>
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
                            <div style={{ fontSize: 16, fontWeight: 600, color: store.decision.target_price ? "#15be53" : "#8c8c8c" }}>
                              {store.decision.target_price ? `${store.decision.target_price} 元` : "--"}
                            </div>
                          </div>
                          <div>
                            <div style={{ fontSize: 11, color: "#8c8c8c", marginBottom: 2 }}>止损价</div>
                            <div style={{ fontSize: 16, fontWeight: 500, color: store.decision.stop_loss_price ? "#ef4444" : "#8c8c8c" }}>
                              {store.decision.stop_loss_price ? `${store.decision.stop_loss_price} 元` : "--"}
                            </div>
                          </div>
                          <div>
                            <div style={{ fontSize: 11, color: "#8c8c8c", marginBottom: 2 }}>预期收益</div>
                            <div style={{ fontSize: 16, fontWeight: 600, color: expectedReturn !== null ? (expectedReturn >= 0 ? "#15be53" : "#ef4444") : "#8c8c8c" }}>
                              {expectedReturn !== null ? `${expectedReturn >= 0 ? "+" : ""}${expectedReturn.toFixed(1)}%` : "--"}
                            </div>
                          </div>
                        </div>
                      </div>

                      {/* 右侧：评分仪表盘 */}
                      <div style={{ display: "flex", gap: 20 }}>
                        <div style={{ textAlign: "center" }}>
                          <div style={{ position: "relative", width: 64, height: 64 }}>
                            <svg viewBox="0 0 36 36" style={{ transform: "rotate(-90deg)", width: 64, height: 64 }}>
                              <path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="#e8e8e8" strokeWidth="3" />
                              <path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="#533afd" strokeWidth="3" strokeDasharray={`${toPercent(store.decision.confidence)}, 100`} strokeLinecap="round" />
                            </svg>
                            <div style={{ position: "absolute", top: "50%", left: "50%", transform: "translate(-50%, -50%)", fontSize: 16, fontWeight: 700, color: "#533afd" }}>
                              {toPercent(store.decision.confidence).toFixed(0)}%
                            </div>
                          </div>
                          <div style={{ fontSize: 10, color: "#8c8c8c", marginTop: 2 }}>置信度</div>
                        </div>
                        <div style={{ textAlign: "center" }}>
                          <div style={{ position: "relative", width: 64, height: 64 }}>
                            <svg viewBox="0 0 36 36" style={{ transform: "rotate(-90deg)", width: 64, height: 64 }}>
                              <path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="#e8e8e8" strokeWidth="3" />
                              <path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="#ef4444" strokeWidth="3" strokeDasharray={`${toPercent(store.decision.risk_score)}, 100`} strokeLinecap="round" />
                            </svg>
                            <div style={{ position: "absolute", top: "50%", left: "50%", transform: "translate(-50%, -50%)", fontSize: 16, fontWeight: 700, color: "#ef4444" }}>
                              {toPercent(store.decision.risk_score).toFixed(0)}%
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
                    children: (() => {
                      const analystAgents = PHASE_AGENT_ORDER.analysts
                        .filter((agent) => isQuickMode ? agent === "market_analyst" || agent === "fundamentals_analyst" : true);
                      return (
                        <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 12 }}>
                          {analystAgents.map((agent) => {
                            const summary = store.agentReports[agent];
                            if (summary) {
                              return <AgentReportCard key={agent} agent={agent} summary={summary} gridMode />;
                            }
                            return (
                              <Card
                                key={agent}
                                size="small"
                                style={{ borderRadius: 6, border: "1px dashed #d9d9d9", background: "#fafafa", height: "100%" }}
                                styles={{ body: { padding: 12 } }}
                              >
                                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
                                  <div style={{
                                    width: 24, height: 24, borderRadius: "50%",
                                    background: "#f0f0f0", display: "flex", alignItems: "center", justifyContent: "center",
                                    fontSize: 12, color: "#8c8c8c",
                                  }}>
                                    {AGENT_DISPLAY_NAMES[agent]?.[0] || "?"}
                                  </div>
                                  <Text style={{ fontSize: 13, fontWeight: 500, color: "#8c8c8c" }}>
                                    {AGENT_DISPLAY_NAMES[agent] || agent}
                                  </Text>
                                </div>
                                <Text style={{ fontSize: 12, color: "#bfbfbf" }}>未生成报告（可能因 API 限流导致）</Text>
                              </Card>
                            );
                          })}
                        </div>
                      );
                    })(),
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
                      key: "trader",
                      label: <span><DollarOutlined style={{ marginRight: 4 }} />交易决策</span>,
                      children: (() => {
                        const traderSummary = store.agentReports["trader"];
                        return traderSummary ? (
                          <AgentReportCard agent="trader" summary={traderSummary} />
                        ) : (
                          <div style={{ textAlign: "center", padding: 40 }}>
                            <DollarOutlined style={{ fontSize: 32, color: "#d9d9d9", marginBottom: 8 }} />
                            <div style={{ fontSize: 13, color: "#8c8c8c" }}>暂无交易决策</div>
                          </div>
                        );
                      })(),
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
                    children: store.fullContent ? (
                      <div className="markdown-body" style={{ padding: "16px 0", fontSize: 14, lineHeight: 1.8 }}>
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>{store.fullContent}</ReactMarkdown>
                      </div>
                    ) : (
                      <div style={{ textAlign: "center", padding: 40 }}>
                        <FileTextOutlined style={{ fontSize: 32, color: "#d9d9d9", marginBottom: 8 }} />
                        <div style={{ fontSize: 13, color: "#8c8c8c" }}>暂无完整报告，请重新发起分析</div>
                      </div>
                    ),
                  },
                ]}
              />

              {/* 快速模式引导 */}
              {isQuickMode && (
                <div style={{
                  marginTop: 20,
                  padding: "12px 16px",
                  background: "#f8f7ff",
                  border: "1px solid #d6d9fc",
                  borderRadius: 6,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                }}>
                  <div>
                    <Text style={{ fontSize: 13, color: "#061b31", fontFeatureSettings: "'ss01' on" }}>想要更全面的分析？</Text>
                    <Text style={{ fontSize: 12, color: "#64748d", marginLeft: 4 }}>深度分析包含 4 位分析师 + 多空辩论 + 风险评估</Text>
                  </div>
                  <Button size="small" type="primary" ghost onClick={handleReset} style={{ borderRadius: 4, flexShrink: 0 }}>
                    试试深度分析
                  </Button>
                </div>
              )}

              {/* 对比分析 */}
              {historyItems.length >= 2 && (
                <div style={{ marginTop: 8 }}>
                  <AnalysisComparison open={comparisonOpen} onClose={() => setComparisonOpen(false)} items={historyItems} />
                </div>
              )}
            </div>
          </>
        )}

        {/* 完整报告 Drawer（Running/Done 均可使用） */}
        <AgentReportDrawer />

        {/* 合规提示 */}
        <div
          style={{
            position: "absolute",
            bottom: 0,
            left: (isRunning || isDone) ? 280 : 0,
            right: (isRunning) ? 280 : 0,
            textAlign: "center",
            padding: "8px 0",
            background: "linear-gradient(transparent, #ffffff 30%)",
            pointerEvents: "none",
            zIndex: 10,
          }}
        >
          <Text style={{ fontSize: 11, color: "#c0c6cf", fontFeatureSettings: "'ss01' on" }}>
            本工具仅供投研参考，不构成任何投资建议
          </Text>
        </div>
      </div>

      {/* 全局动画 keyframes */}
      <style>{`
        @keyframes blink {
          0%, 100% { opacity: 1; }
          50% { opacity: 0; }
        }
        @keyframes thinkingDots {
          0%, 20% { content: ''; }
          40% { content: '.'; }
          60% { content: '..'; }
          80%, 100% { content: '...'; }
        }
        .thinking-dots::after {
          display: inline-block;
          animation: thinkingDots 1.5s infinite;
          content: '';
        }
        @keyframes pulseProgress {
          0% { width: 5%; opacity: 0.6; }
          50% { width: 60%; opacity: 1; }
          100% { width: 95%; opacity: 0.6; }
        }
        .pulse-progress-bar {
          animation: pulseProgress 2.5s ease-in-out infinite;
        }
        /* Agent 呼吸脉冲 — 用于 running 态小圆点 */
        @keyframes agentPulse {
          0%, 100% { opacity: 1; transform: scale(1); }
          50% { opacity: 0.4; transform: scale(0.7); }
        }
        /* Agent 头像呼吸光晕 */
        @keyframes agentBreath {
          0%, 100% { box-shadow: 0 0 0 0px rgba(83, 58, 253, 0); }
          50% { box-shadow: 0 0 0 4px rgba(83, 58, 253, 0.1); }
        }
        /* Steps 阶段过渡 */
        .analysis-phase-steps .ant-steps-item-title {
          transition: color 0.3s ease !important;
        }
        .analysis-phase-steps .ant-steps-item-icon {
          transition: all 0.3s ease !important;
        }
        .analysis-phase-steps .ant-steps-item-wait .ant-steps-item-icon {
          opacity: 0.5;
          transition: opacity 0.3s ease;
        }
        .analysis-phase-steps .ant-steps-item-process .ant-steps-item-icon {
          animation: agentBreath 2s ease-in-out infinite;
        }
      `}</style>
    </div>
  );
};

export default StockAnalysisPage;
