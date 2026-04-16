/** useAnalysis — 分析流程编排 */

import { useCallback, useRef } from "react";
import { useSSE } from "../hooks/useSSE";
import { useAnalysisStore } from "../store/analysisStore";
import { AnalysisStatus } from "../domain/types";

export function useAnalysis() {
  const { runAnalysis } = useSSE();
  const { status, result, title, summary, industries, error } = useAnalysisStore();
  const abortRef = useRef<AbortController | null>(null);

  const analyze = useCallback(
    async (eventType: string, question: string) => {
      // 取消之前的请求
      if (abortRef.current) {
        abortRef.current.abort();
      }
      const controller = new AbortController();
      abortRef.current = controller;

      await runAnalysis(eventType, question, controller.signal);
    },
    [runAnalysis]
  );

  const stop = useCallback(() => {
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }
    useAnalysisStore.getState().done();
  }, []);

  const isStreaming = status === AnalysisStatus.STREAMING;
  const isDone = status === AnalysisStatus.DONE;
  const isError = status === AnalysisStatus.ERROR;
  const isIdle = status === AnalysisStatus.IDLE;

  return {
    status,
    result,
    title,
    summary,
    industries,
    error,
    analyze,
    stop,
    isStreaming,
    isDone,
    isError,
    isIdle,
  };
}
