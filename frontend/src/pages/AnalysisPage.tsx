/** AnalysisPage — AI 事件分析主页面（Stripe 对话式布局） */

import React, { useState } from "react";
import { Button, Modal, Input, Typography, message } from "antd";
import { useAnalysis } from "../application/useAnalysis";
import AnalysisResult from "../components/analysis/AnalysisResult";
import AnalysisInput from "../components/analysis/AnalysisInput";
import EventTypeSelector from "../components/analysis/EventTypeSelector";
import IndustryTag from "../components/common/IndustryTag";
import { EventType, AnalysisStatus } from "../domain/types";
import { saveArticle } from "../services/analysisService";
import { useAnalysisStore } from "../store/analysisStore";

const { Text } = Typography;

const AnalysisPage: React.FC = () => {
  const [eventType, setEventType] = useState<EventType | null>(null);
  const { status, result, analyze, stop, isStreaming, isDone } = useAnalysis();
  const { title, summary, industries, reset } = useAnalysisStore();

  // 保存相关状态
  const [editTitle, setEditTitle] = useState("");
  const [editSummary, setEditSummary] = useState("");
  const [editIndustries, setEditIndustries] = useState<string[]>([]);
  const [saveModalOpen, setSaveModalOpen] = useState(false);
  const [saving, setSaving] = useState(false);

  const handleSubmit = (question: string) => {
    analyze(eventType ?? EventType.GEO_POLITICAL, question);
  };

  const isIdle = status === AnalysisStatus.IDLE && !result;

  // 打开保存确认弹窗
  const handleOpenSaveModal = () => {
    setEditTitle(title || "");
    setEditSummary(summary || "");
    setEditIndustries([...industries]);
    setSaveModalOpen(true);
  };

  // 执行保存
  const handleSave = async () => {
    if (editIndustries.length === 0) {
      message.warning("请至少保留1个行业标签");
      return;
    }

    setSaving(true);
    try {
      const store = useAnalysisStore.getState();
      await saveArticle({
        title: editTitle,
        summary: editSummary,
        content: store.result,
        event_type: eventType ?? EventType.OTHER,
        raw_input: "",
        industry_codes: editIndustries,
        stock_refs: [],
        chain_table: null,
      });
      message.success(`已保存，关联了${editIndustries.length}个行业`);
      setSaveModalOpen(false);
      reset();
    } catch (err) {
      message.error(err instanceof Error ? err.message : "保存失败");
    } finally {
      setSaving(false);
    }
  };

  // 不保存，重置
  const handleDiscard = () => {
    reset();
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
            {/* 分析完成后：可编辑标题和摘要 */}
            {isDone && title && (
              <div style={{ marginBottom: 16 }}>
                <Input
                  value={title}
                  onChange={(e) => useAnalysisStore.getState().setTitle(e.target.value)}
                  bordered={false}
                  placeholder="文章标题"
                  style={{
                    fontSize: 22,
                    fontWeight: 300,
                    color: "#061b31",
                    fontFeatureSettings: "'ss01' on",
                    letterSpacing: "-0.22px",
                    padding: "4px 0",
                    borderBottom: "1px solid #e5edf5",
                    marginBottom: 8,
                  }}
                />
                <Input.TextArea
                  value={summary}
                  onChange={(e) => useAnalysisStore.getState().setSummary(e.target.value)}
                  autoSize
                  bordered={false}
                  placeholder="文章摘要"
                  style={{
                    fontSize: 14,
                    color: "#64748d",
                    padding: "4px 0",
                    borderBottom: "1px solid #e5edf5",
                    resize: "none",
                  }}
                />
              </div>
            )}

            <AnalysisResult onStop={stop} />

            {/* 分析完成后：保存/丢弃按钮 */}
            {isDone && (
              <div
                style={{
                  display: "flex",
                  justifyContent: "flex-end",
                  gap: 12,
                  marginTop: 16,
                  paddingTop: 16,
                  borderTop: "1px solid #e5edf5",
                }}
              >
                <Button
                  onClick={handleDiscard}
                  style={{
                    borderRadius: 4,
                    borderColor: "#e5edf5",
                    color: "#64748d",
                    fontWeight: 400,
                  }}
                >
                  不保存
                </Button>
                <Button
                  type="primary"
                  onClick={handleOpenSaveModal}
                  style={{
                    borderRadius: 4,
                    fontWeight: 400,
                  }}
                >
                  保存到知识库
                </Button>
              </div>
            )}
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
          <Text style={{ fontSize: 13, color: "#273951", marginBottom: 6, display: "block" }}>
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
          <Text style={{ fontSize: 13, color: "#273951", marginBottom: 6, display: "block" }}>
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
          <Text style={{ fontSize: 13, color: "#273951", marginBottom: 6, display: "block" }}>
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
            <Text style={{ fontSize: 12, color: "#ea2261", marginTop: 8, display: "block" }}>
              请至少保留1个行业标签
            </Text>
          )}
        </div>
      </Modal>
    </div>
  );
};

export default AnalysisPage;
