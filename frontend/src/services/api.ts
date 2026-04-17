import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: 30000,
  headers: {
    "Content-Type": "application/json",
  },
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const detail = error.response?.data?.detail;
    if (detail?.message) {
      return Promise.reject(new Error(detail.message));
    }
    return Promise.reject(new Error(error.message || "请求失败"));
  }
);

export default api;
