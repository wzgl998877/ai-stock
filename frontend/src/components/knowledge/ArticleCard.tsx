/** ArticleCard — 文章卡片（Stripe Design） */

import React from "react";
import { Typography, Tag } from "antd";
import { DeleteOutlined } from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import type { ArticleListItem } from "../../domain/types";
import { stripMarkdown } from "../../utils/stripMarkdown";

const { Text, Paragraph } = Typography;

interface Props {
  article: ArticleListItem;
  keyword?: string;
  highlightStockCode?: string;
  onDelete?: (id: string) => void;
}

const ArticleCard: React.FC<Props> = ({ article, keyword, highlightStockCode, onDelete }) => {
  const navigate = useNavigate();

  const handleClick = () => {
    navigate(`/knowledge/articles/${article.id}`);
  };

  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    onDelete?.(article.id);
  };

  // 高亮关键词
  const highlightText = (text: string) => {
    if (!keyword) return text;
    const parts = text.split(new RegExp(`(${keyword.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, "gi"));
    return parts.map((part, i) =>
      part.toLowerCase() === keyword.toLowerCase()
        ? <mark key={i} style={{ background: "rgba(83,58,253,0.15)", color: "#533afd", padding: "0 2px", borderRadius: 2 }}>{part}</mark>
        : part
    );
  };

  return (
    <div
      className="article-card-hoverable"
      onClick={handleClick}
      style={{
        background: "#ffffff",
        border: "1px solid #e5edf5",
        borderRadius: 6,
        padding: "16px 20px",
        cursor: "pointer",
        transition: "transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease",
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.boxShadow = "rgba(50,50,93,0.15) 0px 8px 24px -8px";
        e.currentTarget.style.borderColor = "#d6d9fc";
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.boxShadow = "none";
        e.currentTarget.style.borderColor = "#e5edf5";
      }}
    >
      {/* 标题行 */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 8 }}>
        <Text
          style={{
            fontSize: 15,
            fontWeight: 400,
            color: "#061b31",
            fontFeatureSettings: "'ss01' on",
            flex: 1,
            lineHeight: 1.4,
          }}
        >
          {highlightText(article.title)}
        </Text>
        {onDelete && (
          <DeleteOutlined
            className="article-delete-btn"
            onClick={handleDelete}
            style={{
              color: "#b0b8c4",
              fontSize: 14,
              marginLeft: 12,
              marginTop: 2,
              flexShrink: 0,
              opacity: 0,
              transition: "color 0.2s ease, opacity 0.2s ease",
            }}
          />
        )}
      </div>

      {/* 摘要 */}
      <Paragraph
        ellipsis={{ rows: 2 }}
        style={{
          fontSize: 13,
          color: "#64748d",
          margin: 0,
          marginBottom: 10,
          lineHeight: 1.5,
          fontFeatureSettings: "'ss01' on",
        }}
      >
        {article.highlight ? highlightText(stripMarkdown(article.highlight)) : stripMarkdown(article.summary || "")}
      </Paragraph>

      {/* 高亮股票标签 */}
      {highlightStockCode && article.stocks.some(s => s.code === highlightStockCode) && (
        <Tag
          style={{
            margin: 0,
            marginBottom: 8,
            borderRadius: 4,
            border: "1px solid #d6d9fc",
            background: "rgba(83,58,253,0.08)",
            color: "#533afd",
            fontSize: 11,
          }}
        >
          {article.stocks.find(s => s.code === highlightStockCode)?.name} ({highlightStockCode})
        </Tag>
      )}

      {/* 行业标签 + 日期 */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
          {article.industries.slice(0, 3).map((ind, idx) => (
            <Tag
              key={idx}
              style={{
                margin: 0,
                borderRadius: 4,
                border: "1px solid #d6d9fc",
                background: "rgba(83,58,253,0.05)",
                color: "#533afd",
                fontSize: 11,
              }}
            >
              {ind.name || ind.code}
            </Tag>
          ))}
        </div>
        <Text style={{ fontSize: 12, color: "#b0b8c4", flexShrink: 0, marginLeft: 12 }}>
          {new Date(article.created_at).toLocaleDateString("zh-CN")}
        </Text>
      </div>
    </div>
  );
};

export default ArticleCard;
