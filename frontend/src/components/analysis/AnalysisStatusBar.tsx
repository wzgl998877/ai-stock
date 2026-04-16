/** AnalysisStatusBar — 全局分析状态条 */

import React from "react";
import { Alert, Space } from "antd";
import { SyncOutlined, CheckCircleOutlined } from "@ant-design/icons";
import { useAnalysisStore } from "../../store/analysisStore";
import { AnalysisStatus } from "../../domain/types";

const AnalysisStatusBar: React.FC = () => {
  const { status, title } = useAnalysisStore();

  if (status === AnalysisStatus.IDLE) return null;

  if (status === AnalysisStatus.STREAMING) {
    return (
      <Alert
        type="info"
        showIcon
        icon={<SyncOutlined spin style={{ color: "#07C160" }} />}
        message="分析进行中..."
        style={{ marginBottom: 16, borderRadius: 12, background: "#f0fdf4", border: "1px solid #bbf7d0" }}
        banner
      />
    );
  }

  if (status === AnalysisStatus.DONE) {
    return (
      <Alert
        type="success"
        showIcon
        icon={<CheckCircleOutlined style={{ color: "#07C160" }} />}
        message={
          <Space>
            <span>分析完成</span>
            {title && (
              <a
                onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
                style={{ color: "#07C160" }}
              >
                点击查看
              </a>
            )}
          </Space>
        }
        style={{ marginBottom: 16, borderRadius: 12, background: "#f0fdf4", border: "1px solid #bbf7d0" }}
        closable
      />
    );
  }

  if (status === AnalysisStatus.ERROR) {
    return (
      <Alert
        type="error"
        message="分析失败"
        description="请检查网络连接后重试"
        style={{ marginBottom: 16, borderRadius: 12 }}
        closable
      />
    );
  }

  return null;
};

export default AnalysisStatusBar;
