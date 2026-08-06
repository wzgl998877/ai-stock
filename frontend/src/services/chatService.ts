/** Chat API Service */

import api, { getAuthHeaders } from "./api";
import type { SSEEvent, ChatSessionType } from "../domain/types";

const BASE = "/api/chat";

/** 创建新会话 */
export async function createSession(
  title?: string,
  eventType?: string
): Promise<ChatSessionType> {
  const res = await api.post(`${BASE}/sessions`, {
    title: title || null,
    event_type: eventType || null,
  });
  return res.data;
}

/** 列出所有会话 */
export async function listSessions(): Promise<{
  sessions: ChatSessionType[];
  total: number;
}> {
  const res = await api.get(`${BASE}/sessions`);
  return res.data;
}

/** 获取会话详情（含消息列表） */
export async function getSession(id: string): Promise<{
  id: string;
  title: string;
  event_type: string | null;
  messages: {
    id: string;
    role: string;
    content: string;
    thinking_steps?: any[];
    event_type?: string | null;
    summary?: string | null;
    industries?: string[] | null;
    created_at: string;
  }[];
  created_at: string;
  updated_at: string;
}> {
  const res = await api.get(`${BASE}/sessions/${id}`);
  return res.data;
}

/** 删除会话 */
export async function deleteSession(id: string): Promise<void> {
  await api.delete(`${BASE}/sessions/${id}`);
}

/**
 * 流式发送消息 — fetch + ReadableStream 解析 SSE
 */
export async function streamMessage(
  sessionId: string,
  content: string,
  eventType: string | null,
  onEvent: (event: SSEEvent) => void,
  signal?: AbortSignal,
  useKnowledgeBase: boolean = true
): Promise<void> {
  const baseURL = import.meta.env.VITE_API_BASE_URL || "";
  const response = await fetch(`${baseURL}${BASE}/sessions/${sessionId}/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...getAuthHeaders() },
    body: JSON.stringify({ content, event_type: eventType, use_knowledge_base: useKnowledgeBase }),
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
