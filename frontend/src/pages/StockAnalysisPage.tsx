/** StockAnalysisPage -- 个股分析主页面（含可视化+历史+快速模式） */

import React, { useCallback, useEffect, useRef, useState } from "react";
import { Button, Typography, Card, Steps, Spin, Alert, Space, Divider, Badge, Tag } from "antd";
import {
  PlayCircleOutlined,
  RedoOutlined,
  StockOutlined,
  HistoryOutlined,
  SwapOutlined,
  DatabaseOutlined,
} from "@ant-design/icons";
import StockSearchInput from "../components/stock-analysis/StockSearchInput";
import AnalysisModeSelector from "../components/stock-analysis/AnalysisModeSelector";
import AgentProgressPanel from "../components/stock-analysis/AgentProgressPanel";
import AgentReportCard from "../components/stock-analysis/AgentReportCard";
import DebateTimeline from "../components/stock-analysis/DebateTimeline";
import DecisionCard from "../components/stock-analysis/DecisionCard";
import AnalysisHistoryList from "../components/stock-analysis/AnalysisHistoryList";
import AnalysisComparison from "../components/stock-analysis/AnalysisComparison";
import { useStockAnalysisStore } from "../store/stockAnalysisStore";
import * as stockAnalysisService from "../services/stockAnalysisService";
import { stockDataService } from "../services/stockDataService";
import {
  ANALYSIS_PHASE_LABELS,
} from "../domain/constants";
import { AnalysisMode } from "../domain/types";
import type { StockSSEEvent, AgentStatusEvent, DebateEvent, DecisionEvent, AgentReportEvent } from "../domain/types";

const { Text, Title, Paragraph } = Typography;

/** 分析阶段顺序 */
const PHASE_ORDER = ["analysts", "debate", "trader", "risk"];

const StockAnalysisPage: React.FC = () => {
  const store = useStockAnalysisStore();
  const abortRef = useRef<AbortController | null>(null);
  const [comparisonOpen, setComparisonOpen] = useState(false);
  const [historyItems] = useState<any[]>([]);

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

  /** 发起分析 */
  const handleStart = useCallback(async () => {
    if (!store.stockCode || !store.stockName) return;

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    store.startAnalysis();

    try {
      const session = await stockAnalysisService.createStockAnalysisSession({
        stock_code: store.stockCode,
        stock_name: store.stockName,
        analysis_mode: store.analysisMode,
      });

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
            case "agent_status":
              st.updateAgentStatus(event.data as AgentStatusEvent);
              break;
            case "agent_report":
              {
                const report = event.data as AgentReportEvent;
                st.addAgentReport(report.agent, report.summary);
              }
              break;
            case "debate":
              st.addDebate(event.data as DebateEvent);
              break;
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
    abortRef.current?.abort();
    useStockAnalysisStore.setState({ analysisState: "done" });
  }, []);

  const handleReset = useCallback(() => {
    store.reset();
  }, [store]);

  const currentPhaseIndex = PHASE_ORDER.indexOf(store.currentPhase);

  // === Idle 态 ===
  if (isIdle) {
    return (
      <div
        style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          padding: "0 32px",
          height: "100vh",
        }}
      >
        <h1
          style={{
            fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
            fontWeight: 300,
            fontSize: 30,
            color: "#061b31",
            letterSpacing: "-0.6px",
            fontFeatureSettings: "'ss01' on",
            margin: 0,
            marginBottom: 12,
            textAlign: "center",
          }}
        >
          <StockOutlined style={{ color: "#533afd", marginRight: 8 }} />
          个股深度分析
        </h1>
        <Paragraph
          style={{
            fontSize: 15,
            color: "#64748d",
            textAlign: "center",
            marginBottom: 40,
            fontFeatureSettings: "'ss01' on",
          }}
        >
          多 Agent 协作分析，从技术面、基本面、新闻面等多维度评估个股
        </Paragraph>

        <div style={{ marginBottom: 28 }}>
          <Text style={{ fontSize: 13, color: "#273951", display: "block", marginBottom: 8, fontFeatureSettings: "'ss01' on" }}>
            选择分析标的
          </Text>
          <StockSearchInput />
        </div>

        <div style={{ marginBottom: 36 }}>
          <Text style={{ fontSize: 13, color: "#273951", display: "block", marginBottom: 8, fontFeatureSettings: "'ss01' on" }}>
            分析模式
          </Text>
          <AnalysisModeSelector />
        </div>

        <Button
          type="primary"
          size="large"
          disabled={!store.stockCode || !store.stockName || store.validationLoading}
          onClick={handleStart}
          icon={<PlayCircleOutlined />}
          style={{ borderRadius: 6, fontWeight: 400, height: 44, padding: "0 28px", fontSize: 15 }}
        >
          开始分析
        </Button>

        <div style={{ position: "absolute", bottom: 24 }}>
          <Text style={{ fontSize: 11, color: "#d0d5dd", fontFeatureSettings: "'ss01' on" }}>
            本工具仅供投研参考，不构成任何投资建议
          </Text>
        </div>
      </div>
    );
  }

  // === Running / Done / Error 态 ===
  const phasesToShow = isQuickMode ? ["analysts"] : PHASE_ORDER;

  return (
    <div style={{ height: "100vh", display: "flex", flexDirection: "column" }}>
      {/* 顶部标题栏 */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          padding: "16px 24px",
          borderBottom: "1px solid #e5edf5",
          flexShrink: 0,
        }}
      >
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
              <Text style={{ fontSize: 13, color: "#64748d", fontFeatureSettings: "'ss01' on" }}>
                {store.title}
              </Text>
            )}
          </div>
          {store.dataSource && (
            <Tag color="blue" icon={<DatabaseOutlined />}>
              数据源: {store.dataSource}
            </Tag>
          )}
        </div>
        <Space>
          {isRunning && (
            <Button onClick={handleStop} style={{ borderRadius: 4 }}>
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
      {isRunning && (
        <div style={{ padding: "8px 24px", borderBottom: "1px solid #e5edf5", flexShrink: 0 }}>
          <Steps
            current={Math.min(currentPhaseIndex, phasesToShow.length - 1)}
            size="small"
            items={phasesToShow.map((phase) => ({
              title: (
                <span style={{ fontSize: 12, fontFeatureSettings: "'ss01' on", color: store.currentPhase === phase ? "#533afd" : "#64748d" }}>
                  {ANALYSIS_PHASE_LABELS[phase] || phase}
                </span>
              ),
            }))}
          />
        </div>
      )}

      {/* 主内容区：左面板 + 右面板 */}
      <div style={{ flex: 1, overflow: "hidden", display: "flex" }}>
        {/* 左面板：Agent 进度（仅 full 模式或运行中显示） */}
        {(isRunning && !isQuickMode) && (
          <div
            style={{
              width: 240,
              flexShrink: 0,
              borderRight: "1px solid #e5edf5",
              overflowY: "auto",
              padding: "8px 12px",
              background: "#fafbfc",
            }}
          >
            <Text style={{ fontSize: 12, color: "#64748d", display: "block", marginBottom: 8, fontFeatureSettings: "'ss01' on" }}>
              分析进度
            </Text>
            <AgentProgressPanel />
          </div>
        )}

        {/* 右面板：分析内容 */}
        <div style={{ flex: 1, overflowY: "auto", padding: "20px 24px" }}>
          {/* 加载中 */}
          {isRunning && Object.keys(store.agentStatuses).length === 0 && (
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: "60px 0" }}>
              <Spin size="large" />
              <Text style={{ fontSize: 13, color: "#64748d", marginTop: 16, fontFeatureSettings: "'ss01' on" }}>
                正在初始化分析流程...
              </Text>
            </div>
          )}

          {/* Agent 报告卡片 */}
          {Object.keys(store.agentReports).length > 0 && (
            <div style={{ marginBottom: 16 }}>
              {Object.entries(store.agentReports).map(([agent, summary]) => {
                // 快速模式只显示技术面+基本面
                if (isQuickMode && agent !== "market_analyst" && agent !== "fundamentals_analyst") return null;
                return (
                  <AgentReportCard
                    key={agent}
                    agent={agent}
                    summary={summary}
                    isRunning={store.agentStatuses[agent] === "running"}
                  />
                );
              })}
            </div>
          )}

          {/* 辩论时间线（仅 full 模式） */}
          {!isQuickMode && store.debates.length > 0 && (
            <div style={{ marginBottom: 16 }}>
              <DebateTimeline debates={store.debates} />
            </div>
          )}

          {/* 决策卡片 */}
          {store.decision && (
            <div style={{ marginBottom: 16 }}>
              <DecisionCard decision={store.decision} />
            </div>
          )}

          {/* 分析内容文本（兜底展示） */}
          {store.content && !store.decision && (
            <Card style={{ marginBottom: 16, borderRadius: 6, border: "1px solid #e5edf5" }} bodyStyle={{ padding: "16px 20px" }}>
              <div style={{ fontSize: 14, color: "#061b31", lineHeight: 1.8, whiteSpace: "pre-wrap", fontFeatureSettings: "'ss01' on" }}>
                {store.content}
                {isRunning && (
                  <span style={{ display: "inline-block", width: 2, height: 16, background: "#533afd", marginLeft: 1, animation: "blink 1s infinite", verticalAlign: "middle" }} />
                )}
              </div>
            </Card>
          )}

          {/* 错误信息 */}
          {isError && (
            <Alert type="error" message="分析失败" description={store.error} showIcon style={{ marginBottom: 16, borderRadius: 6 }} />
          )}

          {/* 历史分析区域（完成或空闲时显示） */}
          {(isDone || isError) && store.stockCode && (
            <div style={{ marginTop: 16 }}>
              <Divider style={{ margin: "16px 0 12px" }} />
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <HistoryOutlined style={{ color: "#533afd" }} />
                  <Text style={{ fontSize: 14, fontWeight: 400, color: "#061b31", fontFeatureSettings: "'ss01' on" }}>
                    历史分析
                  </Text>
                </div>
                {historyItems.length >= 2 && (
                  <Button
                    size="small"
                    icon={<SwapOutlined />}
                    onClick={() => setComparisonOpen(true)}
                    style={{ borderRadius: 4 }}
                  >
                    对比分析
                  </Button>
                )}
              </div>
              <AnalysisHistoryList
                stockCode={store.stockCode}
                onRefresh={store.historyRefreshKey}
              />
              <AnalysisComparison
                open={comparisonOpen}
                onClose={() => setComparisonOpen(false)}
                items={historyItems}
              />
            </div>
          )}

          {/* 底部免责声明 */}
          <div style={{ textAlign: "center", padding: "24px 0 16px", borderTop: "1px solid #f6f9fc", marginTop: 8 }}>
            <Text style={{ fontSize: 11, color: "#d0d5dd", fontFeatureSettings: "'ss01' on" }}>
              本工具仅供投研参考，不构成任何投资建议
            </Text>
          </div>
        </div>
      </div>

      {/* 光标闪烁动画 */}
      <style>{`
        @keyframes blink {
          0%, 100% { opacity: 1; }
          50% { opacity: 0; }
        }
      `}</style>
    </div>
  );
};

export default StockAnalysisPage;
