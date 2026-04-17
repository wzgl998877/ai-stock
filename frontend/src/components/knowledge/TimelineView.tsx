/** TimelineView — 文章按日期倒序排列 */

import React from "react";
import { Typography, Empty, Spin } from "antd";
import ArticleCard from "./ArticleCard";
import type { ArticleListItem } from "../../domain/types";

const { Text } = Typography;

interface Props {
  articles: ArticleListItem[];
  loading: boolean;
  onDelete: (id: string) => void;
}

/** 按日期分组 */
function groupByDate(articles: ArticleListItem[]): Map<string, ArticleListItem[]> {
  const groups = new Map<string, ArticleListItem[]>();
  articles.forEach((a) => {
    const date = new Date(a.created_at).toLocaleDateString("zh-CN", {
      year: "numeric",
      month: "long",
      day: "numeric",
    });
    if (!groups.has(date)) groups.set(date, []);
    groups.get(date)!.push(a);
  });
  return groups;
}

const TimelineView: React.FC<Props> = ({ articles, loading, onDelete }) => {
  if (loading) {
    return (
      <div style={{ textAlign: "center", padding: 48 }}>
        <Spin />
      </div>
    );
  }

  if (articles.length === 0) {
    return <Empty description="知识库暂无文章" />;
  }

  const groups = groupByDate(articles);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      {Array.from(groups.entries()).map(([date, items]) => (
        <div key={date}>
          {/* 日期分组标题 */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 12,
              marginBottom: 12,
            }}
          >
            <Text
              style={{
                fontSize: 13,
                color: "#64748d",
                fontWeight: 400,
                fontFeatureSettings: "'ss01' on",
                flexShrink: 0,
              }}
            >
              {date}
            </Text>
            <div style={{ flex: 1, height: 1, background: "#e5edf5" }} />
          </div>

          {/* 文章列表 */}
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {items.map((article) => (
              <ArticleCard key={article.id} article={article} onDelete={onDelete} />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
};

export default TimelineView;
