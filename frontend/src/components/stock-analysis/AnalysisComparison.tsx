import React from "react";
import { Modal, Table, Typography, Tag } from "antd";
import { SwapOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";

const { Text } = Typography;

const ACTION_TAG_COLOR: Record<string, string> = {
  "买入": "green",
  "卖出": "red",
  "持有": "blue",
};

interface ComparisonItem {
  id: string;
  title: string;
  created_at: string;
  analysis_data?: {
    decision?: {
      action?: string;
      target_price?: number;
      confidence?: number;
      risk_score?: number;
      reasoning?: string;
    };
  };
}

interface AnalysisComparisonProps {
  open: boolean;
  onClose: () => void;
  items: ComparisonItem[];
}

const AnalysisComparison: React.FC<AnalysisComparisonProps> = ({ open, onClose, items }) => {
  if (items.length < 2) return null;

  const left = items[0];
  const right = items[1];
  const leftDecision = left.analysis_data?.decision || {};
  const rightDecision = right.analysis_data?.decision || {};

  const highlightDiff = (leftVal: any, rightVal: any, text: string) => {
    if (leftVal !== rightVal && leftVal !== undefined && rightVal !== undefined) {
      return <span style={{ background: "#fef3c7", padding: "0 4px", borderRadius: 2 }}>{text}</span>;
    }
    return text;
  };

  const columns: ColumnsType<{ field: string; left: any; right: any }> = [
    { title: "对比项", dataIndex: "field", key: "field", width: 100, render: (t: string) => <Text style={{ fontSize: 12, color: "#64748d" }}>{t}</Text> },
    {
      title: (
        <div>
          <Text style={{ fontSize: 12, color: "#061b31" }}>{left.title?.slice(0, 12)}</Text>
          <br />
          <Text style={{ fontSize: 10, color: "#94a3b8" }}>{left.created_at?.slice(0, 10)}</Text>
        </div>
      ),
      dataIndex: "left",
      key: "left",
      render: (val: any, record: any) => record.leftRender || val,
    },
    {
      title: (
        <div>
          <Text style={{ fontSize: 12, color: "#061b31" }}>{right.title?.slice(0, 12)}</Text>
          <br />
          <Text style={{ fontSize: 10, color: "#94a3b8" }}>{right.created_at?.slice(0, 10)}</Text>
        </div>
      ),
      dataIndex: "right",
      key: "right",
      render: (val: any, record: any) => record.rightRender || val,
    },
  ];

  const data = [
    {
      key: "action",
      field: "操作方向",
      left: leftDecision.action || "-",
      right: rightDecision.action || "-",
      leftRender: leftDecision.action ? <Tag color={ACTION_TAG_COLOR[leftDecision.action] || "default"}>{leftDecision.action}</Tag> : "-",
      rightRender: rightDecision.action ? <Tag color={ACTION_TAG_COLOR[rightDecision.action] || "default"}>{rightDecision.action}</Tag> : "-",
    },
    {
      key: "target_price",
      field: "目标价",
      left: leftDecision.target_price ? `${leftDecision.target_price.toFixed(2)}元` : "-",
      right: rightDecision.target_price ? `${rightDecision.target_price.toFixed(2)}元` : "-",
    },
    {
      key: "confidence",
      field: "置信度",
      left: leftDecision.confidence ? `${Math.round(leftDecision.confidence * 100)}%` : "-",
      right: rightDecision.confidence ? `${Math.round(rightDecision.confidence * 100)}%` : "-",
    },
    {
      key: "risk_score",
      field: "风险评分",
      left: leftDecision.risk_score ? `${Math.round(leftDecision.risk_score * 100)}%` : "-",
      right: rightDecision.risk_score ? `${Math.round(rightDecision.risk_score * 100)}%` : "-",
    },
    {
      key: "reasoning",
      field: "决策依据",
      left: leftDecision.reasoning?.slice(0, 60) || "-",
      right: rightDecision.reasoning?.slice(0, 60) || "-",
    },
  ];

  return (
    <Modal
      title={
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <SwapOutlined style={{ color: "#533afd" }} />
          <Text style={{ fontSize: 15, fontWeight: 400, color: "#061b31" }}>对比分析</Text>
        </div>
      }
      open={open}
      onCancel={onClose}
      footer={null}
      width={680}
    >
      <Table
        columns={columns}
        dataSource={data}
        pagination={false}
        size="small"
        style={{ marginTop: 8 }}
      />
    </Modal>
  );
};

export default AnalysisComparison;
