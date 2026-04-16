/** App — 路由入口 + 主题配置 */

import React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { ConfigProvider, theme } from "antd";
import zhCN from "antd/locale/zh_CN";
import AppLayout from "./components/layout/AppLayout";
import AnalysisPage from "./pages/AnalysisPage";
import "./styles/global.css";

const App: React.FC = () => (
  <ConfigProvider
    locale={zhCN}
    theme={{
      token: {
        colorPrimary: "#07C160",
        colorSuccess: "#07C160",
        colorInfo: "#07C160",
        borderRadius: 12,
        colorBgContainer: "#ffffff",
        colorBgLayout: "#f5f7fa",
        fontFamily: `-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'PingFang SC', 'Microsoft YaHei', sans-serif`,
        fontSize: 14,
        colorText: "#1d2939",
        colorTextSecondary: "#667085",
        colorBorder: "#eaecf0",
        colorBorderSecondary: "#f2f4f7",
      },
      components: {
        Button: {
          borderRadius: 8,
          controlHeight: 40,
          fontWeight: 500,
        },
        Card: {
          borderRadiusLG: 16,
        },
        Radio: {
          borderRadius: 8,
        },
        Input: {
          borderRadius: 10,
        },
        Alert: {
          borderRadius: 10,
        },
        Menu: {
          itemBorderRadius: 8,
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
          <Route path="*" element={<Navigate to="/analysis" replace />} />
        </Routes>
      </AppLayout>
    </BrowserRouter>
  </ConfigProvider>
);

export default App;
