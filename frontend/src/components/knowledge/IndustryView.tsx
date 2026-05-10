/** IndustryView — 左侧行业列表 + 右侧文章列表 */

import React, { useState, useMemo } from "react";
import SidebarArticleList from "./SidebarArticleList";
import type { ArticleListItem } from "../../domain/types";

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
  const [searchValue, setSearchValue] = useState("");

  const filteredItems = useMemo(() => {
    if (!searchValue.trim()) return industries;
    const keyword = searchValue.toLowerCase();
    return industries.filter(
      (ind) =>
        ind.name.toLowerCase().includes(keyword) ||
        ind.code.toLowerCase().includes(keyword)
    );
  }, [industries, searchValue]);

  return (
    <SidebarArticleList
      sidebarTitle="行业分类"
      items={filteredItems}
      selectedCode={selectedIndustry}
      articles={articles}
      loading={loading}
      emptySidebarText="暂无匹配的行业"
      emptyArticlesTextSelected="该行业暂无文章"
      emptyArticlesTextUnselected="请选择行业查看文章"
      onSelectItem={onSelectIndustry}
      onDelete={onDelete}
      sidebarSearch={{
        value: searchValue,
        onChange: setSearchValue,
        placeholder: "搜索行业...",
      }}
    />
  );
};

export default IndustryView;
