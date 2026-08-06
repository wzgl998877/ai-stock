/**
 * 通用 SSE 流式请求工具（T030）。
 *
 * 复用 ``stockAnalysisService`` 的 fetch + ReadableStream 范式，但解析标准 SSE
 * 报文（``event:`` + ``data:`` 行），供缠论重算 / 回测等 SSE 端点共用。
 *
 * 所有请求经 ``getAuthHeaders()`` 携带用户头（前端不直连网络外的鉴权信息）。
 */

import { getAuthHeaders } from "./api";

export interface SSEMessage {
  event: string;
  data: unknown;
}

export interface StreamSSEOptions {
  url: string;
  method?: "GET" | "POST";
  body?: unknown;
  signal?: AbortSignal;
  onEvent: (msg: SSEMessage) => void;
}

/**
 * 发起 SSE 流式请求，逐条解析 ``event:/data:`` 块回调 ``onEvent``。
 *
 * @throws 当 HTTP 非 2xx 时抛出含后端 detail 的 Error
 */
export async function streamSSE(opts: StreamSSEOptions): Promise<void> {
  const baseURL = import.meta.env.VITE_API_BASE_URL || "";
  const headers: Record<string, string> = { ...getAuthHeaders() };
  const method = opts.method || (opts.body ? "POST" : "GET");
  if (opts.body !== undefined) {
    headers["Content-Type"] = "application/json";
  }

  const response = await fetch(`${baseURL}${opts.url}`, {
    method,
    headers,
    body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
    signal: opts.signal,
  });

  if (!response.ok) {
    const err = await response.json().catch(() => null);
    throw new Error(err?.detail || err?.message || `请求失败: ${response.status}`);
  }

  const reader = response.body?.getReader();
  if (!reader) throw new Error("ReadableStream 不可用");

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    // SSE 报文以空行分隔
    const blocks = buffer.split("\n\n");
    buffer = blocks.pop() || "";

    for (const block of blocks) {
      const msg = parseSSEBlock(block);
      if (msg) opts.onEvent(msg);
    }
  }
}

/** 解析单个 SSE 块（多行 event:/data:）为 ``{event, data}``。 */
function parseSSEBlock(block: string): SSEMessage | null {
  let event = "message";
  const dataLines: string[] = [];

  for (const line of block.split("\n")) {
    const trimmed = line.trim();
    if (trimmed.startsWith("event:")) {
      event = trimmed.slice(6).trim();
    } else if (trimmed.startsWith("data:")) {
      dataLines.push(trimmed.slice(5).trim());
    }
  }

  if (dataLines.length === 0) return null;
  const dataStr = dataLines.join("\n");
  try {
    return { event, data: JSON.parse(dataStr) };
  } catch {
    return { event, data: dataStr };
  }
}
