/** TimelineView — 文章按日期倒序排列 */

import React from "react";
import { Typography, Empty, Skeleton } from "antd";
import ArticleCard from "./ArticleCard";
import type { ArticleListItem } from "../../domain/types";

const { Text } = Typography;

interface Props {
  articles: ArticleListItem[];
  loading: boolean;
  onDelete: (id: string) => void;
  total?: number;
  pageSize?: number;
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

const TimelineView: React.FC<Props> = ({ articles, loading, onDelete, total, pageSize }) => {
  if (loading) {
    return (
      <div className="timeline-loading" style={{ textAlign: "center", padding: "32px 0" }}>
        <Skeleton active avatar paragraph={{ rows: 2 }} title={false} />
        <div style={{ height: 16 }} />
        <Skeleton active avatar paragraph={{ rows: 2 }} title={false} />
        <div style={{ height: 16 }} />
        <Skeleton active avatar paragraph={{ rows: 2 }} title={false} />
      </div>
    );
  }

  if (articles.length === 0) {
    return (
      <div className="timeline-empty" style={{ textAlign: "center", padding: "48px 0" }}>
        <Empty description="知识库暂无文章" />
        <Text style={{ fontSize: 13, color: "#64748d", marginTop: 8, display: "block" }}>
          去分析页面生成并保存第一篇分析报告
        </Text>
      </div>
    );
  }

  const groups = groupByDate(articles);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      {Array.from(groups.entries()).map(([date, items]) => (
        <div key={date} style={{ position: "relative", paddingLeft: 16 }}>
          {/* 时间线圆点 */}
          <div
            style={{
              position: "absolute",
              left: 0,
              top: 4,
              width: 10,
              height: 10,
              borderRadius: "50%",
              background: "#533afd",
              border: "2px solid #fff",
              boxShadow: "0 0 0 2px rgba(83,58,253,0.2)",
            }}
          />
          {/* 时间线竖线 */}
          <div
            style={{
              position: "absolute",
              left: 4,
              top: 18,
              bottom: -(items === Array.from(groups.entries()).pop()?.[1] ? 0 : 6),
              width: 2,
              background: "linear-gradient(to bottom, rgba(83,58,253,0.3), rgba(83,58,253,0.05))",
            }}
          />

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
              className="timeline-date-title"
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
            <span
              style={{
                fontSize: 11,
                color: "#b0b8c4",
                flexShrink: 0,
              }}
            >
              {items.length} 篇
            </span>
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

      {/* 分页提示 */}
      {total != null && pageSize != null && (
        <div style={{ textAlign: "center", paddingTop: 8 }}>
          <Text style={{ fontSize: 12, color: "#b0b8c4" }}>
            当前页显示 {articles.length} 篇，共 {total} 篇
          </Text>
        </div>
      )}
    </div>
  );
};

export default TimelineView;
