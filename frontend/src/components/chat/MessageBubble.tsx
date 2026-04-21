/** MessageBubble — 单条消息气泡 */

import React, { useState } from "react";
import { Typography, Spin } from "antd";
import { LoadingOutlined } from "@ant-design/icons";
import ReactMarkdown from "react-markdown";
import type { ChatMessageType } from "../../domain/types";
import ThinkingChain from "./ThinkingChain";

const { Text } = Typography;

interface Props {
  message: ChatMessageType;
  isStreaming?: boolean;
}

/** 推理思考过程 — 可折叠展示 */
const ReasoningBox: React.FC<{ text: string; streaming?: boolean }> = ({ text, streaming }) => {
  const [collapsed, setCollapsed] = useState(false);

  if (!text) return null;

  // 流式中默认展开，完成后默认折叠
  if (collapsed || (!streaming && text.length > 100)) {
    const preview = text.length > 80 ? text.slice(0, 80) + "..." : text;
    return (
      <div
        onClick={() => setCollapsed(false)}
        style={{
          marginBottom: 12,
          padding: "8px 12px",
          background: "#faf5ff",
          borderRadius: 6,
          border: "1px solid #e9d5ff",
          cursor: "pointer",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 4, marginBottom: collapsed ? 0 : 4 }}>
          <span style={{ fontSize: 12, color: "#7c3aed", fontWeight: 500 }}>思考过程</span>
          <span style={{ fontSize: 10, color: "#a78bfa" }}>&#9662; 展开</span>
        </div>
        {collapsed && (
          <Text style={{ fontSize: 12, color: "#7c3aed", opacity: 0.7 }}>{preview}</Text>
        )}
      </div>
    );
  }

  return (
    <div
      style={{
        marginBottom: 12,
        padding: "10px 12px",
        background: "#faf5ff",
        borderRadius: 6,
        border: "1px solid #e9d5ff",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          {streaming && <LoadingOutlined style={{ fontSize: 10, color: "#7c3aed" }} />}
          <span style={{ fontSize: 12, color: "#7c3aed", fontWeight: 500 }}>
            {streaming ? "思考中..." : "思考过程"}
          </span>
        </div>
        {!streaming && (
          <span
            onClick={() => setCollapsed(true)}
            style={{ fontSize: 10, color: "#a78bfa", cursor: "pointer" }}
          >
            &#9652; 折叠
          </span>
        )}
      </div>
      <div
        style={{
          fontSize: 12,
          lineHeight: 1.7,
          color: "#6b21a8",
          maxHeight: streaming ? 120 : 200,
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

  // AI 消息：左对齐
  const isThinkingDone = !isStreaming && !!message.thinking_steps && message.thinking_steps.length > 0
    ? true
    : undefined;

  return (
    <div style={{ display: "flex", justifyContent: "flex-start" }}>
      <div
        style={{
          background: "#ffffff",
          border: "1px solid #e5edf5",
          borderRadius: 8,
          padding: 24,
          width: "100%",
          boxShadow: "rgba(23,23,23,0.06) 0px 3px 6px",
        }}
      >
        {/* 思维链步骤 */}
        {message.thinking_steps && message.thinking_steps.length > 0 && (
          <ThinkingChain
            steps={message.thinking_steps}
            completed={isThinkingDone}
          />
        )}

        {/* 推理思考过程（GLM/DeepSeek 等推理模型） */}
        {(message.reasoning || (isStreaming && !message.content)) && (
          <ReasoningBox
            text={message.reasoning || ""}
            streaming={isStreaming && !message.content}
          />
        )}

        {/* 正文内容 */}
        {message.content ? (
          <div className="markdown-body">
            <ReactMarkdown>{message.content}</ReactMarkdown>
          </div>
        ) : isStreaming && !message.reasoning ? (
          <div style={{ textAlign: "center", padding: "24px 0" }}>
            <Spin
              indicator={
                <LoadingOutlined style={{ color: "#533afd", fontSize: 24 }} spin />
              }
            />
          </div>
        ) : null}

        {/* 流式进行中提示 */}
        {isStreaming && message.content && (
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
    </div>
  );
};

export default MessageBubble;
