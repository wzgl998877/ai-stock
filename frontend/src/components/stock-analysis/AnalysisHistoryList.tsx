import React, { useEffect, useState } from "react";
import { List, Typography, Tag, Empty, Spin } from "antd";
import { ClockCircleOutlined } from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import * as knowledgeService from "../../services/knowledgeService";

const { Text } = Typography;

const ACTION_TAG_COLOR: Record<string, string> = {
  "买入": "green",
  "卖出": "red",
  "持有": "blue",
};

interface HistoryItem {
  id: string;
  title: string;
  summary: string;
  created_at: string;
  analysis_data?: {
    decision?: {
      action?: string;
      target_price?: number;
      confidence?: number;
      risk_score?: number;
    };
  };
}

interface AnalysisHistoryListProps {
  stockCode: string;
  onRefresh?: number;  // 递增触发刷新
}

const AnalysisHistoryList: React.FC<AnalysisHistoryListProps> = ({ stockCode, onRefresh }) => {
  const [items, setItems] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    if (!stockCode) return;
    setLoading(true);
    knowledgeService
      .getArticles({ article_type: "stock_analysis", stock_code: stockCode, page: 1, page_size: 3 })
      .then((res: any) => {
        setItems(res.items || []);
      })
      .catch(() => setItems([]))
      .finally(() => setLoading(false));
  }, [stockCode, onRefresh]);

  if (loading) {
    return <Spin style={{ display: "block", margin: "20px auto" }} />;
  }

  if (items.length === 0) {
    return <Empty description="暂无历史分析记录" image={Empty.PRESENTED_IMAGE_SIMPLE} />;
  }

  return (
    <List
      size="small"
      dataSource={items}
      renderItem={(item) => {
        const decision = item.analysis_data?.decision;
        return (
          <List.Item
            style={{ cursor: "pointer", padding: "8px 12px", borderRadius: 4 }}
            onClick={() => navigate(`/knowledge/articles/${item.id}`)}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", width: "100%" }}>
              <div style={{ flex: 1, minWidth: 0 }}>
                <Text style={{ fontSize: 13, color: "#061b31", display: "block", marginBottom: 4 }}>{item.title}</Text>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <ClockCircleOutlined style={{ fontSize: 11, color: "#94a3b8" }} />
                  <Text style={{ fontSize: 11, color: "#94a3b8" }}>{item.created_at?.slice(0, 10)}</Text>
                </div>
              </div>
              {decision && (
                <div style={{ display: "flex", alignItems: "center", gap: 8, flexShrink: 0 }}>
                  {decision.action && (
                    <Tag color={ACTION_TAG_COLOR[decision.action] || "default"} style={{ fontSize: 12, borderRadius: 4, margin: 0 }}>
                      {decision.action}
                    </Tag>
                  )}
                  {decision.target_price ? (
                    <Text style={{ fontSize: 12, color: "#061b31", fontFeatureSettings: "'tnum'" }}>
                      目标价 {decision.target_price.toFixed(2)}
                    </Text>
                  ) : null}
                </div>
              )}
            </div>
          </List.Item>
        );
      }}
    />
  );
};

export default AnalysisHistoryList;
