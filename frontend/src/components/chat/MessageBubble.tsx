/** MessageBubble — 单条消息气泡 */

import React, { useState } from "react";
import { Typography, Spin } from "antd";
import { LoadingOutlined } from "@ant-design/icons";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { ChatMessageType } from "../../domain/types";
import ThinkingChain from "./ThinkingChain";

const { Text } = Typography;

interface Props {
  message: ChatMessageType;
  isStreaming?: boolean;
}

/** 推理思考过程 — 独立区块，可折叠 */
const ReasoningBox: React.FC<{ text: string; streaming?: boolean }> = ({ text, streaming }) => {
  const [expanded, setExpanded] = useState(false);

  if (!text) return null;

  // 默认行为：流式中展开，完成后折叠（除非用户主动展开）
  const showCollapsed = !streaming && text.length > 100 && !expanded;

  if (showCollapsed) {
    const preview = text.length > 80 ? text.slice(0, 80) + "..." : text;
    return (
      <div
        onClick={() => setExpanded(true)}
        style={{
          padding: "10px 16px",
          background: "#faf5ff",
          borderRadius: 8,
          border: "1px solid #e9d5ff",
          cursor: "pointer",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 4 }}>
          {streaming && <LoadingOutlined style={{ fontSize: 13, color: "#7c3aed" }} />}
          <span style={{ fontSize: 14, color: "#7c3aed", fontWeight: 600 }}>思考过程</span>
          <span style={{ fontSize: 12, color: "#a78bfa" }}>&#9662; 展开</span>
        </div>
        <Text style={{ fontSize: 13, color: "#7c3aed", opacity: 0.7 }}>{preview}</Text>
      </div>
    );
  }

  return (
    <div
      style={{
        padding: "12px 16px",
        background: "#faf5ff",
        borderRadius: 8,
        border: "1px solid #e9d5ff",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          {streaming && <LoadingOutlined style={{ fontSize: 13, color: "#7c3aed" }} />}
          <span style={{ fontSize: 14, color: "#7c3aed", fontWeight: 600 }}>
            {streaming ? "思考中..." : "思考过程"}
          </span>
        </div>
        {!streaming && text.length > 100 && (
          <span
            onClick={() => setExpanded(false)}
            style={{ fontSize: 12, color: "#a78bfa", cursor: "pointer" }}
          >
            &#9652; 折叠
          </span>
        )}
      </div>
      <div
        style={{
          fontSize: 13,
          lineHeight: 1.8,
          color: "#6b21a8",
          maxHeight: streaming ? 160 : 300,
          overflowY: "auto",
        }}
      >
        {text}
      </div>
    </div>
  );
};

const MessageBubble: React.FC<Props> = ({ message, isStreaming }) => {
  // 用户消息：右对齐
  if (message.role === "user") {
    return (
      <div style={{ display: "flex", justifyContent: "flex-end" }}>
        <div
          style={{
            background: "#533afd",
            color: "#fff",
            padding: "10px 16px",
            borderRadius: "16px 16px 4px 16px",
            maxWidth: "70%",
            fontSize: 14,
            lineHeight: 1.6,
            wordBreak: "break-word",
          }}
        >
          {message.content}
        </div>
      </div>
    );
  }

  // AI 消息：拆分为独立区块
  const isThinkingDone = !isStreaming && !!message.thinking_steps && message.thinking_steps.length > 0
    ? true
    : undefined;

  const hasThinkingSteps = message.thinking_steps && message.thinking_steps.length > 0;
  const hasReasoning = message.reasoning || (isStreaming && !message.content);
  const hasContent = !!message.content;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      {/* 区块1：思维链步骤（独立卡片） */}
      {hasThinkingSteps && (
        <ThinkingChain
          steps={message.thinking_steps!}
          completed={isThinkingDone}
        />
      )}

      {/* 区块2：推理思考过程（独立卡片） */}
      {hasReasoning && (
        <ReasoningBox
          text={message.reasoning || ""}
          streaming={isStreaming && !message.content}
        />
      )}

      {/* 区块3：正文结果（独立卡片） */}
      {hasContent ? (
        <div
          style={{
            background: "#ffffff",
            border: "1px solid #e5edf5",
            borderRadius: 8,
            padding: 24,
            boxShadow: "rgba(23,23,23,0.06) 0px 3px 6px",
          }}
        >
          <div className="markdown-body">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
          </div>

          {/* 流式进行中提示 */}
          {isStreaming && (
            <div
              style={{
                marginTop: 16,
                paddingTop: 12,
                borderTop: "1px solid #e5edf5",
              }}
            >
              <Text
                className="streaming-pulse"
                style={{ fontSize: 12, color: "#533afd" }}
              >
                分析进行中...
              </Text>
            </div>
          )}
        </div>
      ) : isStreaming && !message.reasoning ? (
        <div
          style={{
            background: "#ffffff",
            border: "1px solid #e5edf5",
            borderRadius: 8,
            padding: 24,
            boxShadow: "rgba(23,23,23,0.06) 0px 3px 6px",
            textAlign: "center",
          }}
        >
          <Spin
            indicator={
              <LoadingOutlined style={{ color: "#533afd", fontSize: 24 }} spin />
            }
          />
        </div>
      ) : null}
    </div>
  );
};

export default MessageBubble;
