/** 分析相关 API Service */

import api, { getAuthHeaders } from "./api";
import type {
  SSEEvent,
  ArticleListResponseDTO,
  ArticleDetailDTO,
  SimilarArticleDTO,
} from "../domain/types";

const BASE = "/api/analysis";
const KNOWLEDGE_BASE = "/api/knowledge";

/**
 * 流式分析 — fetch + ReadableStream 解析 SSE
 */
export async function streamAnalysis(
  eventType: string,
  question: string,
  onEvent: (event: SSEEvent) => void,
  signal?: AbortSignal
): Promise<void> {
  const baseURL = import.meta.env.VITE_API_BASE_URL || "";
  const response = await fetch(`${baseURL}${BASE}/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...getAuthHeaders() },
    body: JSON.stringify({ event_type: eventType, question }),
    signal,
  });

  if (!response.ok) {
    const err = await response.json().catch(() => null);
    throw new Error(err?.detail?.message || `请求失败: ${response.status}`);
  }

  const reader = response.body?.getReader();
  if (!reader) throw new Error("ReadableStream 不可用");

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed.startsWith("data: ")) continue;
      const jsonStr = trimmed.slice(6);
      try {
        const event: SSEEvent = JSON.parse(jsonStr);
        onEvent(event);
      } catch {
        // skip malformed
      }
    }
  }
}

/**
 * 保存文章到知识库
 */
export async function saveArticle(data: {
  title: string;
  summary: string;
  content: string;
  event_type: string;
  raw_input: string;
  industry_codes: string[];
  stock_refs: { code: string; name: string }[];
  chain_table: unknown[] | null;
}) {
  const res = await api.post(`${BASE}/articles`, data);
  return res.data;
}

/**
 * 相似问题检测
 */
export async function checkSimilarity(
  question: string,
  topK = 3
): Promise<{ similar_articles: SimilarArticleDTO[] }> {
  const res = await api.post(`${BASE}/similarity`, {
    question,
    top_k: topK,
  });
  return res.data;
}

/**
 * 获取知识库文章列表
 */
export async function getArticles(params: {
  view?: string;
  industry?: string;
  stock_code?: string;
  keyword?: string;
  page?: number;
  page_size?: number;
}): Promise<ArticleListResponseDTO> {
  const res = await api.get(`${KNOWLEDGE_BASE}/articles`, { params });
  return res.data;
}

/**
 * 获取文章详情
 */
export async function getArticleDetail(id: string): Promise<ArticleDetailDTO> {
  const res = await api.get(`${KNOWLEDGE_BASE}/articles/${id}`);
  return res.data;
}

/**
 * 删除文章
 */
export async function deleteArticle(id: string): Promise<void> {
  await api.delete(`${KNOWLEDGE_BASE}/articles/${id}`);
}

/**
 * 获取行业列表
 */
export async function getIndustries(): Promise<{
  industries: { name: string; article_count: number }[];
}> {
  const res = await api.get(`${KNOWLEDGE_BASE}/industries`);
  return res.data;
}

/**
 * 搜索知识库
 */
export async function searchArticles(
  q: string,
  page = 1,
  pageSize = 20
): Promise<ArticleListResponseDTO> {
  const res = await api.get(`${KNOWLEDGE_BASE}/search`, {
    params: { q, page, page_size: pageSize },
  });
  return res.data;
}

/**
 * 从分析内容中提取行业标签（保存知识库兜底方案）
 */
export async function extractIndustries(
  content: string,
  eventType: string
): Promise<{ industries: string[] }> {
  const res = await api.post(`${BASE}/extract-industries`, {
    content,
    event_type: eventType,
  });
  return res.data;
}
