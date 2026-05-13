/** 事件详情 Drawer — 三段式布局 */

import React, { useEffect, useState } from "react";
import {
  Drawer,
  Typography,
  Tag,
  Divider,
  Button,
  Spin,
  List,
  message,
} from "antd";
import {
  ThunderboltOutlined,
  LineChartOutlined,
  LinkOutlined,
  FileTextOutlined,
} from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import { eventRadarService } from "../../services/eventRadarService";
import { useStockDrawerStore } from "../../store/stockDrawerStore";

const { Text, Paragraph } = Typography;

interface EventDetailDrawerProps {
  visible: boolean;
  impactId: number | null;
  onClose: () => void;
}

const sentimentLabels: Record<string, { color: string; label: string }> = {
  positive: { color: "#15be53", label: "利好" },
  negative: { color: "#ea2261", label: "利空" },
  neutral: { color: "#64748d", label: "中性" },
};

const EventDetailDrawer: React.FC<EventDetailDrawerProps> = ({
  visible,
  impactId,
  onClose,
}) => {
  const [detail, setDetail] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const { open: openStockDrawer } = useStockDrawerStore();

  useEffect(() => {
    if (visible && impactId) {
      setLoading(true);
      eventRadarService
        .getImpactDetail(impactId)
        .then((data) => setDetail(data))
        .catch(() => message.error("加载详情失败"))
        .finally(() => setLoading(false));
    } else {
      setDetail(null);
    }
  }, [visible, impactId]);

  const handleQuickAnalysis = () => {
    if (!detail) return;
    const params = new URLSearchParams({
      eventTitle: detail.title,
      eventSummary: detail.summary || "",
      eventType: detail.event_type || "other",
    });
    onClose();
    navigate(`/analysis?${params.toString()}`);
  };

  const handleViewStock = (code: string) => {
    openStockDrawer(code);
  };

  return (
    <Drawer
      title={detail?.title || "事件详情"}
      placement="right"
      width={520}
      open={visible}
      onClose={onClose}
    >
      {loading ? (
        <div style={{ textAlign: "center", padding: "60px 0" }}>
          <Spin />
        </div>
      ) : detail ? (
        <>
          {/* 第一段：原文摘要 */}
          <div style={{ marginBottom: 16 }}>
            <Text style={{ fontSize: 12, color: "#94a3b8" }}>原文摘要</Text>
            <Paragraph style={{ marginTop: 4, color: "#061b31" }}>
              {detail.summary || "暂无摘要"}
            </Paragraph>
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
              {detail.sentiment && (
                <Tag color={sentimentLabels[detail.sentiment]?.color === "#15be53" ? "green" : sentimentLabels[detail.sentiment]?.color === "#ea2261" ? "red" : "default"}>
                  {sentimentLabels[detail.sentiment]?.label || detail.sentiment}
                </Tag>
              )}
              {detail.matched_stocks?.map((s: any) => (
                <Tag
                  key={s.code}
                  color={s.direction === "positive" ? "green" : s.direction === "negative" ? "red" : "default"}
                  style={{ cursor: "pointer" }}
                  onClick={() => handleViewStock(s.code)}
                >
                  {s.name || s.code}
                </Tag>
              ))}
            </div>
            {detail.articles?.length > 0 && (
              <div style={{ marginTop: 8 }}>
                {detail.articles.map((a: any) => (
                  <div key={a.article_id} style={{ marginBottom: 4 }}>
                    <a href={a.url} target="_blank" rel="noopener noreferrer" style={{ fontSize: 12 }}>
                      <LinkOutlined /> {a.source} - {a.title}
                    </a>
                  </div>
                ))}
              </div>
            )}
          </div>

          <Divider style={{ margin: "12px 0" }} />

          {/* 第二段：AI 解读 */}
          <div style={{ marginBottom: 16 }}>
            <Text style={{ fontSize: 12, color: "#94a3b8" }}>AI 影响解读</Text>
            {detail.ai_insight ? (
              <div style={{ marginTop: 8 }}>
                <Paragraph>{detail.ai_insight.event_nature}</Paragraph>
                {detail.ai_insight.stock_impact_reasons?.map((r: any) => (
                  <div key={r.code} style={{ marginBottom: 4 }}>
                    <Text strong>{r.name}</Text>: <Text type="secondary">{r.reason}</Text>
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ marginTop: 8, color: "#94a3b8", fontSize: 13 }}>
                暂无 AI 解读
              </div>
            )}
          </div>

          <Divider style={{ margin: "12px 0" }} />

          {/* 知识库关联区域 */}
          {detail.related_analyses && detail.related_analyses.length > 0 && (
            <>
              <div style={{ marginBottom: 16 }}>
                <Text style={{ fontSize: 12, color: "#94a3b8" }}>
                  <FileTextOutlined style={{ marginRight: 4 }} />
                  知识库关联
                </Text>
                <List
                  size="small"
                  style={{ marginTop: 8 }}
                  dataSource={detail.related_analyses}
                  renderItem={(item: any) => (
                    <List.Item style={{ padding: "8px 0", border: "none" }}>
                      <List.Item.Meta
                        title={
                          <a
                            href={`/analysis?articleId=${item.article_id}`}
                            onClick={(e) => {
                              e.preventDefault();
                              const params = new URLSearchParams({
                                articleId: item.article_id,
                              });
                              onClose();
                              navigate(`/analysis?${params.toString()}`);
                            }}
                            style={{ color: "#1677ff", fontSize: 13 }}
                          >
                            {item.title}
                          </a>
                        }
                        description={
                          <div>
                            {item.analyzed_at && (
                              <Text style={{ fontSize: 12, color: "#94a3b8", marginRight: 8 }}>
                                {item.analyzed_at.substring(0, 10)}
                              </Text>
                            )}
                            {item.summary && (
                              <Paragraph
                                ellipsis={{ rows: 2 }}
                                style={{ fontSize: 12, color: "#64748b", margin: 0 }}
                              >
                                {item.summary}
                              </Paragraph>
                            )}
                          </div>
                        }
                      />
                    </List.Item>
                  )}
                />
              </div>
              <Divider style={{ margin: "12px 0" }} />
            </>
          )}

          {/* 第三段：行动按钮 */}
          <div>
            <Text style={{ fontSize: 12, color: "#94a3b8" }}>操作</Text>
            <div style={{ marginTop: 8, display: "flex", gap: 8 }}>
              <Button type="primary" icon={<ThunderboltOutlined />} onClick={handleQuickAnalysis}>
                一键分析
              </Button>
              {detail.matched_stocks?.[0] && (
                <Button
                  icon={<LineChartOutlined />}
                  onClick={() => handleViewStock(detail.matched_stocks[0].code)}
                >
                  查看K线
                </Button>
              )}
            </div>
          </div>

          <div style={{ marginTop: 24, padding: "8px 12px", background: "#f6f9fc", borderRadius: 6 }}>
            <Text style={{ fontSize: 12, color: "#98a2b3" }}>
              以上为 AI 分析参考，不构成投资建议
            </Text>
          </div>
        </>
      ) : (
        <div style={{ textAlign: "center", padding: "60px 0", color: "#94a3b8" }}>
          暂无数据
        </div>
      )}
    </Drawer>
  );
};

export default EventDetailDrawer;
