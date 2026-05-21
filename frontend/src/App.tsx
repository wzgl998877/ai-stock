/** App — 路由入口 + 主题配置 + 认证守卫 */

import React, { useEffect } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { ConfigProvider, theme } from "antd";
import zhCN from "antd/locale/zh_CN";
import AppLayout from "./components/layout/AppLayout";
import LoginPage from "./pages/LoginPage";
import ForgotPasswordPage from "./pages/ForgotPasswordPage";
import AnalysisPage from "./pages/AnalysisPage";
import KnowledgePage from "./pages/KnowledgePage";
import ArticleDetailPage from "./pages/ArticleDetailPage";
import StockAnalysisPage from "./pages/StockAnalysisPage";
import StockAnalysisDebugPage from "./pages/StockAnalysisDebugPage";
import AnalysisRecordsPage from "./pages/AnalysisRecordsPage";
import SyncPanel from "./pages/SyncPanel";
import StockDetailPage from "./pages/StockDetailPage";
import WatchlistPage from "./pages/WatchlistPage";
import IndustryPage from "./pages/IndustryPage";
import EventRadarPage from "./pages/EventRadarPage";
import { useAuthStore } from "./store/authStore";
import "./styles/global.css";

/** 路由守卫：未登录跳转到 /login */
const AuthGuard: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated } = useAuthStore();
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
};

/** 已登录守卫：已登录时访问登录页跳转到 /analysis */
const GuestGuard: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated } = useAuthStore();
  if (isAuthenticated) {
    return <Navigate to="/analysis" replace />;
  }
  return <>{children}</>;
};

/** 页面内容：统一使用 AppLayout */
const AppContent: React.FC = () => {
  const { sessionKey } = useAuthStore();
  return (
    <AppLayout key={sessionKey}>
      <Routes>
        <Route path="/analysis" element={<AnalysisPage />} />
        <Route path="/stock-analysis" element={<StockAnalysisPage />} />
        <Route path="/stock-analysis-debug" element={<StockAnalysisDebugPage />} />
        <Route path="/analysis-records" element={<AnalysisRecordsPage />} />
        <Route path="/sync" element={<SyncPanel />} />
        <Route path="/knowledge" element={<KnowledgePage />} />
        <Route path="/knowledge/articles/:id" element={<ArticleDetailPage />} />
        {/* 模块二：行情数据 */}
        <Route path="/market/stock/:code" element={<StockDetailPage />} />
        <Route path="/market/watchlist" element={<WatchlistPage />} />
        {/* 行业对比 — 即将推出 */}
        {/* <Route path="/market/industry" element={<IndustryPage />} /> */}
        {/* 模块四：事件影响雷达 */}
        <Route path="/event-radar" element={<EventRadarPage />} />
        <Route path="*" element={<Navigate to="/analysis" replace />} />
      </Routes>
    </AppLayout>
  );
};

const App: React.FC = () => {
  const { loadFromStorage } = useAuthStore();

  useEffect(() => {
    loadFromStorage();
  }, [loadFromStorage]);

  return (
    <ConfigProvider
      locale={zhCN}
      theme={{
        token: {
          colorPrimary: "#533afd",
          colorSuccess: "#15be53",
          colorInfo: "#533afd",
          borderRadius: 6,
          colorBgContainer: "#ffffff",
          colorBgLayout: "#ffffff",
          fontFamily: `'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif`,
          fontSize: 14,
          colorText: "#061b31",
          colorTextSecondary: "#64748d",
          colorBorder: "#e5edf5",
          colorBorderSecondary: "#e5edf5",
        },
        components: {
          Button: {
            borderRadius: 4,
            controlHeight: 40,
            fontWeight: 400,
          },
          Card: {
            borderRadiusLG: 6,
          },
          Radio: {
            borderRadius: 4,
          },
          Input: {
            borderRadius: 4,
          },
          Alert: {
            borderRadius: 6,
          },
          Menu: {
            itemBorderRadius: 6,
            itemMarginBlock: 4,
          },
        },
        algorithm: theme.defaultAlgorithm,
      }}
    >
      <BrowserRouter>
        <Routes>
          {/* 公开路由 — 未登录可访问，已登录自动跳转 */}
          <Route
            path="/login"
            element={
              <GuestGuard>
                <LoginPage />
              </GuestGuard>
            }
          />
          <Route
            path="/forgot-password"
            element={
              <GuestGuard>
                <ForgotPasswordPage />
              </GuestGuard>
            }
          />
          {/* 受保护路由 */}
          <Route
            path="/*"
            element={
              <AuthGuard>
                <AppContent />
              </AuthGuard>
            }
          />
        </Routes>
      </BrowserRouter>
    </ConfigProvider>
  );
};

export default App;
