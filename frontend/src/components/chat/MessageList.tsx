/** MessageList — 消息列表，自动滚动到底部 */

import React, { useEffect, useRef } from "react";
import { useChatStore } from "../../store/chatStore";
import MessageBubble from "./MessageBubble";

const MessageList: React.FC = () => {
  const { messages, streamingMessageId } = useChatStore();
  const containerRef = useRef<HTMLDivElement>(null);

  // 有新内容时自动滚动到底部
  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [messages]);

  if (messages.length === 0) return null;

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
      </div>
    </div>
  );
};

export default MessageList;
