/** MessageList — 消息列表，自动滚动到底部 */

import React, { useEffect, useRef, useState, useCallback } from "react";
import { useChatStore } from "../../store/chatStore";
import MessageBubble from "./MessageBubble";
import { Button } from "antd";
import { ArrowDownOutlined } from "@ant-design/icons";

const SCROLL_THRESHOLD = 300; // 距离底部超过此值时显示按钮

const MessageList: React.FC<{
  onNewChat: () => void;
  onSaveToKnowledge: () => void;
  /** 当滚动距离底部较远时触发 */
  onScrollFarFromBottom?: (far: boolean) => void;
  /** 滚动到底部回调 */
  scrollBottomRef?: React.MutableRefObject<(() => void) | null>;
}> = ({ onNewChat, onSaveToKnowledge, onScrollFarFromBottom, scrollBottomRef }) => {
  const { messages, streamingMessageId } = useChatStore();
  const containerRef = useRef<HTMLDivElement>(null);
  const [showScrollBottom, setShowScrollBottom] = useState(false);

  // 检查是否需要显示回到底部按钮
  const checkScrollPosition = useCallback(() => {
    const el = containerRef.current;
    if (!el) return;
    const distFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
    const far = distFromBottom > SCROLL_THRESHOLD;
    setShowScrollBottom(far);
    onScrollFarFromBottom?.(far);
  }, [onScrollFarFromBottom]);

  // 监听滚动
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    el.addEventListener("scroll", checkScrollPosition, { passive: true });
    return () => el.removeEventListener("scroll", checkScrollPosition);
  }, [checkScrollPosition]);

  // 有新内容时自动滚动到底部
  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [messages]);

  // 点击回到底部
  const scrollToBottom = useCallback(() => {
    const el = containerRef.current;
    if (!el) return;
    el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
  }, []);

  // 暴露 scrollToBottom 给父组件
  useEffect(() => {
    if (scrollBottomRef) scrollBottomRef.current = scrollToBottom;
  }, [scrollBottomRef, scrollToBottom]);

  if (messages.length === 0) return null;

  const isStreaming = streamingMessageId !== null;
  const showActions = !isStreaming && messages.length > 0;

  return (
    <div style={{ flex: 1, overflow: "hidden" }}>
      <div
        ref={containerRef}
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "24px 24px 100px",
          height: "100%",
        }}
      >
        <div
          style={{
            maxWidth: 780,
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
                  borderRadius: 20,
                  borderColor: "#e5edf5",
                  color: "#64748d",
                  fontWeight: 400,
                  paddingInline: 16,
                  height: 32,
                }}
              >
                新对话
              </Button>
              <Button
                type="primary"
                size="small"
                onClick={onSaveToKnowledge}
                style={{ borderRadius: 20, fontWeight: 400, paddingInline: 16, height: 32 }}
              >
                保存到知识库
              </Button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default MessageList;
