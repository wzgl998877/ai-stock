/** StockView — 左侧股票列表 + 右侧文章列表 */

import React from "react";
import { Typography, Empty, Spin } from "antd";
import ArticleCard from "./ArticleCard";
import type { ArticleListItem } from "../../domain/types";

const { Text } = Typography;

interface Props {
  stocks: { code: string; name: string; article_count: number }[];
  articles: ArticleListItem[];
  selectedStock: string | null;
  loading: boolean;
  onSelectStock: (code: string) => void;
  onDelete: (id: string) => void;
}

const StockView: React.FC<Props> = ({
  stocks,
  articles,
  selectedStock,
  loading,
  onSelectStock,
  onDelete,
}) => {
  return (
    <div style={{ display: "flex", gap: 20 }}>
      {/* 左侧：股票列表 */}
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
          提及股票
        </Text>
        {stocks.length === 0 ? (
          <div style={{ padding: "12px 0" }}>
            <Text style={{ fontSize: 13, color: "#b0b8c4" }}>
              暂无数据，分析中提及的股票会自动收录
            </Text>
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
            {stocks.map((s) => (
              <div
                key={s.code}
                onClick={() => onSelectStock(s.code)}
                style={{
                  padding: "8px 12px",
                  borderRadius: 4,
                  cursor: "pointer",
                  background: selectedStock === s.code ? "rgba(83,58,253,0.08)" : "transparent",
                  borderLeft: selectedStock === s.code ? "2px solid #533afd" : "2px solid transparent",
                  transition: "all 0.15s ease",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <Text
                    style={{
                      fontSize: 13,
                      color: selectedStock === s.code ? "#533afd" : "#061b31",
                      fontWeight: selectedStock === s.code ? 400 : 300,
                      fontFeatureSettings: "'ss01' on",
                    }}
                  >
                    {s.name}
                  </Text>
                  <Text style={{ fontSize: 11, color: "#b0b8c4" }}>{s.article_count}</Text>
                </div>
                <Text style={{ fontSize: 11, color: "#b0b8c4" }}>{s.code}</Text>
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
          <Empty description={selectedStock ? "该股票暂无关联文章" : "请选择股票查看关联文章"} />
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

export default StockView;
