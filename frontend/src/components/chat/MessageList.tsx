/** MessageList — 消息列表，自动滚动到底部 */

import React, { useEffect, useRef } from "react";
import { useChatStore } from "../../store/chatStore";
import MessageBubble from "./MessageBubble";
import { Button } from "antd";

const MessageList: React.FC<{
  onNewChat: () => void;
  onSaveToKnowledge: () => void;
}> = ({ onNewChat, onSaveToKnowledge }) => {
  const { messages, streamingMessageId } = useChatStore();
  const containerRef = useRef<HTMLDivElement>(null);

  // 有新内容时自动滚动到底部
  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [messages]);

  if (messages.length === 0) return null;

  const isStreaming = streamingMessageId !== null;
  const showActions = !isStreaming && messages.length > 0;

  return (
    <div
      ref={containerRef}
      style={{
        flex: 1,
        overflowY: "auto",
        padding: "24px 24px 100px",
      }}
    >
      <div
        style={{
          maxWidth: 860,
          width: "100%",
          margin: "0 auto",
          display: "flex",
          flexDirection: "column",
          gap: 16,
        }}
      >
        {messages.map((msg) => (
          <MessageBubble
            key={msg.id}
            message={msg}
            isStreaming={msg.id === streamingMessageId}
          />
        ))}

        {showActions && (
          <div
            style={{
              display: "flex",
              justifyContent: "flex-end",
              gap: 12,
              padding: "8px 0",
            }}
          >
            <Button
              onClick={onNewChat}
              size="small"
              style={{
                borderRadius: 4,
                borderColor: "#e5edf5",
                color: "#64748d",
                fontWeight: 400,
              }}
            >
              新对话
            </Button>
            <Button
              type="primary"
              size="small"
              onClick={onSaveToKnowledge}
              style={{ borderRadius: 4, fontWeight: 400 }}
            >
              保存到知识库
            </Button>
          </div>
        )}
      </div>
    </div>
  );
};

export default MessageList;
