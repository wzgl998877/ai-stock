/** AnalysisPage — AI 事件分析主页面（Stripe 对话式布局） */

import React, { useState } from "react";
import { useAnalysis } from "../application/useAnalysis";
import AnalysisResult from "../components/analysis/AnalysisResult";
import AnalysisInput from "../components/analysis/AnalysisInput";
import EventTypeSelector from "../components/analysis/EventTypeSelector";
import { EventType } from "../domain/types";

const AnalysisPage: React.FC = () => {
  const [eventType, setEventType] = useState<EventType | null>(null);
  const { status, result, analyze, stop, isStreaming } = useAnalysis();

  const handleSubmit = (question: string) => {
    analyze(eventType ?? EventType.GEO_POLITICAL, question);
  };

  const isIdle = status === "idle" && !result;

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100vh",
        overflow: "hidden",
      }}
    >
      {/* 可滚动内容区域 */}
      <div
        style={{
          flex: 1,
          overflowY: "auto",
          display: "flex",
          flexDirection: "column",
        }}
      >
        {isIdle ? (
          /* 空闲态：居中欢迎 */
          <div
            style={{
              flex: 1,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              padding: "0 32px",
            }}
          >
            {/* 标题 */}
            <h1
              style={{
                fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
                fontWeight: 300,
                fontSize: 30,
                color: "#061b31",
                letterSpacing: "-0.6px",
                fontFeatureSettings: "'ss01' on",
                margin: 0,
                marginBottom: 40,
                textAlign: "center",
              }}
            >
              你好，我是{' '}
              <span style={{ color: "#533afd", fontWeight: 400 }}>
                AI 投研助手
              </span>
              ，有什么能帮你的吗？
            </h1>

            {/* 输入框 */}
            <div style={{ width: 780 }}>
              <AnalysisInput
                eventType={eventType}
                disabled={isStreaming}
                onSubmit={handleSubmit}
              />
              {/* 事件类型标签在输入框下方 */}
              <EventTypeSelector
                value={eventType}
                onChange={setEventType}
                disabled={isStreaming}
              />
            </div>
          </div>
        ) : (
          /* 分析态：结果展示 */
          <div
            style={{
              maxWidth: 860,
              width: "100%",
              margin: "0 auto",
              padding: "24px 24px 100px",
            }}
          >
            <AnalysisResult onStop={stop} />
          </div>
        )}
      </div>

      {/* 分析态：底部固定输入栏 */}
      {!isIdle && (
        <div
          style={{
            flexShrink: 0,
            borderTop: "1px solid #e5edf5",
            padding: "16px 32px 20px",
            background: "#ffffff",
            display: "flex",
            justifyContent: "center",
          }}
        >
          <div style={{ width: 780 }}>
            <AnalysisInput
              eventType={eventType}
              disabled={isStreaming}
              onSubmit={handleSubmit}
            />
            <EventTypeSelector
              value={eventType}
              onChange={setEventType}
              disabled={isStreaming}
            />
          </div>
        </div>
      )}
    </div>
  );
};

export default AnalysisPage;
