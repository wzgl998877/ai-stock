/** ThinkingChain — 思维链步骤列表，独立区块展示，分析完成后可折叠 */

import React, { useState } from "react";
import { Typography } from "antd";
import { CheckCircleFilled, CloseCircleFilled, LoadingOutlined } from "@ant-design/icons";
import type { ThinkingStepData } from "../../domain/types";

const { Text } = Typography;

interface Props {
  steps: ThinkingStepData[];
  /** 是否已完成（非流式状态） */
  completed?: boolean;
}

const ThinkingChain: React.FC<Props> = ({ steps, completed }) => {
  // 用户是否主动展开（覆盖默认折叠行为）
  const [expanded, setExpanded] = useState(false);

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

  // 已完成且未主动展开时，显示折叠摘要
  const showCollapsed = completed && isAllDone && !expanded;

  if (showCollapsed) {
    const doneCount = normalizedSteps.filter((s) => s.status === "done").length;
    return (
      <div
        onClick={() => setExpanded(true)}
        style={{
          padding: "10px 16px",
          background: "#f0fdf4",
          borderRadius: 8,
          border: "1px solid #bbf7d0",
          cursor: "pointer",
          display: "flex",
          alignItems: "center",
          gap: 8,
          fontSize: 14,
          color: "#16a34a",
          fontWeight: 500,
        }}
      >
        <CheckCircleFilled style={{ fontSize: 14 }} />
        <span>
          完成 {doneCount}/{normalizedSteps.length} 个步骤
        </span>
        <span style={{ color: "#94a3b8", marginLeft: 4, fontSize: 12 }}>&#9662; 展开</span>
      </div>
    );
  }

  return (
    <div
      style={{
        padding: "12px 16px",
        background: "#f8fafc",
        borderRadius: 8,
        border: "1px solid #e5edf5",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
        <span style={{ fontSize: 14, color: "#273951", fontWeight: 600 }}>分析步骤</span>
        {isAllDone && (
          <span
            onClick={() => setExpanded(false)}
            style={{
              fontSize: 12,
              color: "#94a3b8",
              cursor: "pointer",
            }}
          >
            &#9652; 折叠
          </span>
        )}
      </div>
      {normalizedSteps.map((step, i) => (
        <div
          key={i}
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            fontSize: 14,
            lineHeight: "26px",
            color:
              step.status === "done"
                ? "#16a34a"
                : step.status === "failed"
                ? "#ea2261"
                : "#64748d",
          }}
        >
          {step.status === "done" && (
            <CheckCircleFilled style={{ fontSize: 13, color: "#16a34a" }} />
          )}
          {step.status === "failed" && (
            <CloseCircleFilled style={{ fontSize: 13, color: "#ea2261" }} />
          )}
          {step.status === "running" && (
            <LoadingOutlined style={{ fontSize: 13, color: "#64748d" }} />
          )}
          <Text
            style={{
              fontSize: 14,
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
