import axios from "axios";

const STORAGE_KEY = "ai_stock_auth_user";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: 30000,
  headers: {
    "Content-Type": "application/json",
  },
});

/** 从 localStorage 读取 auth headers */
export function getAuthHeaders(): Record<string, string> {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const user = JSON.parse(raw);
      return {
        "X-User-Id": user.user_id || "default",
        "X-User-Account": user.user_account || "default",
        "X-User-Name": user.user_name || "默认用户",
      };
    }
  } catch {
    // ignore
  }
  return {};
}

/** 请求拦截器 — 注入 auth headers */
api.interceptors.request.use((config) => {
  const authHeaders = getAuthHeaders();
  Object.entries(authHeaders).forEach(([key, value]) => {
    config.headers.set(key, value);
  });
  return config;
});

/** 响应拦截器 — 错误处理 */
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status;
    const url = error.config?.url || "";

    if (status === 401) {
      // 登录/注册接口返回 401 时，不跳转，让调用方显示错误信息
      const isAuthEndpoint = url.includes("/api/auth/login") || url.includes("/api/auth/register");
      if (!isAuthEndpoint) {
        localStorage.removeItem(STORAGE_KEY);
        window.location.href = "/login";
        return Promise.reject(new Error("登录已过期，请重新登录"));
      }
    }

    const detail = error.response?.data?.detail;
    if (detail?.message) {
      return Promise.reject(new Error(detail.message));
    }
    if (detail && typeof detail === "string") {
      return Promise.reject(new Error(detail));
    }
    return Promise.reject(new Error(error.message || "请求失败"));
  }
);

export default api;
