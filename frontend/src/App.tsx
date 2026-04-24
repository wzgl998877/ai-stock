/** App — 路由入口 + 主题配置 */

import React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { ConfigProvider, theme } from "antd";
import zhCN from "antd/locale/zh_CN";
import AppLayout from "./components/layout/AppLayout";
import AnalysisPage from "./pages/AnalysisPage";
import KnowledgePage from "./pages/KnowledgePage";
import ArticleDetailPage from "./pages/ArticleDetailPage";
import StockAnalysisPage from "./pages/StockAnalysisPage";
import SyncPanel from "./pages/SyncPanel";
import "./styles/global.css";

const App: React.FC = () => (
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
      <AppLayout>
        <Routes>
          <Route path="/analysis" element={<AnalysisPage />} />
          <Route path="/stock-analysis" element={<StockAnalysisPage />} />
          <Route path="/sync" element={<SyncPanel />} />
          <Route path="/knowledge" element={<KnowledgePage />} />
          <Route path="/knowledge/articles/:id" element={<ArticleDetailPage />} />
          <Route path="*" element={<Navigate to="/analysis" replace />} />
        </Routes>
      </AppLayout>
    </BrowserRouter>
  </ConfigProvider>
);

export default App;
