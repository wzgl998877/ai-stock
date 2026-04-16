/** AnalysisResult — Markdown 实时渲染 + 自动滚动 + 骨架屏 */

import React, { useEffect, useRef } from "react";
import { Spin, Alert, Typography } from "antd";
import { LoadingOutlined } from "@ant-design/icons";
import ReactMarkdown from "react-markdown";
import { useAnalysisStore } from "../../store/analysisStore";
import { AnalysisStatus } from "../../domain/types";

const { Text } = Typography;

const AnalysisResult: React.FC = () => {
  const { status, result, error } = useAnalysisStore();
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (status === AnalysisStatus.STREAMING && containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [result, status]);

  if (status === AnalysisStatus.IDLE) return null;

  if (status === AnalysisStatus.ERROR && error) {
    return (
      <Alert
        type="error"
        message="分析失败"
        description={error}
        showIcon
        style={{ marginTop: 20, borderRadius: 12 }}
      />
    );
  }

  if (status === AnalysisStatus.STREAMING && !result) {
    return (
      <div
        style={{
          textAlign: "center",
          padding: "48px 0",
          marginTop: 20,
          background: "#ffffff",
          borderRadius: 16,
          boxShadow: "0 1px 3px rgba(16, 24, 40, 0.06)",
        }}
      >
        <Spin
          size="large"
          indicator={<LoadingOutlined style={{ color: "#07C160", fontSize: 32 }} spin />}
        />
        <div style={{ marginTop: 16 }}>
          <Text style={{ color: "#667085", fontSize: 14 }}>
            AI 正在思考中...
          </Text>
        </div>
      </div>
    );
  }

  if (!result) return null;

  return (
    <div
      ref={containerRef}
      style={{
        marginTop: 20,
        padding: 24,
        background: "#ffffff",
        borderRadius: 16,
        maxHeight: 640,
        overflowY: "auto",
        boxShadow: "0 1px 3px rgba(16, 24, 40, 0.06), 0 1px 2px rgba(16, 24, 40, 0.04)",
      }}
    >
      <div className="markdown-body">
        <ReactMarkdown>{result}</ReactMarkdown>
      </div>
      {status === AnalysisStatus.STREAMING && (
        <Text
          className="streaming-pulse"
          style={{ fontSize: 12, color: "#07C160", marginTop: 12, display: "block" }}
        >
          分析进行中...
        </Text>
      )}
    </div>
  );
};

export default AnalysisResult;
