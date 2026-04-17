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

  // 加载行业和股票列表
  useEffect(() => {
    loadIndustries();
    loadStocks();
  }, [loadIndustries, loadStocks]);

  const tabItems = [
    {
      key: "timeline",
      label: "时间线",
      children: (
        <TimelineView articles={articles} loading={loading} onDelete={handleDelete} />
      ),
    },
    {
      key: "industry",
      label: "行业",
      children: (
        <IndustryView
          industries={industries}
          articles={articles}
          selectedIndustry={selectedIndustry}
          loading={loading}
          onSelectIndustry={(code) => setSelectedIndustry(code)}
          onDelete={handleDelete}
        />
      ),
    },
    {
      key: "stock",
      label: "股票",
      children: (
        <StockView
          stocks={stocks}
          articles={articles}
          selectedStock={selectedStock}
          loading={loading}
          onSelectStock={(code) => setSelectedStock(code)}
          onDelete={handleDelete}
        />
      ),
    },
  ];

  return (
    <div
      style={{
        height: "100vh",
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
      }}
    >
      {/* 页头 */}
      <div
        style={{
          flexShrink: 0,
          borderBottom: "1px solid #e5edf5",
          padding: "20px 32px 0",
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
          onChange={(key) => setView(key as ViewMode)}
          items={tabItems}
          style={{ marginBottom: 0 }}
        />
      </div>

      {/* 内容区域 */}
      <div
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "20px 32px",
          background: "#ffffff",
        }}
      >
        {!loading && articles.length === 0 && !searchKeyword ? (
          <div style={{ textAlign: "center", padding: "80px 0" }}>
            <AntEmpty description="还没有保存任何分析" />
            <Text style={{ fontSize: 13, color: "#64748d", marginTop: 8, display: "block" }}>
              去分析页面生成并保存第一篇分析报告
            </Text>
          </div>
        ) : null}
      </div>

      {/* 分页 */}
      {total > pageSize && (
        <div
          style={{
            flexShrink: 0,
            borderTop: "1px solid #e5edf5",
            padding: "12px 32px",
            background: "#ffffff",
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
