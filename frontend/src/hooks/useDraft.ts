/**草稿自动保存 Hook (localStorage) */

import { useCallback, useRef } from "react";
import { DRAFT_KEY_PREFIX, DRAFT_MIN_LENGTH, DRAFT_DEBOUNCE_MS } from "../domain/constants";

interface DraftData {
  content: string;
  eventType: string;
  updatedAt: number;
}

export function useDraft(eventType: string) {
  const key = `${DRAFT_KEY_PREFIX}${eventType}`;
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // 保存草稿（防抖）
  const saveDraft = useCallback(
    (content: string) => {
      if (timerRef.current) clearTimeout(timerRef.current);

      if (content.length >= DRAFT_MIN_LENGTH) {
        timerRef.current = setTimeout(() => {
          const data: DraftData = {
            content,
            eventType,
            updatedAt: Date.now(),
          };
          localStorage.setItem(key, JSON.stringify(data));
        }, DRAFT_DEBOUNCE_MS);
      }
    },
    [key, eventType]
  );

  // 清除草稿
  const clearDraft = useCallback(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    localStorage.removeItem(key);
  }, [key]);

  return { saveDraft, clearDraft };
}
