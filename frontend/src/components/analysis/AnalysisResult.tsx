/** AnalysisResult — Markdown 实时渲染 + 自动滚动 + 骨架屏 */

import React, { useEffect, useRef } from "react";
import { Spin, Alert, Typography } from "antd";
import ReactMarkdown from "react-markdown";
import { useAnalysisStore } from "../../store/analysisStore";
import { AnalysisStatus } from "../../domain/types";

const { Text } = Typography;

const AnalysisResult: React.FC = () => {
  const { status, result, error } = useAnalysisStore();
  const containerRef = useRef<HTMLDivElement>(null);

  // 自动滚动到底部
  useEffect(() => {
    if (status === AnalysisStatus.STREAMING && containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [result, status]);

  // 空状态
  if (status === AnalysisStatus.IDLE) return null;

  // 错误状态
  if (status === AnalysisStatus.ERROR && error) {
    return (
      <Alert
        type="error"
        message="分析失败"
        description={error}
        showIcon
        style={{ marginTop: 16 }}
      />
    );
  }

  // 思考中（无内容时显示骨架屏）
  if (status === AnalysisStatus.STREAMING && !result) {
    return (
      <div style={{ textAlign: "center", padding: "40px 0", marginTop: 16 }}>
        <Spin size="large" />
        <div style={{ marginTop: 12 }}>
          <Text type="secondary">AI 正在思考中...</Text>
        </div>
      </div>
    );
  }

  // 有内容时渲染
  if (!result) return null;

  return (
    <div
      ref={containerRef}
      style={{
        marginTop: 16,
        padding: 16,
        border: "1px solid #f0f0f0",
        borderRadius: 8,
        maxHeight: 600,
        overflowY: "auto",
        backgroundColor: "#fafafa",
      }}
    >
      <ReactMarkdown>{result}</ReactMarkdown>
      {status === AnalysisStatus.STREAMING && (
        <Text type="secondary" style={{ fontSize: 12 }}>
          分析进行中...
        </Text>
      )}
    </div>
  );
};

export default AnalysisResult;
