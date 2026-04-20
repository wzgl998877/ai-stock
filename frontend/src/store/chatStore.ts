/** Chat 状态管理 (Zustand) */

import { create } from "zustand";
import type { ChatMessageType, ChatSessionType, ThinkingStepData } from "../domain/types";

interface ChatState {
  // === State ===
  sessions: ChatSessionType[];
  currentSessionId: string | null;
  messages: ChatMessageType[];
  streamingMessageId: string | null; // 当前正在流式输出的 AI 消息 ID
  title: string;
  summary: string;
  industries: string[];

  // === Session Actions ===
  setSessions: (sessions: ChatSessionType[]) => void;
  addSession: (session: ChatSessionType) => void;
  removeSession: (id: string) => void;
  setCurrentSessionId: (id: string | null) => void;

  // === Message Actions ===
  setMessages: (messages: ChatMessageType[]) => void;
  addMessage: (message: ChatMessageType) => void;
  appendContent: (content: string) => void;
  addThinkingStep: (step: ThinkingStepData) => void;
  setTitle: (title: string) => void;
  setSummary: (summary: string) => void;
  setIndustries: (industries: string[]) => void;

  // === Streaming Control ===
  startStreaming: (messageId: string) => void;
  doneStreaming: () => void;

  // === Reset ===
  resetMessages: () => void;
}

const initialMessageState = {
  messages: [],
  streamingMessageId: null,
  title: "",
  summary: "",
  industries: [],
};

export const useChatStore = create<ChatState>((set) => ({
  sessions: [],
  currentSessionId: null,
  ...initialMessageState,

  // --- Session Actions ---

  setSessions: (sessions) => set({ sessions }),

  addSession: (session) =>
    set((state) => ({ sessions: [session, ...state.sessions] })),

  removeSession: (id) =>
    set((state) => ({
      sessions: state.sessions.filter((s) => s.id !== id),
    })),

  setCurrentSessionId: (id) =>
    set({ currentSessionId: id }),

  // --- Message Actions ---

  setMessages: (messages) => set({ messages }),

  addMessage: (message) =>
    set((state) => ({ messages: [...state.messages, message] })),

  appendContent: (content) =>
    set((state) => ({
      messages: state.messages.map((msg) =>
        msg.id === state.streamingMessageId
          ? { ...msg, content: msg.content + content }
          : msg
      ),
    })),

  addThinkingStep: (step) =>
    set((state) => ({
      messages: state.messages.map((msg) =>
        msg.id === state.streamingMessageId
          ? {
              ...msg,
              thinking_steps: [...(msg.thinking_steps || []), step],
            }
          : msg
      ),
    })),

  setTitle: (title) => set({ title }),

  setSummary: (summary) => set({ summary }),

  setIndustries: (industries) => set({ industries }),

  // --- Streaming Control ---

  startStreaming: (messageId) =>
    set({ streamingMessageId: messageId }),

  doneStreaming: () => set({ streamingMessageId: null }),

  // --- Reset ---

  resetMessages: () => set(initialMessageState),
}));
