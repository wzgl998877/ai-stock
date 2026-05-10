/** StockView — 左侧股票列表 + 右侧文章列表 */

import React, { useState, useMemo } from "react";
import { Typography } from "antd";
import SidebarArticleList, { SidebarItem } from "./SidebarArticleList";
import AddToWatchlistButton from "../stock/AddToWatchlistButton";
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
  const [searchValue, setSearchValue] = useState("");

  const filteredItems = useMemo(() => {
    if (!searchValue.trim()) return stocks;
    const keyword = searchValue.toLowerCase();
    return stocks.filter(
      (s) =>
        s.name.toLowerCase().includes(keyword) ||
        s.code.toLowerCase().includes(keyword)
    );
  }, [stocks, searchValue]);

  const sidebarItems: SidebarItem[] = filteredItems.map((s) => ({
    code: s.code,
    name: s.name,
    article_count: s.article_count,
  }));

  const renderStockExtra = (item: SidebarItem) => (
    <div style={{ marginTop: 4, display: "flex", gap: 4, alignItems: "center" }}>
      <Text style={{ fontSize: 11, color: "#b0b8c4" }}>{item.code}</Text>
      <AddToWatchlistButton stockCode={item.code} stockName={item.name} />
    </div>
  );

  return (
    <SidebarArticleList
      sidebarTitle="股票"
      items={sidebarItems}
      selectedCode={selectedStock}
      articles={articles}
      loading={loading}
      emptySidebarText="暂无匹配的股票"
      emptyArticlesTextSelected="该股票暂无关联文章"
      emptyArticlesTextUnselected="请选择股票查看关联文章"
      onSelectItem={onSelectStock}
      onDelete={onDelete}
      renderSidebarItemExtra={renderStockExtra}
      sidebarSearch={{
        value: searchValue,
        onChange: setSearchValue,
        placeholder: "搜索股票名称/代码...",
      }}
    />
  );
};

export default StockView;
