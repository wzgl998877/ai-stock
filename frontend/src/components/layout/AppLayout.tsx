/** AppLayout — 左右布局框架（侧边栏 + 主区域） — Stripe Design */

import React from "react";
import { Layout, Menu, Typography } from "antd";
import {
  ExperimentOutlined,
  StockOutlined,
  RadarChartOutlined,
} from "@ant-design/icons";
import { useLocation, useNavigate } from "react-router-dom";

const { Sider, Content } = Layout;
const { Text, Paragraph } = Typography;

const NAV_ITEMS = [
  {
    key: "/analysis",
    icon: <ExperimentOutlined />,
    label: "AI 事件分析",
  },
  {
    key: "/market",
    icon: <StockOutlined />,
    label: "行情数据",
    disabled: true,
  },
  {
    key: "/strategy",
    icon: <RadarChartOutlined />,
    label: "策略监控",
    disabled: true,
  },
];

const AppLayout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const location = useLocation();
  const navigate = useNavigate();

  return (
    <Layout style={{ minHeight: "100vh" }}>
      {/* 左侧边栏 */}
      <Sider
        width={220}
        theme="light"
        style={{
          borderRight: "1px solid #e5edf5",
          display: "flex",
          flexDirection: "column",
          position: "fixed",
          left: 0,
          top: 0,
          bottom: 0,
          zIndex: 10,
          background: "#ffffff",
        }}
      >
        {/* 品牌区域 */}
        <div
          style={{
            padding: "24px 20px 20px",
            borderBottom: "1px solid #e5edf5",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <div
              className="brand-gradient"
              style={{
                width: 36,
                height: 36,
                borderRadius: 6,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "#fff",
                fontSize: 18,
                fontWeight: 300,
                fontFeatureSettings: "'ss01' on",
                flexShrink: 0,
              }}
            >
              AI
            </div>
            <div>
              <Text
                style={{
                  fontSize: 15,
                  color: "#061b31",
                  display: "block",
                  fontWeight: 400,
                  fontFeatureSettings: "'ss01' on",
                }}
              >
                AI 投研助手
              </Text>
              <Text
                style={{ fontSize: 11, color: "#64748d", lineHeight: 1.2 }}
              >
                Smart Investment Research
              </Text>
            </div>
          </div>
        </div>

        {/* 导航菜单 */}
        <Menu
          mode="inline"
          selectedKeys={[location.pathname]}
          items={NAV_ITEMS}
          onClick={({ key }) => navigate(key)}
          style={{
            border: "none",
            marginTop: 8,
            padding: "0 8px",
          }}
        />

        {/* 底部免责声明 */}
        <div
          style={{
            marginTop: "auto",
            padding: "16px 20px",
            borderTop: "1px solid #e5edf5",
          }}
        >
          <Paragraph
            style={{
              fontSize: 11,
              color: "#d0d5dd",
              margin: 0,
              lineHeight: 1.5,
            }}
          >
            本工具仅供投研参考
            <br />
            不构成任何投资建议
          </Paragraph>
        </div>
      </Sider>

      {/* 右侧主区域 */}
      <Layout
        style={{
          marginLeft: 220,
          background: "#ffffff",
        }}
      >
        <Content
          style={{
            minHeight: "100vh",
          }}
        >
          {children}
        </Content>
      </Layout>
    </Layout>
  );
};

export default AppLayout;
