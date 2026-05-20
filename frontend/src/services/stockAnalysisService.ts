/** 个股分析 API Service */
import api, { getAuthHeaders } from "./api";
import type { StockValidationResult, StockSSEEvent, AnalysisRecordDetail, AnalysisRecordListResponse } from "../domain/types";

const BASE = "/api/chat";
const ANALYSIS_BASE = "/api/analysis";

/** 验证股票代码/名称 */
export async function validateStock(keyword: string): Promise<StockValidationResult> {
  const res = await api.get(`${ANALYSIS_BASE}/validate-stock`, { params: { keyword } });
  return res.data;
}

/** 检查近期分析 */
export async function checkRecentAnalysis(stockCode: string, minutes: number = 5): Promise<{
  has_recent: boolean;
  article_id?: string;
  title?: string;
  created_at?: string;
}> {
  const res = await api.get(`${ANALYSIS_BASE}/stock-recent`, { params: { stock_code: stockCode, minutes } });
  return res.data;
}

/** 创建个股分析会话 */
export async function createStockAnalysisSession(config: {
  stock_code: string;
  stock_name: string;
  analysis_mode: string;
  title?: string;
}): Promise<{ id: string; title: string; created_at: string }> {
  const res = await api.post(`${BASE}/sessions`, {
    title: config.title || `${config.stock_name}深度分析`,
    event_type: "stock_analysis",
    config: {
      stock_code: config.stock_code,
      stock_name: config.stock_name,
      analysis_mode: config.analysis_mode,
    },
  });
  return res.data;
}

/** 流式发起个股分析 -- fetch + ReadableStream 解析 SSE */
export async function streamStockAnalysis(
  sessionId: string,
  config: {
    stock_code: string;
    stock_name: string;
    analysis_mode: string;
    content: string;
  },
  onEvent: (event: StockSSEEvent) => void,
  signal?: AbortSignal
): Promise<void> {
  const baseURL = import.meta.env.VITE_API_BASE_URL || "";
  const response = await fetch(`${baseURL}${BASE}/sessions/${sessionId}/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...getAuthHeaders() },
    body: JSON.stringify({
      content: config.content,
      event_type: "stock_analysis",
      config: {
        stock_code: config.stock_code,
        stock_name: config.stock_name,
        analysis_mode: config.analysis_mode,
      },
    }),
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
        const event: StockSSEEvent = JSON.parse(jsonStr);
        onEvent(event);
      } catch {
        // skip malformed
      }
    }
  }
}

/** 获取分析记录列表 */
export async function listAnalysisRecords(params?: {
  page?: number;
  pageSize?: number;
  status?: string;
  stockCode?: string;
}): Promise<AnalysisRecordListResponse> {
  const res = await api.get(`${ANALYSIS_BASE}/records`, {
    params: {
      page: params?.page || 1,
      page_size: params?.pageSize || 50,
      status: params?.status,
      stock_code: params?.stockCode,
    },
  });
  return res.data;
}

/** 获取单条分析记录详情 */
export async function getAnalysisRecord(recordId: string): Promise<AnalysisRecordDetail> {
  const res = await api.get(`${ANALYSIS_BASE}/records/${recordId}`);
  return res.data;
}

/** 获取分析进度（用于轮询恢复） */
export async function getAnalysisProgress(recordId: string) {
  const res = await api.get(`${ANALYSIS_BASE}/records/${recordId}/progress`);
  return res.data;
}
