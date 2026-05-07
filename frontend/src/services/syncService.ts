import api, { getAuthHeaders } from "./api";

export interface SyncTaskRecord {
  task_id: string;
  source_type: string;
  data_type: string;
  status: string;
  total_count: number;
  processed_count: number;
  success_count: number;
  fail_count: number;
  error_message: string | null;
  start_time: string | null;
  end_time: string | null;
  duration_ms: number | null;
}

export interface SyncTaskListResponse {
  items: SyncTaskRecord[];
  total: number;
  page: number;
  page_size: number;
}

export interface SyncParams {
  sourceType: string;
  dataType: string;
  symbol?: string;
  startDate?: string;
  endDate?: string;
}

export const syncService = {
  /**
   * Execute sync and receive SSE progress events.
   * Returns an AbortController so the caller can cancel.
   */
  executeSync(
    params: SyncParams,
    onEvent: (eventType: string, data: any) => void,
    onError: (error: Error) => void,
  ): AbortController {
    const controller = new AbortController();
    const query = new URLSearchParams({
      source_type: params.sourceType,
      data_type: params.dataType,
    });
    if (params.symbol) query.set("symbol", params.symbol);
    if (params.startDate) query.set("start_date", params.startDate);
    if (params.endDate) query.set("end_date", params.endDate);

    const url = `${import.meta.env.VITE_API_BASE_URL}/api/v1/sync/execute?${query.toString()}`;

    fetch(url, {
      method: "GET",
      headers: {
        Accept: "text/event-stream",
        "Cache-Control": "no-cache",
        ...getAuthHeaders(),
      },
      signal: controller.signal,
    })
      .then(async (response) => {
        if (!response.ok) {
          const errData = await response.json().catch(() => null);
          onError(new Error(errData?.message || `HTTP ${response.status}`));
          return;
        }

        const reader = response.body?.getReader();
        if (!reader) {
          onError(new Error("ReadableStream not supported"));
          return;
        }

        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });

          // Parse SSE messages (event: ...\ndata: ...\n\n)
          const messages = buffer.split("\n\n");
          buffer = messages.pop() || "";

          for (const msg of messages) {
            if (!msg.trim()) continue;
            const lines = msg.split("\n");
            let eventType = "message";
            let dataStr = "";
            for (const line of lines) {
              if (line.startsWith("event: ")) {
                eventType = line.slice(7).trim();
              } else if (line.startsWith("data: ")) {
                dataStr = line.slice(6).trim();
              }
            }
            if (dataStr) {
              try {
                const data = JSON.parse(dataStr);
                onEvent(eventType, data);
              } catch {
                onEvent(eventType, { raw: dataStr });
              }
            }
          }
        }
      })
      .catch((err) => {
        if (err.name !== "AbortError") {
          onError(err);
        }
      });

    return controller;
  },

  async listSyncTasks(
    page = 1,
    pageSize = 20,
    sourceType?: string,
    status?: string,
  ): Promise<SyncTaskListResponse> {
    const params = new URLSearchParams({
      page: String(page),
      page_size: String(pageSize),
    });
    if (sourceType) params.set("source_type", sourceType);
    if (status) params.set("status", status);

    const res = await api.get(`/api/v1/sync/tasks?${params.toString()}`);
    return res.data.data;
  },

  async retryTask(taskId: string): Promise<void> {
    await api.post(`/api/v1/sync/tasks/${taskId}/retry`);
  },
};
