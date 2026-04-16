/** AnalysisPage — AI 事件分析主页面 */

import React, { useState } from "react";
import { Typography, Divider } from "antd";
import { ExperimentOutlined } from "@ant-design/icons";
import { useAnalysis } from "../application/useAnalysis";
import EventTypeSelector from "../components/analysis/EventTypeSelector";
import AnalysisInput from "../components/analysis/AnalysisInput";
import AnalysisResult from "../components/analysis/AnalysisResult";
import AnalysisStatusBar from "../components/analysis/AnalysisStatusBar";
import { EventType } from "../domain/types";
import { EXAMPLE_PROMPTS } from "../domain/constants";

const { Title, Paragraph, Text } = Typography;

const AnalysisPage: React.FC = () => {
  const [eventType, setEventType] = useState<EventType>(EventType.GEO_POLITICAL);
  const { status, result, analyze, stop, isStreaming } = useAnalysis();

  const handleSubmit = (question: string) => {
    analyze(eventType, question);
  };

  const handleExampleClick = (example: (typeof EXAMPLE_PROMPTS)[number]) => {
    setEventType(example.eventType);
    analyze(example.eventType, example.question);
  };

  return (
    <div style={{ maxWidth: 880, margin: "0 auto", padding: "32px 24px 48px" }}>
      {/* 页面标题区域 */}
      <div style={{ marginBottom: 28 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 8 }}>
          <div
            style={{
              width: 40,
              height: 40,
              borderRadius: 12,
              background: "linear-gradient(135deg, #07C160, #0cce6b)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "#fff",
              fontSize: 20,
            }}
          >
            <ExperimentOutlined />
          </div>
          <div>
            <Title level={3} style={{ margin: 0, color: "#101828" }}>
              AI 事件分析
            </Title>
          </div>
        </div>
        <Paragraph style={{ color: "#667085", margin: 0, fontSize: 14, paddingLeft: 52 }}>
          描述一个市场事件，AI 将从产业链、行业、个股等维度进行深度分析
        </Paragraph>
      </div>

      {/* 全局状态条 */}
      <AnalysisStatusBar />

      {/* 输入区域 */}
      <div
        style={{
          background: "#ffffff",
          borderRadius: 16,
          padding: 24,
          boxShadow: "0 1px 3px rgba(16, 24, 40, 0.06), 0 1px 2px rgba(16, 24, 40, 0.04)",
          marginBottom: 20,
        }}
      >
        <EventTypeSelector
          value={eventType}
          onChange={setEventType}
          disabled={isStreaming}
        />
        <AnalysisInput
          eventType={eventType}
          disabled={isStreaming}
          onSubmit={handleSubmit}
        />
        {isStreaming && (
          <a
            onClick={stop}
            style={{
              marginLeft: 8,
              fontSize: 13,
              color: "#f5222d",
              marginTop: 8,
              display: "inline-block",
            }}
          >
            停止分析
          </a>
        )}
      </div>

      {/* 分析结果 */}
      <AnalysisResult />

      {/* 示例问题 — 仅空闲时展示 */}
      {status === "idle" && !result && (
        <div style={{ marginTop: 32 }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              marginBottom: 16,
            }}
          >
            <Divider
              style={{ flex: 1, margin: 0, borderColor: "#eaecf0" }}
            />
            <Text style={{ color: "#98a2b3", fontSize: 13, whiteSpace: "nowrap" }}>
              不知道怎么问？试试这些示例
            </Text>
            <Divider
              style={{ flex: 1, margin: 0, borderColor: "#eaecf0" }}
            />
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {EXAMPLE_PROMPTS.map((ex, i) => (
              <div
                key={i}
                className="example-card"
                onClick={() => handleExampleClick(ex)}
                style={{
                  background: "#ffffff",
                  borderRadius: 12,
                  padding: "14px 18px",
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  gap: 12,
                }}
              >
                <div
                  style={{
                    width: 28,
                    height: 28,
                    borderRadius: 8,
                    background: "#f0fdf4",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    color: "#07C160",
                    fontSize: 14,
                    fontWeight: 600,
                    flexShrink: 0,
                  }}
                >
                  {i + 1}
                </div>
                <Text style={{ color: "#344054", fontSize: 14 }}>{ex.question}</Text>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default AnalysisPage;
