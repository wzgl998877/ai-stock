/** ArticleCard — 文章卡片（Stripe Design） */

import React from "react";
import { Typography, Tag } from "antd";
import { DeleteOutlined, SearchOutlined } from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import type { ArticleListItem } from "../../domain/types";
import StockCodeLink from "../common/StockCodeLink";
import { stripMarkdown } from "../../utils/stripMarkdown";

const { Text, Paragraph } = Typography;

interface Props {
  article: ArticleListItem;
  keyword?: string;
  onDelete?: (id: string) => void;
}

const ArticleCard: React.FC<Props> = ({ article, keyword, onDelete }) => {
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

  const eventTypeLabels: Record<string, string> = {
    geopolitical: "地缘",
    policy: "政策",
    earnings: "财报",
    supply_chain: "产业链",
    other: "其他",
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
            fontSize: 16,
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
          fontSize: 14,
          color: "#64748d",
          margin: 0,
          marginBottom: 12,
          lineHeight: 1.5,
          fontFeatureSettings: "'ss01' on",
        }}
      >
        {article.highlight ? highlightText(stripMarkdown(article.highlight)) : stripMarkdown(article.summary || "")}
      </Paragraph>

      {/* 关联股票 */}
      {article.stocks.length > 0 && (
        <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 10, flexWrap: "wrap" }}>
          <SearchOutlined style={{ fontSize: 12, color: "#b0b8c4" }} />
          {article.stocks.slice(0, 6).map((s, idx) => (
            <StockCodeLink key={idx} code={s.code} name={s.name} />
          ))}
          {article.stocks.length > 6 && (
            <Text style={{ fontSize: 12, color: "#b0b8c4" }}>+{article.stocks.length - 6}</Text>
          )}
        </div>
      )}

      {/* 底部：事件类型 + 行业标签 + 日期 */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div style={{ display: "flex", gap: 4, alignItems: "center", flexWrap: "wrap" }}>
          <Tag
            style={{
              margin: 0,
              borderRadius: 4,
              border: "1px solid #e5edf5",
              background: "#f6f9fc",
              color: "#273951",
              fontSize: 11,
            }}
          >
            {eventTypeLabels[article.event_type] || article.event_type}
          </Tag>
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
