/** AnalysisPage — AI 事件分析主页面 */

import React, { useState } from "react";
import { Typography, Divider, Card } from "antd";
import { useAnalysis } from "../application/useAnalysis";
import EventTypeSelector from "../components/analysis/EventTypeSelector";
import AnalysisInput from "../components/analysis/AnalysisInput";
import AnalysisResult from "../components/analysis/AnalysisResult";
import AnalysisStatusBar from "../components/analysis/AnalysisStatusBar";
import { EventType } from "../domain/types";
import { EXAMPLE_PROMPTS } from "../domain/constants";

const { Title, Paragraph } = Typography;

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
    <div style={{ maxWidth: 960, margin: "0 auto", padding: "24px 16px" }}>
      <Title level={2}>AI 事件分析</Title>
      <Paragraph type="secondary">
        描述一个市场事件，AI 将从产业链、行业、个股等维度进行深度分析。
      </Paragraph>

      <AnalysisStatusBar />

      <Card style={{ marginBottom: 24 }}>
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
            style={{ marginLeft: 8, fontSize: 12, color: "#ff4d4f" }}
          >
            停止分析
          </a>
        )}
      </Card>

      <AnalysisResult />

      {/* 示例问题 — 仅空闲时展示 */}
      {status === "idle" && !result && (
        <>
          <Divider>不知道怎么问？试试这些示例</Divider>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {EXAMPLE_PROMPTS.map((ex, i) => (
              <Card
                key={i}
                size="small"
                hoverable
                style={{ cursor: "pointer" }}
                onClick={() => handleExampleClick(ex)}
              >
                <Typography.Text>{ex.question}</Typography.Text>
              </Card>
            ))}
          </div>
        </>
      )}

      <Divider />
      <Paragraph type="secondary" style={{ fontSize: 12, textAlign: "center" }}>
        本工具仅供投研参考，不构成任何投资建议
      </Paragraph>
    </div>
  );
};

export default AnalysisPage;
