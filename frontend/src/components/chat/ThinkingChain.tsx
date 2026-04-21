/** ThinkingChain — 思维链步骤列表，分析完成后可折叠 */

import React, { useState } from "react";
import { Typography } from "antd";
import { CheckCircleFilled, CloseCircleFilled } from "@ant-design/icons";
import type { ThinkingStepData } from "../../domain/types";

const { Text } = Typography;

interface Props {
  steps: ThinkingStepData[];
  /** 是否已完成（非流式状态） */
  completed?: boolean;
}

const ThinkingChain: React.FC<Props> = ({ steps, completed }) => {
  const [collapsed, setCollapsed] = useState(false);

  if (steps.length === 0) return null;

  // 如果已完成（非流式），将所有 running 状态视为 done
  const normalizedSteps = completed
    ? steps.map((s) =>
        s.status === "running" ? { ...s, status: "done" as const } : s
      )
    : steps;

  const isAllDone = normalizedSteps.every(
    (s) => s.status === "done" || s.status === "failed"
  );

  // 已完成时默认折叠，显示摘要行
  if (collapsed || (completed && isAllDone)) {
    const doneCount = normalizedSteps.filter((s) => s.status === "done").length;
    return (
      <div
        onClick={() => setCollapsed(false)}
        style={{
          marginBottom: 12,
          padding: "6px 12px",
          background: "#f0fdf4",
          borderRadius: 6,
          border: "1px solid #bbf7d0",
          cursor: "pointer",
          display: "flex",
          alignItems: "center",
          gap: 6,
          fontSize: 12,
          color: "#16a34a",
        }}
      >
        <CheckCircleFilled style={{ fontSize: 12 }} />
        <span>
          完成 {doneCount}/{normalizedSteps.length} 个步骤
        </span>
        <span style={{ color: "#94a3b8", marginLeft: 4 }}>&#9662; 展开</span>
      </div>
    );
  }

  return (
    <div
      style={{
        marginBottom: 12,
        padding: "8px 12px",
        background: "#f8fafc",
        borderRadius: 6,
        border: "1px solid #e5edf5",
      }}
    >
      {isAllDone && (
        <div
          onClick={() => setCollapsed(true)}
          style={{
            display: "flex",
            justifyContent: "flex-end",
            cursor: "pointer",
            marginBottom: 4,
            fontSize: 11,
            color: "#94a3b8",
          }}
        >
          &#9652; 折叠
        </div>
      )}
      {normalizedSteps.map((step, i) => (
        <div
          key={i}
          style={{
            display: "flex",
            alignItems: "center",
            gap: 6,
            fontSize: 12,
            lineHeight: "22px",
            color:
              step.status === "done"
                ? "#16a34a"
                : step.status === "failed"
                ? "#ea2261"
                : "#64748d",
          }}
        >
          {step.status === "done" && (
            <CheckCircleFilled style={{ fontSize: 10, color: "#16a34a" }} />
          )}
          {step.status === "failed" && (
            <CloseCircleFilled style={{ fontSize: 10, color: "#ea2261" }} />
          )}
          <Text
            style={{
              fontSize: 12,
              color:
                step.status === "done"
                  ? "#16a34a"
                  : step.status === "failed"
                  ? "#ea2261"
                  : "#64748d",
            }}
          >
            {step.message}
          </Text>
        </div>
      ))}
    </div>
  );
};

export default ThinkingChain;
