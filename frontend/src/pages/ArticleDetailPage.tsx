/** ArticleDetailPage — 文章详情页（Stripe Design） */

import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Typography, Spin, Button, Tag, message, Popconfirm } from "antd";
import { ArrowLeftOutlined, DeleteOutlined } from "@ant-design/icons";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { getArticleDetail, deleteArticle } from "../services/knowledgeService";
import StockCodeLink from "../components/common/StockCodeLink";
import type { ArticleDetail } from "../domain/types";

const { Text, Paragraph } = Typography;

const ArticleDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [article, setArticle] = useState<ArticleDetail | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    getArticleDetail(id)
      .then(setArticle)
      .catch(() => message.error("加载失败"))
      .finally(() => setLoading(false));
  }, [id]);

  const handleDelete = async () => {
    if (!id) return;
    try {
      await deleteArticle(id);
      message.success("已删除");
      navigate("/knowledge");
    } catch {
      message.error("删除失败");
    }
  };

  if (loading) {
    return (
      <div style={{ textAlign: "center", padding: 80 }}>
        <Spin size="large" />
      </div>
    );
  }

  if (!article) {
    return (
      <div style={{ textAlign: "center", padding: 80 }}>
        <Text style={{ color: "#64748d" }}>文章不存在或已删除</Text>
        <br />
        <Button type="link" onClick={() => navigate("/knowledge")}>
          返回知识库
        </Button>
      </div>
    );
  }

  const eventTypeLabels: Record<string, string> = {
    geopolitical: "地缘政治",
    policy: "政策法规",
    earnings: "财报季报",
    supply_chain: "产业链分析",
    other: "其他",
  };

  return (
    <div
      style={{
        maxWidth: 860,
        margin: "0 auto",
        padding: "24px 32px 80px",
        minHeight: "100vh",
      }}
    >
      {/* 返回导航 */}
      <div style={{ marginBottom: 24 }}>
        <Button
          type="text"
          icon={<ArrowLeftOutlined />}
          onClick={() => navigate("/knowledge")}
          style={{ color: "#64748d", padding: "4px 0" }}
        >
          <span style={{ fontFeatureSettings: "'ss01' on" }}>返回知识库</span>
        </Button>
      </div>

      {/* 文章头部 */}
      <div style={{ marginBottom: 24 }}>
        <h1
          style={{
            fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
            fontWeight: 300,
            fontSize: 26,
            color: "#061b31",
            letterSpacing: "-0.26px",
            fontFeatureSettings: "'ss01' on",
            margin: 0,
            marginBottom: 12,
            lineHeight: 1.3,
          }}
        >
          {article.title}
        </h1>

        {/* 摘要 */}
        {article.summary && (
          <Paragraph
            style={{
              fontSize: 15,
              color: "#64748d",
              lineHeight: 1.6,
              margin: 0,
              marginBottom: 16,
              fontFeatureSettings: "'ss01' on",
            }}
          >
            {article.summary}
          </Paragraph>
        )}

        {/* 元信息标签行 */}
        <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
          <Tag
            style={{
              borderRadius: 4,
              border: "1px solid #e5edf5",
              background: "#f6f9fc",
              color: "#273951",
              fontSize: 12,
            }}
          >
            {eventTypeLabels[article.event_type] || article.event_type}
          </Tag>
          {article.industries.map((ind, idx) => (
            <Tag
              key={idx}
              style={{
                borderRadius: 4,
                border: "1px solid #d6d9fc",
                background: "rgba(83,58,253,0.05)",
                color: "#533afd",
                fontSize: 12,
              }}
            >
              {ind.name || ind.code}
            </Tag>
          ))}
          <Text style={{ fontSize: 12, color: "#b0b8c4", marginLeft: 4 }}>
            {new Date(article.created_at).toLocaleDateString("zh-CN")}
          </Text>
        </div>
      </div>

      {/* 正文内容 */}
      <div
        style={{
          background: "#ffffff",
          border: "1px solid #e5edf5",
          borderRadius: 6,
          padding: 32,
          boxShadow: "rgba(23,23,23,0.06) 0px 3px 6px",
          marginBottom: 24,
        }}
      >
        <div className="markdown-body">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{article.content}</ReactMarkdown>
        </div>
      </div>

      {/* 股票引用区域 */}
      {article.stocks.length > 0 && (
        <div
          style={{
            background: "#f6f9fc",
            border: "1px solid #e5edf5",
            borderRadius: 6,
            padding: 16,
            marginBottom: 24,
          }}
        >
          <Text
            style={{
              fontSize: 13,
              color: "#273951",
              fontWeight: 400,
              display: "block",
              marginBottom: 8,
              fontFeatureSettings: "'ss01' on",
            }}
          >
            提及股票
          </Text>
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
            {article.stocks.map((s, idx) => (
              <StockCodeLink key={idx} code={s.code} name={s.name} />
            ))}
          </div>
        </div>
      )}

      {/* 底部操作 */}
      <div style={{ display: "flex", justifyContent: "flex-end" }}>
        <Popconfirm
          title="确认删除？"
          description="删除后不可恢复"
          onConfirm={handleDelete}
          okText="确认"
          cancelText="取消"
        >
          <Button
            icon={<DeleteOutlined />}
            danger
            style={{ borderRadius: 4 }}
          >
            删除文章
          </Button>
        </Popconfirm>
      </div>
    </div>
  );
};

export default ArticleDetailPage;
