/** 知识库 API Service */

import api from "./api";
import type { ArticleListResponseDTO, ArticleDetailDTO } from "../domain/types";

const BASE = "/api/knowledge";

/** 获取知识库文章列表 */
export async function getArticles(params: {
  view?: string;
  industry?: string;
  stock_code?: string;
  page?: number;
  page_size?: number;
}): Promise<ArticleListResponseDTO> {
  const res = await api.get(`${BASE}/articles`, { params });
  return res.data;
}

/** 获取文章详情 */
export async function getArticleDetail(id: string): Promise<ArticleDetailDTO> {
  const res = await api.get(`${BASE}/articles/${id}`);
  return res.data;
}

/** 删除文章 */
export async function deleteArticle(id: string): Promise<void> {
  await api.delete(`${BASE}/articles/${id}`);
}

/** 获取有文章的行业列表 */
export async function getIndustries(): Promise<{
  industries: { code: string; name: string; article_count: number }[];
}> {
  const res = await api.get(`${BASE}/industries`);
  return res.data;
}

/** 获取有文章的股票列表 */
export async function getWatchlistStocks(): Promise<{
  stocks: { code: string; name: string; article_count: number }[];
}> {
  const res = await api.get(`${BASE}/watchlist-stocks`);
  return res.data;
}

/** 全文搜索知识库 */
export async function searchArticles(
  q: string,
  page = 1,
  pageSize = 20
): Promise<ArticleListResponseDTO> {
  const res = await api.get(`${BASE}/search`, {
    params: { q, page, page_size: pageSize },
  });
  return res.data;
}
