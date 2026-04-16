/** AnalysisResult — 消息气泡式结果展示（Stripe Design） */

import React, { useEffect, useRef } from "react";
import { Spin, Typography, Button } from "antd";
import { LoadingOutlined, StopOutlined } from "@ant-design/icons";
import ReactMarkdown from "react-markdown";
import { useAnalysisStore } from "../../store/analysisStore";
import { AnalysisStatus } from "../../domain/types";

const { Text } = Typography;

interface Props {
  isStreaming?: boolean;
  onStop: () => void;
}

const AnalysisResult: React.FC<Props> = ({ onStop }) => {
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
      <div
        style={{
          padding: "16px 20px",
          background: "rgba(234,34,97,0.05)",
          borderRadius: 6,
          border: "1px solid rgba(234,34,97,0.2)",
          color: "#ea2261",
          fontSize: 14,
        }}
      >
        <Text style={{ color: "#ea2261", fontWeight: 400 }}>分析失败：</Text>
        <Text style={{ color: "#64748d" }}>{error}</Text>
      </div>
    );
  }

  if (status === AnalysisStatus.STREAMING && !result) {
    return (
      <div
        style={{
          textAlign: "center",
          padding: "48px 0",
        }}
      >
        <Spin
          size="large"
          indicator={<LoadingOutlined style={{ color: "#533afd", fontSize: 32 }} spin />}
        />
        <div style={{ marginTop: 16 }}>
          <Text
            style={{
              color: "#64748d",
              fontSize: 14,
              fontFeatureSettings: "'ss01' on",
            }}
          >
            AI 正在思考中...
          </Text>
        </div>
      </div>
    );
  }

  if (!result) return null;

  return (
    <div ref={containerRef}>
      {/* AI 回复区域 */}
      <div
        style={{
          background: "#ffffff",
          borderRadius: 8,
          border: "1px solid #e5edf5",
          padding: 24,
          boxShadow: "rgba(23,23,23,0.06) 0px 3px 6px",
        }}
      >
        <div className="markdown-body">
          <ReactMarkdown>{result}</ReactMarkdown>
        </div>
        {status === AnalysisStatus.STREAMING && (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              marginTop: 16,
              paddingTop: 12,
              borderTop: "1px solid #e5edf5",
            }}
          >
            <Text
              className="streaming-pulse"
              style={{
                fontSize: 12,
                color: "#533afd",
                fontFeatureSettings: "'ss01' on",
              }}
            >
              分析进行中...
            </Text>
            <Button
              size="small"
              icon={<StopOutlined />}
              onClick={onStop}
              style={{
                color: "#64748d",
                borderColor: "#e5edf5",
                borderRadius: 4,
                fontSize: 12,
              }}
            >
              停止
            </Button>
          </div>
        )}
      </div>
    </div>
  );
};

export default AnalysisResult;
