/** 事件详情 Drawer — 增强版三段式布局 */

import React, { useEffect, useState } from "react";
import {
  Drawer,
  Typography,
  Tag,
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
  positive: { color: "#16a34a", label: "利好" },
  negative: { color: "#dc2626", label: "利空" },
  neutral: { color: "#64748b", label: "中性" },
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

  const sentiment = detail?.sentiment ? sentimentLabels[detail.sentiment] : null;

  return (
    <Drawer
      title={
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ fontSize: 15, fontWeight: 600 }}>{detail?.title || "事件详情"}</span>
          {sentiment && (
            <Tag color={sentiment.color === "#16a34a" ? "success" : sentiment.color === "#dc2626" ? "error" : "default"}>
              {sentiment.label}
            </Tag>
          )}
        </div>
      }
      placement="right"
      width={560}
      open={visible}
      onClose={onClose}
      styles={{
        body: { padding: "16px 20px", background: "#fafbfc" },
      }}
    >
      {loading ? (
        <div style={{ textAlign: "center", padding: "60px 0" }}>
          <Spin />
          <div style={{ marginTop: 12, color: "#6366f1", fontSize: 13 }}>AI 正在加载事件详情...</div>
        </div>
      ) : detail ? (
        <>
          {/* Section 1: Summary */}
          <div style={{
            background: "#ffffff", borderRadius: 8, padding: 16,
            border: "1px solid #e5edf5", marginBottom: 12,
          }}>
            <div style={{ fontSize: 12, color: "#6366f1", fontWeight: 600, marginBottom: 8, letterSpacing: "0.5px" }}>
              原文摘要
            </div>
            <Paragraph style={{ color: "#1e293b", margin: 0, lineHeight: 1.7 }}>
              {detail.summary || "暂无摘要"}
            </Paragraph>
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginTop: 10 }}>
              {detail.matched_stocks?.map((s: any) => (
                <Tag
                  key={s.code}
                  color={s.direction === "positive" ? "success" : s.direction === "negative" ? "error" : "default"}
                  style={{ cursor: "pointer" }}
                  onClick={() => handleViewStock(s.code)}
                >
                  {s.name || s.code}
                  {s.direction === "positive" ? " ▲" : s.direction === "negative" ? " ▼" : ""}
                </Tag>
              ))}
            </div>
            {detail.articles?.length > 0 && (
              <div style={{ marginTop: 10 }}>
                <div style={{ fontSize: 11, color: "#94a3b8", marginBottom: 4 }}>来源</div>
                {detail.articles.map((a: any) => (
                  <div key={a.article_id} style={{ marginBottom: 4 }}>
                    <a href={a.url} target="_blank" rel="noopener noreferrer" style={{ fontSize: 13, color: "#6366f1" }}>
                      <LinkOutlined /> {a.source} - {a.title || "查看原文"}
                    </a>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Section 2: AI Insight */}
          <div style={{
            background: "linear-gradient(135deg, #f8faff, #f5f3ff)",
            borderRadius: 8, padding: 16,
            border: "1px solid #e0e7ff", marginBottom: 12,
          }}>
            <div style={{ fontSize: 12, color: "#6366f1", fontWeight: 600, marginBottom: 8, letterSpacing: "0.5px" }}>
              ◆ AI 影响解读
            </div>
            {detail.ai_insight ? (
              <div>
                <div style={{ fontSize: 14, color: "#1e293b", marginBottom: 8, lineHeight: 1.6 }}>
                  {detail.ai_insight.event_nature}
                </div>
                {detail.ai_insight.affected_industries_detail?.length > 0 && (
                  <div style={{ marginBottom: 8 }}>
                    <Text style={{ fontSize: 12, color: "#64748b" }}>影响行业</Text>
                    <div style={{ display: "flex", gap: 4, flexWrap: "wrap", marginTop: 4 }}>
                      {detail.ai_insight.affected_industries_detail.map((ind: any, i: number) => (
                        <Tag key={i} color="purple">{ind.name} ({ind.direction})</Tag>
                      ))}
                    </div>
                  </div>
                )}
                {detail.ai_insight.stock_impact_reasons?.length > 0 && (
                  <div>
                    <Text style={{ fontSize: 12, color: "#64748b" }}>个股影响分析</Text>
                    <div style={{ marginTop: 6 }}>
                      {detail.ai_insight.stock_impact_reasons.map((r: any) => (
                        <div key={r.code} style={{
                          padding: "8px 12px", background: "#ffffff", borderRadius: 6,
                          border: "1px solid #e0e7ff", marginBottom: 6,
                        }}>
                          <Text strong style={{ color: "#1e293b" }}>{r.name}</Text>
                          <div style={{ fontSize: 13, color: "#64748b", marginTop: 2 }}>{r.reason}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div style={{ color: "#94a3b8", fontSize: 13, padding: "8px 0" }}>
                暂无 AI 解读，点击下方按钮可生成
              </div>
            )}
          </div>

          {/* Section 3: Knowledge base */}
          {detail.related_analyses && detail.related_analyses.length > 0 && (
            <div style={{
              background: "#ffffff", borderRadius: 8, padding: 16,
              border: "1px solid #e5edf5", marginBottom: 12,
            }}>
              <div style={{ fontSize: 12, color: "#6366f1", fontWeight: 600, marginBottom: 8, letterSpacing: "0.5px" }}>
                <FileTextOutlined style={{ marginRight: 4 }} />
                知识库关联
              </div>
              <List
                size="small"
                dataSource={detail.related_analyses}
                renderItem={(item: any) => (
                  <List.Item style={{ padding: "8px 0", border: "none" }}>
                    <List.Item.Meta
                      title={
                        <a
                          href={`/analysis?articleId=${item.article_id}`}
                          onClick={(e) => {
                            e.preventDefault();
                            onClose();
                            navigate(`/analysis?articleId=${item.article_id}`);
                          }}
                          style={{ color: "#6366f1", fontSize: 13 }}
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
                            <Paragraph ellipsis={{ rows: 2 }} style={{ fontSize: 12, color: "#64748b", margin: 0 }}>
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
          )}

          {/* Section 4: Actions */}
          <div style={{
            background: "#ffffff", borderRadius: 8, padding: 16,
            border: "1px solid #e5edf5", marginBottom: 12,
          }}>
            <div style={{ fontSize: 12, color: "#6366f1", fontWeight: 600, marginBottom: 8, letterSpacing: "0.5px" }}>
              操作
            </div>
            <div style={{ display: "flex", gap: 8 }}>
              <Button type="primary" icon={<ThunderboltOutlined />} onClick={handleQuickAnalysis}>
                一键分析
              </Button>
              {detail.matched_stocks?.[0] && (
                <Button icon={<LineChartOutlined />} onClick={() => handleViewStock(detail.matched_stocks[0].code)}>
                  查看K线
                </Button>
              )}
            </div>
          </div>

          <div style={{
            padding: "8px 12px", background: "#f0f0ff", borderRadius: 6,
            textAlign: "center", fontSize: 12, color: "#94a3b8",
          }}>
            以上为 AI 分析参考，不构成投资建议
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
