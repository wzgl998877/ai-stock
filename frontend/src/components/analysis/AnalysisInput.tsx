/** AnalysisInput — 输入框 + 草稿自动保存 + 字数校验 */

import React, { useState, useEffect } from "react";
import { Input, Button, Typography, Space } from "antd";
import { SendOutlined } from "@ant-design/icons";
import { useDraft } from "../../hooks/useDraft";
import { EventType } from "../../domain/types";
import SimilarPrompt from "./SimilarPrompt";

const { TextArea } = Input;
const { Text } = Typography;

const MIN_LENGTH = 10;

interface Props {
  eventType: EventType;
  disabled?: boolean;
  onSubmit: (question: string) => void;
}

const AnalysisInput: React.FC<Props> = ({ eventType, disabled, onSubmit }) => {
  const { draft, saveDraft, clearDraft } = useDraft(eventType);
  const [input, setInput] = useState(draft);
  const [hint, setHint] = useState<string>("");

  useEffect(() => {
    setInput(draft);
  }, [draft]);

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

  return (
    <div>
      <TextArea
        value={input}
        onChange={(e) => handleChange(e.target.value)}
        placeholder="描述你想分析的市场事件，例如：美国对伊朗实施新一轮制裁，对A股有什么影响？"
        autoSize={{ minRows: 3, maxRows: 6 }}
        disabled={disabled}
        maxLength={500}
        showCount
        style={{
          borderRadius: 10,
          borderColor: "#eaecf0",
          fontSize: 14,
        }}
      />
      {hint && (
        <Text
          type="warning"
          style={{ fontSize: 12, marginTop: 6, display: "block" }}
        >
          {hint}
        </Text>
      )}
      <SimilarPrompt question={input} />
      <Space style={{ marginTop: 16 }}>
        <Button
          type="primary"
          icon={<SendOutlined />}
          onClick={handleSubmit}
          disabled={disabled || !input.trim()}
          loading={disabled}
          style={{
            height: 40,
            paddingLeft: 24,
            paddingRight: 24,
            borderRadius: 10,
            fontWeight: 500,
            background: disabled || !input.trim()
              ? undefined
              : "linear-gradient(135deg, #07C160, #0cce6b)",
            boxShadow:
              disabled || !input.trim()
                ? "none"
                : "0 2px 8px rgba(7, 193, 96, 0.3)",
          }}
        >
          开始分析
        </Button>
      </Space>
    </div>
  );
};

export default AnalysisInput;
