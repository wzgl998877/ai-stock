/** Auth Store — Zustand */

import { create } from "zustand";
import type { UserInfo } from "../services/authService";
import { useChatStore } from "./chatStore";

const STORAGE_KEY = "ai_stock_auth_user";

interface AuthState {
  user: UserInfo | null;
  isAuthenticated: boolean;
  sessionKey: number; // 每次登录递增，用于强制重置 UI 组件
  setUser: (user: UserInfo) => void;
  logout: () => void;
  loadFromStorage: () => void;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  isAuthenticated: false,
  sessionKey: 0,

  setUser: (user: UserInfo) => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(user));
    set({ user, isAuthenticated: true, sessionKey: get().sessionKey + 1 });
  },

  logout: () => {
    localStorage.removeItem(STORAGE_KEY);
    set({ user: null, isAuthenticated: false });
    // 清空 chat 数据，防止新用户/重新登录后看到旧会话
    useChatStore.getState().setSessions([]);
    useChatStore.getState().setCurrentSessionId(null);
    useChatStore.getState().resetMessages();
  },

  loadFromStorage: () => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const user: UserInfo = JSON.parse(raw);
        set({ user, isAuthenticated: true, sessionKey: get().sessionKey + 1 });
      }
    } catch {
      localStorage.removeItem(STORAGE_KEY);
    }
  },
}));
