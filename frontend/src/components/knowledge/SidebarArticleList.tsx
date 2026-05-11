/** SidebarArticleList — 侧边栏 + 文章列表共用组件 */

import React, { useState } from "react";
import { Typography, Empty, Input } from "antd";
import ArticleCard from "./ArticleCard";
import type { ArticleListItem } from "../../domain/types";

const { Text } = Typography;

export interface SidebarItem {
  code: string;
  name: string;
  article_count: number;
  extra?: React.ReactNode;
}

interface Props {
  sidebarTitle: string;
  items: SidebarItem[];
  selectedCode: string | null;
  articles: ArticleListItem[];
  loading: boolean;
  emptySidebarText?: string;
  emptyArticlesTextSelected?: string;
  emptyArticlesTextUnselected?: string;
  onSelectItem: (code: string) => void;
  onDelete: (id: string) => void;
  renderSidebarItemExtra?: (item: SidebarItem, hovered: boolean) => React.ReactNode;
  sidebarSearch?: { value: string; onChange: (val: string) => void; placeholder?: string };
}

const SidebarArticleList: React.FC<Props> = ({
  sidebarTitle,
  items,
  selectedCode,
  articles,
  loading,
  emptySidebarText = "暂无数据",
  emptyArticlesTextSelected = "暂无文章",
  emptyArticlesTextUnselected = "请选择查看文章",
  onSelectItem,
  onDelete,
  renderSidebarItemExtra,
  sidebarSearch,
}) => {
  const [hoveredCode, setHoveredCode] = useState<string | null>(null);

  return (
    <div style={{ display: "flex", gap: 20 }}>
      {/* 左侧：列表 */}
      <div
        style={{
          width: 240,
          flexShrink: 0,
          borderRight: "1px solid #e5edf5",
          paddingRight: 16,
          maxHeight: "calc(100vh - 200px)",
          overflowY: "auto",
        }}
      >
        <Text
          className="sidebar-section-title"
          style={{
            fontSize: 12,
            color: "#64748d",
            fontWeight: 400,
            textTransform: "uppercase",
            letterSpacing: "0.5px",
            display: "block",
            marginBottom: 12,
          }}
        >
          {sidebarTitle}
        </Text>
        {sidebarSearch && (
          <div style={{ marginBottom: 8 }}>
            <Input.Search
              size="small"
              variant="borderless"
              value={sidebarSearch.value}
              onChange={(e) => sidebarSearch.onChange(e.target.value)}
              placeholder={sidebarSearch.placeholder || "搜索..."}
              style={{ background: "#f7f9fc", borderRadius: 4 }}
            />
          </div>
        )}
        {items.length === 0 ? (
          <Text style={{ fontSize: 13, color: "#b0b8c4" }}>{emptySidebarText}</Text>
        ) : (
          <div className="sidebar-list" style={{ display: "flex", flexDirection: "column", gap: 2 }}>
            {items.map((item) => {
              const isActive = selectedCode === item.code;
              const isHovered = hoveredCode === item.code;
              return (
                <div
                  key={item.code}
                  className="sidebar-item"
                  onClick={() => onSelectItem(item.code)}
                  onMouseEnter={() => setHoveredCode(item.code)}
                  onMouseLeave={() => setHoveredCode(null)}
                  style={{
                    padding: "8px 12px",
                    borderRadius: 4,
                    cursor: "pointer",
                    background: isActive ? "rgba(83,58,253,0.08)" : isHovered ? "#f7f9fc" : "transparent",
                    borderLeft: isActive ? "2px solid #533afd" : "2px solid transparent",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <Text
                      style={{
                        fontSize: 14,
                        color: isActive ? "#533afd" : "#061b31",
                        fontWeight: isActive ? 400 : 300,
                        fontFeatureSettings: "'ss01' on",
                      }}
                    >
                      {item.name}
                    </Text>
                    <Text style={{ fontSize: 11, color: "#b0b8c4" }}>{item.article_count}</Text>
                  </div>
                  {renderSidebarItemExtra ? renderSidebarItemExtra(item, isHovered) : item.extra}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* 右侧：文章列表 */}
      <div style={{ flex: 1 }}>
        {loading ? (
          <div className="timeline-loading" style={{ textAlign: "center", padding: "32px 0" }}>
            <div className="skeleton-card" />
            <div className="skeleton-card" />
            <div className="skeleton-card" />
          </div>
        ) : articles.length === 0 ? (
          <Empty description={selectedCode ? emptyArticlesTextSelected : emptyArticlesTextUnselected} />
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {articles.map((article) => (
              <ArticleCard key={article.id} article={article} onDelete={onDelete} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default SidebarArticleList;
