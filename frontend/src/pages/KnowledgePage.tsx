/** KnowledgePage — 知识库浏览页面（Stripe Design） */

import React, { useEffect } from "react";
import { Typography, Tabs, Pagination, Empty as AntEmpty } from "antd";
import { useKnowledge } from "../application/useKnowledge";
import { useKnowledgeStore, ViewMode } from "../store/knowledgeStore";
import SearchBar from "../components/knowledge/SearchBar";
import TimelineView from "../components/knowledge/TimelineView";
import IndustryView from "../components/knowledge/IndustryView";
import StockView from "../components/knowledge/StockView";

const { Text } = Typography;

const KnowledgePage: React.FC = () => {
  const {
    view,
    selectedIndustry,
    selectedStock,
    searchKeyword,
    articles,
    total,
    page,
    pageSize,
    loading,
    industries,
    stocks,
    handleDelete,
    setPage,
    loadIndustries,
    loadStocks,
  } = useKnowledge();

  const setView = useKnowledgeStore((s) => s.setView);
  const setSelectedIndustry = useKnowledgeStore((s) => s.setSelectedIndustry);
  const setSelectedStock = useKnowledgeStore((s) => s.setSelectedStock);
  const setSearchKeyword = useKnowledgeStore((s) => s.setSearchKeyword);

  // 切换 tab 时，行业/股票视图自动选中第一项
  const handleTabChange = (key: string) => {
    setView(key as ViewMode);
    if (key === "industry") {
      const list = useKnowledgeStore.getState().industries;
      if (list.length > 0) setSelectedIndustry(list[0].code);
    } else if (key === "stock") {
      const list = useKnowledgeStore.getState().stocks;
      if (list.length > 0) setSelectedStock(list[0].code);
    }
  };

  // 加载行业和股票列表
  useEffect(() => {
    loadIndustries();
    loadStocks();
  }, [loadIndustries, loadStocks]);

  const tabItems = [
    {
      key: "timeline",
      label: "时间线",
    },
    {
      key: "industry",
      label: "行业",
    },
    {
      key: "stock",
      label: "股票",
    },
  ];

  return (
    <div
      className="knowledge-page"
      style={{
        height: "100vh",
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
      }}
    >
      {/* 页头 */}
      <div
        className="knowledge-header"
        style={{
          flexShrink: 0,
          borderBottom: "1px solid #e5edf5",
          padding: "20px 32px 16px",
          background: "#ffffff",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
          <div>
            <Text
              style={{
                fontSize: 22,
                fontWeight: 300,
                color: "#061b31",
                fontFeatureSettings: "'ss01' on",
                letterSpacing: "-0.22px",
              }}
            >
              知识库
            </Text>
            <Text
              style={{
                fontSize: 13,
                color: "#64748d",
                marginLeft: 12,
                fontFeatureSettings: "'ss01' on",
              }}
            >
              共 {total} 篇分析
            </Text>
          </div>
          <SearchBar value={searchKeyword} onChange={setSearchKeyword} />
        </div>

        <Tabs
          activeKey={view}
          onChange={handleTabChange}
          items={tabItems}
          className="knowledge-tabs"
          style={{ marginBottom: 0 }}
        />

        {/* 搜索提示 */}
        {searchKeyword && (
          <div
            style={{
              marginTop: 12,
              padding: "8px 12px",
              background: "rgba(83,58,253,0.05)",
              borderRadius: 4,
              display: "flex",
              alignItems: "center",
              gap: 6,
            }}
          >
            <span style={{ fontSize: 14 }}>🔍</span>
            <Text style={{ fontSize: 13, color: "#533afd" }}>
              正在全库搜索 &quot;{searchKeyword}&quot; · 匹配标题和正文
            </Text>
          </div>
        )}
      </div>

      {/* 内容区域 */}
      <div
        className="knowledge-content"
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "24px 32px",
          background: "#f7f9fc",
        }}
      >
        {!loading && view === "timeline" && articles.length === 0 && !searchKeyword ? (
          <div style={{ textAlign: "center", padding: "80px 0" }}>
            <AntEmpty description="还没有保存任何分析" />
            <Text style={{ fontSize: 13, color: "#64748d", marginTop: 8, display: "block" }}>
              去分析页面生成并保存第一篇分析报告
            </Text>
          </div>
        ) : (
          <>
            {view === "timeline" && (
              <TimelineView articles={articles} loading={loading} onDelete={handleDelete} total={total} pageSize={pageSize} />
            )}
            {view === "industry" && (
              <IndustryView
                industries={industries}
                articles={articles}
                selectedIndustry={selectedIndustry}
                loading={loading}
                onSelectIndustry={(code) => setSelectedIndustry(code)}
                onDelete={handleDelete}
              />
            )}
            {view === "stock" && (
              <StockView
                stocks={stocks}
                articles={articles}
                selectedStock={selectedStock}
                loading={loading}
                onSelectStock={(code) => setSelectedStock(code)}
                onDelete={handleDelete}
              />
            )}
          </>
        )}
      </div>

      {/* 分页 */}
      {total > pageSize && (
        <div
          className="knowledge-pagination"
          style={{
            flexShrink: 0,
            borderTop: "1px solid #e5edf5",
            padding: "12px 32px",
            background: "#f7f9fc",
            display: "flex",
            justifyContent: "center",
          }}
        >
          <Pagination
            current={page}
            total={total}
            pageSize={pageSize}
            onChange={(p) => setPage(p)}
            showSizeChanger={false}
            size="small"
          />
        </div>
      )}
    </div>
  );
};

export default KnowledgePage;
