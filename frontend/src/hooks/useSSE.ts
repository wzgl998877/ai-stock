/** SSE 流式连接 Hook */

import { useCallback } from "react";
import { streamAnalysis } from "../services/analysisService";
import { useAnalysisStore } from "../store/analysisStore";
import type { SSEEvent } from "../domain/types";

export function useSSE() {
  const {
    startAnalysis,
    appendContent,
    setTitle,
    setSummary,
    setIndustries,
    setError,
    done,
  } = useAnalysisStore();

  const runAnalysis = useCallback(
    async (eventType: string, question: string, signal?: AbortSignal) => {
      startAnalysis();

      const handleEvent = (event: SSEEvent) => {
        switch (event.type) {
          case "content":
            appendContent(event.data as string);
            break;
          case "title":
            setTitle(event.data as string);
            break;
          case "summary":
            setSummary(event.data as string);
            break;
          case "industries":
            setIndustries(event.data as string[]);
            break;
          case "error":
            setError(event.data as string);
            break;
          case "done":
            done();
            break;
        }
      };

      try {
        await streamAnalysis(eventType, question, handleEvent, signal);
      } catch (err) {
        setError(err instanceof Error ? err.message : "分析失败");
      }
    },
    [startAnalysis, appendContent, setTitle, setSummary, setIndustries, setError, done]
  );

  return { runAnalysis };
}
