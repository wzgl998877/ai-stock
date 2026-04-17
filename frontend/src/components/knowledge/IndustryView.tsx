/** IndustryView — 左侧行业列表 + 右侧文章列表 */

import React from "react";
import { Typography, Empty, Spin } from "antd";
import ArticleCard from "./ArticleCard";
import type { ArticleListItem } from "../../domain/types";

const { Text } = Typography;

interface Props {
  industries: { code: string; name: string; article_count: number }[];
  articles: ArticleListItem[];
  selectedIndustry: string | null;
  loading: boolean;
  onSelectIndustry: (code: string) => void;
  onDelete: (id: string) => void;
}

const IndustryView: React.FC<Props> = ({
  industries,
  articles,
  selectedIndustry,
  loading,
  onSelectIndustry,
  onDelete,
}) => {
  return (
    <div style={{ display: "flex", gap: 20 }}>
      {/* 左侧：行业列表 */}
      <div
        style={{
          width: 200,
          flexShrink: 0,
          borderRight: "1px solid #e5edf5",
          paddingRight: 16,
        }}
      >
        <Text
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
          行业分类
        </Text>
        {industries.length === 0 ? (
          <Text style={{ fontSize: 13, color: "#b0b8c4" }}>暂无数据</Text>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
            {industries.map((ind) => (
              <div
                key={ind.code}
                onClick={() => onSelectIndustry(ind.code)}
                style={{
                  padding: "8px 12px",
                  borderRadius: 4,
                  cursor: "pointer",
                  background: selectedIndustry === ind.code ? "rgba(83,58,253,0.08)" : "transparent",
                  borderLeft: selectedIndustry === ind.code ? "2px solid #533afd" : "2px solid transparent",
                  transition: "all 0.15s ease",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <Text
                    style={{
                      fontSize: 13,
                      color: selectedIndustry === ind.code ? "#533afd" : "#061b31",
                      fontWeight: selectedIndustry === ind.code ? 400 : 300,
                      fontFeatureSettings: "'ss01' on",
                    }}
                  >
                    {ind.name}
                  </Text>
                  <Text style={{ fontSize: 11, color: "#b0b8c4" }}>{ind.article_count}</Text>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 右侧：文章列表 */}
      <div style={{ flex: 1 }}>
        {loading ? (
          <div style={{ textAlign: "center", padding: 48 }}>
            <Spin />
          </div>
        ) : articles.length === 0 ? (
          <Empty description={selectedIndustry ? "该行业暂无文章" : "请选择行业查看文章"} />
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

export default IndustryView;
