/** 草稿自动保存 Hook (localStorage) */

import { useState, useEffect, useCallback, useRef } from "react";
import { DRAFT_KEY_PREFIX, DRAFT_MIN_LENGTH, DRAFT_DEBOUNCE_MS } from "../domain/constants";

interface DraftData {
  content: string;
  eventType: string;
  updatedAt: number;
}

export function useDraft(eventType: string) {
  const key = `${DRAFT_KEY_PREFIX}${eventType}`;
  const [draft, setDraft] = useState<string>("");
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // 页面加载时恢复草稿
  useEffect(() => {
    try {
      const raw = localStorage.getItem(key);
      if (raw) {
        const data: DraftData = JSON.parse(raw);
        setDraft(data.content);
      }
    } catch {
      // ignore
    }
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [key]);

  // 保存草稿（防抖）
  const saveDraft = useCallback(
    (content: string) => {
      setDraft(content);
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
    setDraft("");
    localStorage.removeItem(key);
  }, [key]);

  return { draft, saveDraft, clearDraft };
}
