/** AnalysisInput — 对话式输入框（Stripe Design） */

import React, { useState, useEffect } from "react";
import { Input, Typography } from "antd";
import { ArrowUpOutlined } from "@ant-design/icons";
import { useDraft } from "../../hooks/useDraft";
import { EventType } from "../../domain/types";
import SimilarPrompt from "./SimilarPrompt";

const { Text } = Typography;

const MIN_LENGTH = 10;

interface Props {
  eventType: EventType | null;
  disabled?: boolean;
  onSubmit: (question: string) => void;
  /** 外部强制清空（用于分析完成后重置） */
  forceClear?: boolean;
}

const AnalysisInput: React.FC<Props> = ({ eventType, disabled, onSubmit, forceClear }) => {
  const { saveDraft, clearDraft } = useDraft(eventType ?? "default");
  const [input, setInput] = useState("");
  const [hint, setHint] = useState<string>("");
  const [focused, setFocused] = useState(false);

  // 外部强制清空
  useEffect(() => {
    if (forceClear) {
      setInput("");
      setHint("");
    }
  }, [forceClear]);

  const handleChange = (val: string) => {
    setInput(val);
    saveDraft(val);
    if (!val.trim()) {
      setHint("");
    } else if (val.trim().length < MIN_LENGTH) {
      setHint("描述太简短，请详细说明");
    } else {
      setHint("");
    }
  };

  const handleSubmit = () => {
    if (!input.trim()) {
      setHint("请输入事件描述");
      return;
    }
    if (input.trim().length < MIN_LENGTH) {
      setHint("描述太简短，请详细说明");
      return;
    }
    onSubmit(input.trim());
    clearDraft();
    setInput("");
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const canSend = input.trim().length >= MIN_LENGTH;

  return (
    <div>
      {/* 输入框容器 */}
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          background: "#ffffff",
          border: `1px solid ${focused ? "#c4b5fd" : "#e5edf5"}`,
          borderRadius: 16,
          padding: 10,
          width: 780,
          minHeight: 80,
          maxHeight: 280,
          boxShadow: "rgba(23,23,23,0.06) 0px 2px 8px",
          transition: "border-color 0.15s ease",
          boxSizing: "border-box",
        }}
      >
        <Input.TextArea
          value={input}
          onChange={(e) => handleChange(e.target.value)}
          onKeyDown={handleKeyDown}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          placeholder="描述你想分析的市场事件..."
          autoSize
          disabled={disabled}
          maxLength={500}
          bordered={false}
          style={{
            fontSize: 15,
            fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
            fontFeatureSettings: "'ss01' on",
            resize: "none",
            color: "#061b31",
            lineHeight: 1.6,
            padding: 0,
            flex: 1,
          }}
        />
        {/* 底部操作栏：发送按钮右对齐 */}
        <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 6 }}>
          <button
            onClick={handleSubmit}
            disabled={disabled || !canSend}
            style={{
              width: 36,
              height: 36,
              borderRadius: "50%",
              border: "none",
              background: canSend && !disabled ? "#533afd" : "#e5edf5",
              color: canSend && !disabled ? "#ffffff" : "#b0b8c4",
              cursor: canSend && !disabled ? "pointer" : "default",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              transition: "background 0.2s",
              fontSize: 16,
            }}
          >
            <ArrowUpOutlined />
          </button>
        </div>
      </div>

      {hint && (
        <Text
          style={{
            fontSize: 12,
            color: "#ea2261",
            marginTop: 8,
            display: "block",
            paddingLeft: 20,
            fontFeatureSettings: "'ss01' on",
          }}
        >
          {hint}
        </Text>
      )}
      <SimilarPrompt question={input} />
    </div>
  );
};

export default AnalysisInput;
