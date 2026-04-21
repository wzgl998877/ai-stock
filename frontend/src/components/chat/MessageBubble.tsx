/** MessageBubble — 单条消息气泡 */

import React from "react";
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
  // 非流式状态（分析完成或从历史加载）时，思维链标记为已完成
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
        {/* 思维链 */}
        {message.thinking_steps && message.thinking_steps.length > 0 && (
          <ThinkingChain
            steps={message.thinking_steps}
            completed={isThinkingDone}
          />
        )}

        {/* 内容区 */}
        {message.content ? (
          <div className="markdown-body">
            <ReactMarkdown>{message.content}</ReactMarkdown>
          </div>
        ) : isStreaming ? (
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
