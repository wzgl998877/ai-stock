/** useKnowledge — 知识库业务逻辑编排 */

import { useCallback, useEffect } from "react";
import { useKnowledgeStore } from "../store/knowledgeStore";
import * as knowledgeService from "../services/knowledgeService";

export function useKnowledge() {
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
    setArticles,
    setLoading,
    setPage,
    setIndustries,
    setStocks,
  } = useKnowledgeStore();

  // 加载文章列表
  const loadArticles = useCallback(async () => {
    setLoading(true);
    try {
      let data;
      if (searchKeyword.trim()) {
        data = await knowledgeService.searchArticles(searchKeyword.trim(), page, pageSize);
      } else {
        data = await knowledgeService.getArticles({
          view,
          industry: view === "industry" ? selectedIndustry ?? undefined : undefined,
          stock_code: view === "stock" ? selectedStock ?? undefined : undefined,
          page,
          page_size: pageSize,
        });
      }
      setArticles(data.items, data.total);
    } catch (err) {
      console.error("加载文章失败:", err);
    } finally {
      setLoading(false);
    }
  }, [view, selectedIndustry, selectedStock, searchKeyword, page, pageSize, setArticles, setLoading]);

  // 加载行业列表
  const loadIndustries = useCallback(async () => {
    try {
      const data = await knowledgeService.getIndustries();
      setIndustries(data.industries);
    } catch {
      // 静默处理
    }
  }, [setIndustries]);

  // 加载股票列表
  const loadStocks = useCallback(async () => {
    try {
      const data = await knowledgeService.getWatchlistStocks();
      setStocks(data.stocks);
    } catch {
      // 静默处理
    }
  }, [setStocks]);

  // 删除文章
  const handleDelete = useCallback(async (id: string) => {
    await knowledgeService.deleteArticle(id);
    await loadArticles();
  }, [loadArticles]);

  // 视图/筛选变化时重新加载
  useEffect(() => {
    loadArticles();
  }, [loadArticles]);

  return {
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
    loadArticles,
    loadIndustries,
    loadStocks,
    handleDelete,
    setPage,
    setView: useKnowledgeStore.getState().setView,
    setSelectedIndustry: useKnowledgeStore.getState().setSelectedIndustry,
    setSelectedStock: useKnowledgeStore.getState().setSelectedStock,
    setSearchKeyword: useKnowledgeStore.getState().setSearchKeyword,
  };
}
