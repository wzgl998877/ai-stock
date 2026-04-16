/** App — 路由入口 */

import React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { ConfigProvider } from "antd";
import zhCN from "antd/locale/zh_CN";
import AnalysisPage from "./pages/AnalysisPage";

const App: React.FC = () => (
  <ConfigProvider locale={zhCN}>
    <BrowserRouter>
      <Routes>
        <Route path="/analysis" element={<AnalysisPage />} />
        <Route path="*" element={<Navigate to="/analysis" replace />} />
      </Routes>
    </BrowserRouter>
  </ConfigProvider>
);

export default App;
