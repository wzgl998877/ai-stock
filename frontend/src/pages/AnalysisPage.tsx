/** AnalysisPage — AI 事件分析主页面（ChatGPT 对话式布局） */

import React, { useState, useCallback, useRef } from "react";
import { Button, Modal, Input, Typography, message } from "antd";
import MessageList from "../components/chat/MessageList";
import AnalysisInput from "../components/analysis/AnalysisInput";
import EventTypeSelector from "../components/analysis/EventTypeSelector";
import IndustryTag from "../components/common/IndustryTag";
import { EventType } from "../domain/types";
import type { SSEEvent } from "../domain/types";
import { useChatStore } from "../store/chatStore";
import * as chatService from "../services/chatService";
import { saveArticle } from "../services/analysisService";

const { Text } = Typography;

const AnalysisPage: React.FC = () => {
  const [eventType, setEventType] = useState<EventType | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const [inputClearFlag, setInputClearFlag] = useState(false);

  // chatStore
  const {
    currentSessionId,
    messages,
    streamingMessageId,
    title,
    summary,
    industries,
    setCurrentSessionId,
    addMessage,
    appendContent,
    appendReasoning,
    addThinkingStep,
    setTitle,
    setSummary,
    setIndustries,
    startStreaming,
    doneStreaming,
    resetMessages,
    addSession,
    setSessions,
  } = useChatStore();

  // 保存相关状态
  const [editTitle, setEditTitle] = useState("");
  const [editSummary, setEditSummary] = useState("");
  const [editIndustries, setEditIndustries] = useState<string[]>([]);
  const [saveModalOpen, setSaveModalOpen] = useState(false);
  const [saving, setSaving] = useState(false);

  const isStreaming = streamingMessageId !== null;
  const isIdle = messages.length === 0 && !isStreaming;

  // === 提交消息 ===
  const handleSubmit = useCallback(
    async (question: string) => {
      // 取消之前的请求
      if (abortRef.current) {
        abortRef.current.abort();
      }
      const controller = new AbortController();
      abortRef.current = controller;

      try {
        // 1. 确保有会话
        let sessionId = currentSessionId;
        if (!sessionId) {
          const session = await chatService.createSession();
          sessionId = session.id;
          setCurrentSessionId(sessionId);
          addSession(session);
          setSessions([session]);
        }

        // 2. 添加用户消息到 UI
        const userMsgId = Date.now().toString();
        addMessage({
          id: userMsgId,
          role: "user",
          content: question,
          reasoning: "",
          thinking_steps: null,
          event_type: eventType,
          created_at: new Date().toISOString(),
        });

        // 3. 创建占位 AI 消息
        const aiMsgId = (Date.now() + 1).toString();
        addMessage({
          id: aiMsgId,
          role: "assistant",
          content: "",
          reasoning: "",
          thinking_steps: [],
          event_type: eventType,
          created_at: new Date().toISOString(),
        });
        startStreaming(aiMsgId);

        // 4. 流式发送
        await chatService.streamMessage(
          sessionId,
          question,
          eventType,
          (event: SSEEvent) => {
            switch (event.type) {
              case "thinking":
                addThinkingStep(event.data as import("../domain/types").ThinkingStepData);
                break;
              case "reasoning":
                appendReasoning(event.data as string);
                break;
              case "content":
                appendContent(event.data as string);
                break;
              case "title":
                setTitle(event.data as string);
                break;
              case "summary":
                setSummary(event.data as string);
                break;
              case "industries":
                setIndustries(event.data as string[]);
                break;
              case "error":
                message.error(event.data as string);
                doneStreaming();
                break;
              case "done":
                doneStreaming();
                break;
            }
          },
          controller.signal
        );
      } catch (err) {
        if ((err as Error).name === "AbortError") return;
        message.error(err instanceof Error ? err.message : "分析失败");
        doneStreaming();
      }
    },
    [currentSessionId, eventType]
  );

  // === 停止 ===
  const handleStop = useCallback(() => {
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }
    doneStreaming();
  }, [doneStreaming]);

  // === 保存到知识库 ===
  const handleOpenSaveModal = () => {
    setEditTitle(title || "");
    setEditSummary(summary || "");
    setEditIndustries([...industries]);
    setSaveModalOpen(true);
  };

  const handleSave = async () => {
    if (editIndustries.length === 0) {
      message.warning("请至少保留1个行业标签");
      return;
    }
    setSaving(true);
    try {
      const lastAiMsg = [...messages].reverse().find((m) => m.role === "assistant");
      await saveArticle({
        title: editTitle,
        summary: editSummary,
        content: lastAiMsg?.content || "",
        event_type: eventType ?? EventType.OTHER,
        raw_input: "",
        industry_codes: editIndustries,
        stock_refs: [],
        chain_table: null,
      });
      message.success(`已保存，关联了${editIndustries.length}个行业`);
      setSaveModalOpen(false);
    } catch (err) {
      message.error(err instanceof Error ? err.message : "保存失败");
    } finally {
      setSaving(false);
    }
  };

  // === 新建对话（从页面按钮触发） ===
  const handleNewChat = () => {
    handleStop();
    setCurrentSessionId(null);
    resetMessages();
    setInputClearFlag((v) => !v);
  };

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100vh",
        overflow: "hidden",
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
            你好，我是{" "}
            <span style={{ color: "#533afd", fontWeight: 400 }}>
              AI 投研助手
            </span>
            ，有什么能帮你的吗？
          </h1>

          <div style={{ width: 780 }}>
            <AnalysisInput
              eventType={eventType}
              disabled={false}
              onSubmit={handleSubmit}
              forceClear={inputClearFlag}
            />
            <EventTypeSelector
              value={eventType}
              onChange={setEventType}
              disabled={false}
            />
          </div>
        </div>
      ) : (
        <>
          {/* 分析态：消息列表 */}
          <MessageList />

          {/* 分析完成后：保存/丢弃 */}
          {!isStreaming && messages.length > 0 && (
            <div
              style={{
                maxWidth: 860,
                width: "100%",
                margin: "0 auto",
                padding: "0 24px 8px",
                display: "flex",
                justifyContent: "flex-end",
                gap: 12,
              }}
            >
              <Button
                onClick={handleNewChat}
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
                onClick={handleOpenSaveModal}
                style={{ borderRadius: 4, fontWeight: 400 }}
              >
                保存到知识库
              </Button>
            </div>
          )}
        </>
      )}

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
              forceClear={inputClearFlag}
            />
            <EventTypeSelector
              value={eventType}
              onChange={setEventType}
              disabled={isStreaming}
            />
          </div>
        </div>
      )}

      {/* 行业标签确认弹窗 */}
      <Modal
        title="确认保存到知识库"
        open={saveModalOpen}
        onOk={handleSave}
        onCancel={() => setSaveModalOpen(false)}
        confirmLoading={saving}
        okText="确认保存"
        cancelText="取消"
        okButtonProps={{ style: { borderRadius: 4, fontWeight: 400 } }}
        cancelButtonProps={{ style: { borderRadius: 4 } }}
      >
        <div style={{ marginBottom: 16 }}>
          <Text
            style={{
              fontSize: 13,
              color: "#273951",
              marginBottom: 6,
              display: "block",
            }}
          >
            文章标题
          </Text>
          <Input
            value={editTitle}
            onChange={(e) => setEditTitle(e.target.value)}
            placeholder="请输入标题"
            style={{ borderRadius: 4 }}
          />
        </div>
        <div style={{ marginBottom: 16 }}>
          <Text
            style={{
              fontSize: 13,
              color: "#273951",
              marginBottom: 6,
              display: "block",
            }}
          >
            文章摘要
          </Text>
          <Input.TextArea
            value={editSummary}
            onChange={(e) => setEditSummary(e.target.value)}
            autoSize
            placeholder="请输入摘要"
            style={{ borderRadius: 4, resize: "none" }}
          />
        </div>
        <div>
          <Text
            style={{
              fontSize: 13,
              color: "#273951",
              marginBottom: 6,
              display: "block",
            }}
          >
            关联行业标签（至少1个）
          </Text>
          <IndustryTag
            industries={editIndustries}
            editable
            onRemove={(idx) => {
              const next = [...editIndustries];
              next.splice(idx, 1);
              setEditIndustries(next);
            }}
          />
          {editIndustries.length === 0 && (
            <Text
              style={{
                fontSize: 12,
                color: "#ea2261",
                marginTop: 8,
                display: "block",
              }}
            >
              请至少保留1个行业标签
            </Text>
          )}
        </div>
      </Modal>
    </div>
  );
};

export default AnalysisPage;
