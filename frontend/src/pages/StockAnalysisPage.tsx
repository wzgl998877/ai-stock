/** StockAnalysisPage -- 个股分析主页面 */

import React, { useCallback, useRef } from "react";
import { Button, Typography, Card, Steps, Tag, Spin, Alert, Space, Progress } from "antd";
import {
  PlayCircleOutlined,
  RedoOutlined,
  CheckCircleFilled,
  LoadingOutlined,
  CloseCircleFilled,
  StockOutlined,
  SwapOutlined,
  DollarOutlined,
  SafetyCertificateOutlined,
} from "@ant-design/icons";
import StockSearchInput from "../components/stock-analysis/StockSearchInput";
import AnalysisModeSelector from "../components/stock-analysis/AnalysisModeSelector";
import { useStockAnalysisStore } from "../store/stockAnalysisStore";
import * as stockAnalysisService from "../services/stockAnalysisService";
import {
  AGENT_DISPLAY_NAMES,
  ANALYSIS_PHASE_LABELS,
} from "../domain/constants";
import type { StockSSEEvent, AgentStatusEvent, DebateEvent, DecisionEvent, AgentReportEvent } from "../domain/types";

const { Text, Title, Paragraph } = Typography;

/** 阶段图标映射 */
const PHASE_ICONS: Record<string, React.ReactNode> = {
  analysts: <StockOutlined />,
  debate: <SwapOutlined />,
  trader: <DollarOutlined />,
  risk: <SafetyCertificateOutlined />,
};

/** Agent 状态图标 */
const STATUS_ICON: Record<string, React.ReactNode> = {
  running: <LoadingOutlined style={{ color: "#533afd" }} spin />,
  done: <CheckCircleFilled style={{ color: "#15be53" }} />,
  failed: <CloseCircleFilled style={{ color: "#ea2261" }} />,
};

/** 分析阶段顺序 */
const PHASE_ORDER = ["analysts", "debate", "trader", "risk"];

const StockAnalysisPage: React.FC = () => {
  const store = useStockAnalysisStore();
  const abortRef = useRef<AbortController | null>(null);

  const isIdle = store.analysisState === "idle";
  const isRunning = store.analysisState === "running";
  const isDone = store.analysisState === "done";
  const isError = store.analysisState === "error";

  /** 发起分析 */
  const handleStart = useCallback(async () => {
    if (!store.stockCode || !store.stockName) return;

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    store.startAnalysis();

    try {
      // 1. 创建会话
      const session = await stockAnalysisService.createStockAnalysisSession({
        stock_code: store.stockCode,
        stock_name: store.stockName,
        analysis_mode: store.analysisMode,
      });

      // 2. 流式分析
      await stockAnalysisService.streamStockAnalysis(
        session.id,
        {
          stock_code: store.stockCode,
          stock_name: store.stockName,
          analysis_mode: store.analysisMode,
          content: `请对${store.stockName}(${store.stockCode})进行${store.analysisMode === "full" ? "深度" : "快速"}分析`,
        },
        (event: StockSSEEvent) => {
          switch (event.type) {
            case "agent_status":
              store.updateAgentStatus(event.data as AgentStatusEvent);
              break;
            case "agent_report":
              {
                const report = event.data as AgentReportEvent;
                store.addAgentReport(report.agent, report.summary);
              }
              break;
            case "debate":
              store.addDebate(event.data as DebateEvent);
              break;
            case "decision":
              store.setDecision(event.data as DecisionEvent);
              break;
            case "content":
              store.appendContent(event.data as string);
              break;
            case "title":
              store.setTitle(event.data as string);
              break;
            case "summary":
              store.setSummary(event.data as string);
              break;
            case "industries":
              store.setIndustries(event.data as string[]);
              break;
            case "done":
              useStockAnalysisStore.getState().analysisState !== "done" &&
                useStockAnalysisStore.setState({ analysisState: "done" });
              break;
            case "error":
              store.setError(event.data as string);
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

  /** 停止分析 */
  const handleStop = useCallback(() => {
    abortRef.current?.abort();
    useStockAnalysisStore.setState({ analysisState: "done" });
  }, []);

  /** 重新分析 */
  const handleReset = useCallback(() => {
    store.reset();
  }, [store]);

  /** 计算当前阶段进度 */
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
          <Text
            style={{
              fontSize: 13,
              color: "#273951",
              display: "block",
              marginBottom: 8,
              fontFeatureSettings: "'ss01' on",
            }}
          >
            选择分析标的
          </Text>
          <StockSearchInput />
        </div>

        <div style={{ marginBottom: 36 }}>
          <Text
            style={{
              fontSize: 13,
              color: "#273951",
              display: "block",
              marginBottom: 8,
              fontFeatureSettings: "'ss01' on",
            }}
          >
            分析模式
          </Text>
          <AnalysisModeSelector />
        </div>

        <Button
          type="primary"
          size="large"
          disabled={!store.validationValid}
          onClick={handleStart}
          icon={<PlayCircleOutlined />}
          style={{
            borderRadius: 6,
            fontWeight: 400,
            height: 44,
            padding: "0 28px",
            fontSize: 15,
          }}
        >
          开始分析
        </Button>

        {/* 底部免责声明 */}
        <div style={{ position: "absolute", bottom: 24 }}>
          <Text
            style={{
              fontSize: 11,
              color: "#d0d5dd",
              fontFeatureSettings: "'ss01' on",
            }}
          >
            本工具仅供投研参考，不构成任何投资建议
          </Text>
        </div>
      </div>
    );
  }

  // === Running / Done / Error 态 ===
  return (
    <div
      style={{
        height: "100vh",
        overflow: "auto",
        padding: "24px 32px",
      }}
    >
      {/* 顶部标题栏 */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 24,
        }}
      >
        <div>
          <Title
            level={4}
            style={{
              margin: 0,
              fontWeight: 400,
              color: "#061b31",
              fontFeatureSettings: "'ss01' on",
            }}
          >
            {store.stockName}({store.stockCode}) 分析
          </Title>
          {store.title && (
            <Text
              style={{
                fontSize: 13,
                color: "#64748d",
                fontFeatureSettings: "'ss01' on",
              }}
            >
              {store.title}
            </Text>
          )}
        </div>
        <Space>
          {isRunning && (
            <Button onClick={handleStop} style={{ borderRadius: 4 }}>
              停止分析
            </Button>
          )}
          {(isDone || isError) && (
            <Button
              icon={<RedoOutlined />}
              onClick={handleReset}
              style={{ borderRadius: 4 }}
            >
              重新分析
            </Button>
          )}
        </Space>
      </div>

      {/* 阶段进度条 */}
      {isRunning && (
        <Card
          size="small"
          style={{
            marginBottom: 20,
            borderRadius: 6,
            border: "1px solid #e5edf5",
          }}
          bodyStyle={{ padding: "12px 20px" }}
        >
          <Steps
            current={currentPhaseIndex}
            size="small"
            items={PHASE_ORDER.map((phase) => ({
              title: (
                <span
                  style={{
                    fontSize: 12,
                    fontFeatureSettings: "'ss01' on",
                    color:
                      store.currentPhase === phase ? "#533afd" : "#64748d",
                  }}
                >
                  {ANALYSIS_PHASE_LABELS[phase] || phase}
                </span>
              ),
              icon: PHASE_ICONS[phase],
            }))}
          />
        </Card>
      )}

      {/* Agent 状态面板 */}
      {isRunning && (
        <Card
          title={
            <Text
              style={{
                fontSize: 13,
                fontWeight: 400,
                color: "#273951",
                fontFeatureSettings: "'ss01' on",
              }}
            >
              分析进度
            </Text>
          }
          size="small"
          style={{
            marginBottom: 20,
            borderRadius: 6,
            border: "1px solid #e5edf5",
          }}
          bodyStyle={{ padding: "12px 16px" }}
        >
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))",
              gap: 8,
            }}
          >
            {Object.entries(store.agentStatuses).map(([agent, status]) => (
              <div
                key={agent}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  padding: "6px 10px",
                  borderRadius: 4,
                  background:
                    status === "running"
                      ? "#f0efff"
                      : status === "done"
                      ? "#f0fdf4"
                      : status === "failed"
                      ? "#fff1f2"
                      : "#f8fafc",
                  border: `1px solid ${
                    status === "running"
                      ? "#d6d9fc"
                      : status === "done"
                      ? "#bbf7d0"
                      : status === "failed"
                      ? "#fecdd3"
                      : "#e5edf5"
                  }`,
                }}
              >
                {STATUS_ICON[status] || (
                  <div
                    style={{
                      width: 16,
                      height: 16,
                      borderRadius: "50%",
                      background: "#e5edf5",
                    }}
                  />
                )}
                <Text
                  style={{
                    fontSize: 12,
                    color: status === "running" ? "#533afd" : "#061b31",
                    fontFeatureSettings: "'ss01' on",
                  }}
                >
                  {AGENT_DISPLAY_NAMES[agent] || agent}
                </Text>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* 分析结果内容 */}
      {(store.content || isDone) && (
        <Card
          style={{
            marginBottom: 20,
            borderRadius: 6,
            border: "1px solid #e5edf5",
          }}
          bodyStyle={{ padding: "20px 24px" }}
        >
          {store.summary && (
            <div style={{ marginBottom: 16 }}>
              <Text
                style={{
                  fontSize: 13,
                  color: "#273951",
                  fontWeight: 400,
                  display: "block",
                  marginBottom: 6,
                  fontFeatureSettings: "'ss01' on",
                }}
              >
                摘要
              </Text>
              <Paragraph
                style={{
                  fontSize: 14,
                  color: "#061b31",
                  margin: 0,
                  lineHeight: 1.7,
                  fontFeatureSettings: "'ss01' on",
                }}
              >
                {store.summary}
              </Paragraph>
            </div>
          )}

          {store.industries.length > 0 && (
            <div style={{ marginBottom: 16 }}>
              <Text
                style={{
                  fontSize: 13,
                  color: "#273951",
                  fontWeight: 400,
                  display: "block",
                  marginBottom: 6,
                  fontFeatureSettings: "'ss01' on",
                }}
              >
                关联行业
              </Text>
              <Space wrap>
                {store.industries.map((ind) => (
                  <Tag
                    key={ind}
                    style={{
                      borderRadius: 4,
                      background: "#f0efff",
                      color: "#533afd",
                      border: "1px solid #d6d9fc",
                      fontSize: 12,
                    }}
                  >
                    {ind}
                  </Tag>
                ))}
              </Space>
            </div>
          )}

          {store.content && (
            <div>
              <Text
                style={{
                  fontSize: 13,
                  color: "#273951",
                  fontWeight: 400,
                  display: "block",
                  marginBottom: 6,
                  fontFeatureSettings: "'ss01' on",
                }}
              >
                分析报告
              </Text>
              <div
                style={{
                  fontSize: 14,
                  color: "#061b31",
                  lineHeight: 1.8,
                  whiteSpace: "pre-wrap",
                  fontFeatureSettings: "'ss01' on",
                }}
              >
                {store.content}
                {isRunning && (
                  <span
                    style={{
                      display: "inline-block",
                      width: 2,
                      height: 16,
                      background: "#533afd",
                      marginLeft: 1,
                      animation: "blink 1s infinite",
                      verticalAlign: "middle",
                    }}
                  />
                )}
              </div>
            </div>
          )}
        </Card>
      )}

      {/* Agent 报告摘要 */}
      {Object.keys(store.agentReports).length > 0 && (
        <Card
          title={
            <Text
              style={{
                fontSize: 13,
                fontWeight: 400,
                color: "#273951",
                fontFeatureSettings: "'ss01' on",
              }}
            >
              各分析师摘要
            </Text>
          }
          style={{
            marginBottom: 20,
            borderRadius: 6,
            border: "1px solid #e5edf5",
          }}
          bodyStyle={{ padding: "12px 16px" }}
        >
          {Object.entries(store.agentReports).map(([agent, summary]) => (
            <div
              key={agent}
              style={{
                marginBottom: 12,
                paddingBottom: 12,
                borderBottom: "1px solid #f6f9fc",
              }}
            >
              <Text
                style={{
                  fontSize: 12,
                  color: "#533afd",
                  fontWeight: 400,
                  display: "block",
                  marginBottom: 4,
                  fontFeatureSettings: "'ss01' on",
                }}
              >
                {AGENT_DISPLAY_NAMES[agent] || agent}
              </Text>
              <Text
                style={{
                  fontSize: 13,
                  color: "#273951",
                  lineHeight: 1.6,
                  fontFeatureSettings: "'ss01' on",
                }}
              >
                {summary}
              </Text>
            </div>
          ))}
        </Card>
      )}

      {/* 辩论记录 */}
      {store.debates.length > 0 && (
        <Card
          title={
            <Text
              style={{
                fontSize: 13,
                fontWeight: 400,
                color: "#273951",
                fontFeatureSettings: "'ss01' on",
              }}
            >
              投资辩论
            </Text>
          }
          style={{
            marginBottom: 20,
            borderRadius: 6,
            border: "1px solid #e5edf5",
          }}
          bodyStyle={{ padding: "12px 16px" }}
        >
          {store.debates.map((debate, idx) => (
            <div
              key={idx}
              style={{
                marginBottom: 10,
                paddingBottom: 10,
                borderBottom: "1px solid #f6f9fc",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 4 }}>
                <Tag
                  style={{
                    fontSize: 11,
                    borderRadius: 4,
                    background:
                      debate.speaker === "bull_researcher"
                        ? "#f0fdf4"
                        : debate.speaker === "bear_researcher"
                        ? "#fff1f2"
                        : "#f0efff",
                    color:
                      debate.speaker === "bull_researcher"
                        ? "#108c3d"
                        : debate.speaker === "bear_researcher"
                        ? "#ea2261"
                        : "#533afd",
                    border: `1px solid ${
                      debate.speaker === "bull_researcher"
                        ? "#bbf7d0"
                        : debate.speaker === "bear_researcher"
                        ? "#fecdd3"
                        : "#d6d9fc"
                    }`,
                  }}
                >
                  {AGENT_DISPLAY_NAMES[debate.speaker] || debate.speaker}
                </Tag>
                <Text style={{ fontSize: 11, color: "#94a3b8" }}>
                  第{debate.round}轮
                </Text>
              </div>
              <Text
                style={{
                  fontSize: 13,
                  color: "#273951",
                  lineHeight: 1.6,
                  fontFeatureSettings: "'ss01' on",
                }}
              >
                {debate.content}
              </Text>
            </div>
          ))}
        </Card>
      )}

      {/* 交易决策 */}
      {store.decision && (
        <Card
          title={
            <Text
              style={{
                fontSize: 13,
                fontWeight: 400,
                color: "#273951",
                fontFeatureSettings: "'ss01' on",
              }}
            >
              交易决策
            </Text>
          }
          style={{
            marginBottom: 20,
            borderRadius: 6,
            border: "1px solid #e5edf5",
          }}
          bodyStyle={{ padding: "16px 20px" }}
        >
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(4, 1fr)",
              gap: 16,
              marginBottom: 12,
            }}
          >
            <div>
              <Text
                style={{
                  fontSize: 11,
                  color: "#94a3b8",
                  display: "block",
                  marginBottom: 4,
                  fontFeatureSettings: "'ss01' on",
                }}
              >
                操作建议
              </Text>
              <Tag
                color={
                  store.decision.action === "buy"
                    ? "green"
                    : store.decision.action === "sell"
                    ? "red"
                    : "default"
                }
                style={{ fontSize: 14, borderRadius: 4, padding: "2px 12px" }}
              >
                {store.decision.action === "buy"
                  ? "买入"
                  : store.decision.action === "sell"
                  ? "卖出"
                  : store.decision.action === "hold"
                  ? "持有"
                  : store.decision.action}
              </Tag>
            </div>
            <div>
              <Text
                style={{
                  fontSize: 11,
                  color: "#94a3b8",
                  display: "block",
                  marginBottom: 4,
                  fontFeatureSettings: "'ss01' on",
                }}
              >
                目标价格
              </Text>
              <Text
                style={{
                  fontSize: 16,
                  color: "#061b31",
                  fontWeight: 400,
                  fontFeatureSettings: "'tnum'",
                }}
              >
                {store.decision.target_price?.toFixed(2)}
              </Text>
            </div>
            <div>
              <Text
                style={{
                  fontSize: 11,
                  color: "#94a3b8",
                  display: "block",
                  marginBottom: 4,
                  fontFeatureSettings: "'ss01' on",
                }}
              >
                信心指数
              </Text>
              <Progress
                percent={Math.round(store.decision.confidence * 100)}
                size="small"
                strokeColor="#533afd"
                style={{ fontSize: 12 }}
              />
            </div>
            <div>
              <Text
                style={{
                  fontSize: 11,
                  color: "#94a3b8",
                  display: "block",
                  marginBottom: 4,
                  fontFeatureSettings: "'ss01' on",
                }}
              >
                风险评分
              </Text>
              <Progress
                percent={Math.round(store.decision.risk_score * 100)}
                size="small"
                strokeColor={
                  store.decision.risk_score > 0.7
                    ? "#ea2261"
                    : store.decision.risk_score > 0.4
                    ? "#9b6829"
                    : "#15be53"
                }
                style={{ fontSize: 12 }}
              />
            </div>
          </div>
          {store.decision.reasoning && (
            <div>
              <Text
                style={{
                  fontSize: 11,
                  color: "#94a3b8",
                  display: "block",
                  marginBottom: 4,
                  fontFeatureSettings: "'ss01' on",
                }}
              >
                决策依据
              </Text>
              <Paragraph
                style={{
                  fontSize: 13,
                  color: "#273951",
                  lineHeight: 1.6,
                  margin: 0,
                  fontFeatureSettings: "'ss01' on",
                }}
              >
                {store.decision.reasoning}
              </Paragraph>
            </div>
          )}
        </Card>
      )}

      {/* 错误信息 */}
      {isError && (
        <Alert
          type="error"
          message="分析失败"
          description={store.error}
          showIcon
          style={{ marginBottom: 20, borderRadius: 6 }}
        />
      )}

      {/* 加载中遮罩 */}
      {isRunning && !store.content && Object.keys(store.agentStatuses).length === 0 && (
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            padding: "60px 0",
          }}
        >
          <Spin size="large" />
          <Text
            style={{
              fontSize: 13,
              color: "#64748d",
              marginTop: 16,
              fontFeatureSettings: "'ss01' on",
            }}
          >
            正在初始化分析流程...
          </Text>
        </div>
      )}

      {/* 底部免责声明 */}
      <div
        style={{
          textAlign: "center",
          padding: "24px 0 16px",
          borderTop: "1px solid #f6f9fc",
          marginTop: 8,
        }}
      >
        <Text
          style={{
            fontSize: 11,
            color: "#d0d5dd",
            fontFeatureSettings: "'ss01' on",
          }}
        >
          本工具仅供投研参考，不构成任何投资建议
        </Text>
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
