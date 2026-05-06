/** AppLayout — 左右布局框架（侧边栏 + 主区域） — Stripe Design */

import React, { useEffect, useCallback, useState } from "react";
import { Layout, Menu, Typography, Button, Popconfirm, message } from "antd";
import {
  ExperimentOutlined,
  StockOutlined,
  BarChartOutlined,
  RadarChartOutlined,
  BookOutlined,
  PlusOutlined,
  DeleteOutlined,
  SyncOutlined,
  FileSearchOutlined,
} from "@ant-design/icons";
import { useLocation, useNavigate } from "react-router-dom";
import type { MenuProps } from "antd";
import { useChatStore } from "../../store/chatStore";
import StockSearch from "../stock/StockSearch";
import StockDetailDrawer from "../stock/StockDetailDrawer";
import { useStockDrawerStore } from "../../store/stockDrawerStore";
import * as chatService from "../../services/chatService";

const { Sider, Content } = Layout;
const { Text, Paragraph } = Typography;

const AppLayout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const isAnalysisPage = location.pathname === "/analysis";

  const {
    sessions,
    currentSessionId,
    setSessions,
    removeSession,
    setCurrentSessionId,
    switchSession,
    loadHistory,
    resetMessages,
    doneStreaming,
    streamingMessageId,
  } = useChatStore();

  const [openKeys, setOpenKeys] = useState<string[]>(["analysis-group"]);
  const [showAllSessions, setShowAllSessions] = useState(false);

  const { visible: drawerVisible, stockCode: drawerStockCode, close: closeDrawer } = useStockDrawerStore();

  // 默认只展示5条会话
  const MAX_SESSIONS_PREVIEW = 5;
  const displayedSessions = showAllSessions ? sessions : sessions.slice(0, MAX_SESSIONS_PREVIEW);

  // 加载会话列表
  const loadSessions = useCallback(async () => {
    try {
      const res = await chatService.listSessions();
      setSessions(res.sessions);
    } catch {
      // 静默失败
    }
  }, [setSessions]);

  useEffect(() => {
    if (isAnalysisPage) {
      loadSessions();
    }
  }, [isAnalysisPage, loadSessions]);

  // 当前选中的菜单项
  const selectedKeys = currentSessionId && isAnalysisPage
    ? [`session-${currentSessionId}`]
    : [location.pathname];

  // 新建对话
  const handleNewChat = () => {
    if (streamingMessageId) {
      doneStreaming();
    }
    setCurrentSessionId(null);
    resetMessages();
  };

  // 选择会话
  const handleSelectSession = async (sessionId: string) => {
    if (sessionId === currentSessionId) return;
    if (streamingMessageId) {
      doneStreaming();
    }
    switchSession(sessionId);
    try {
      const detail = await chatService.getSession(sessionId);
      const loadedMessages = (detail.messages || []).map((m: any) => ({
        id: m.id,
        role: m.role,
        content: m.content,
        reasoning: m.reasoning || "",
        thinking_steps: m.thinking_steps,
        event_type: m.event_type,
        created_at: m.created_at,
      }));
      loadHistory(loadedMessages);
    } catch {
      message.error("加载会话失败");
    }
  };

  // 删除会话
  const handleDeleteSession = async (e: React.MouseEvent, sessionId: string) => {
    e.stopPropagation();
    try {
      await chatService.deleteSession(sessionId);
      removeSession(sessionId);
    } catch {
      // 静默失败
    }
  };

  // 格式化日期
  const formatDate = (dateStr: string) => {
    if (!dateStr) return "";
    const d = new Date(dateStr);
    const now = new Date();
    const isToday =
      d.getFullYear() === now.getFullYear() &&
      d.getMonth() === now.getMonth() &&
      d.getDate() === now.getDate();
    if (isToday) return `${d.getHours().toString().padStart(2, "0")}:${d.getMinutes().toString().padStart(2, "0")}`;
    return `${(d.getMonth() + 1).toString().padStart(2, "0")}/${d.getDate().toString().padStart(2, "0")}`;
  };

  // 构建菜单项
  const menuItems: MenuProps["items"] = [
    // AI 事件分析（含会话列表）
    {
      key: "analysis-group",
      icon: <ExperimentOutlined />,
      label: "AI 事件分析",
      children: [
        {
          key: "new-chat",
          label: (
            <Button
              type="text"
              icon={<PlusOutlined />}
              size="small"
              style={{ fontSize: 12, padding: 0, height: "auto", color: "#533afd" }}
              onClick={(e) => {
                e.stopPropagation();
                handleNewChat();
              }}
            >
              新建对话
            </Button>
          ),
          disabled: false,
          style: { height: 32, lineHeight: "32px" },
        },
        ...displayedSessions.map((session) => ({
          key: `session-${session.id}`,
          label: (
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                paddingRight: 4,
              }}
            >
              <div style={{ flex: 1, minWidth: 0, overflow: "hidden" }}>
                <div
                  style={{
                    fontSize: 12,
                    color: currentSessionId === session.id ? "#533afd" : "#273951",
                    fontWeight: currentSessionId === session.id ? 500 : 400,
                    whiteSpace: "nowrap",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    lineHeight: "18px",
                  }}
                >
                  {session.title || "新对话"}
                </div>
                <div style={{ fontSize: 10, color: "#94a3b8", lineHeight: "14px" }}>
                  {formatDate(session.created_at)}
                </div>
              </div>
              <Popconfirm
                title="删除此对话？"
                onConfirm={(e) => handleDeleteSession(e as React.MouseEvent, session.id)}
                onCancel={(e) => e?.stopPropagation()}
                okText="删除"
                cancelText="取消"
              >
                <DeleteOutlined
                  onClick={(e) => e.stopPropagation()}
                  style={{ fontSize: 11, color: "#94a3b8", flexShrink: 0, marginLeft: 4 }}
                />
              </Popconfirm>
            </div>
          ),
        })),
        // "查看更多" / "收起"
        ...(sessions.length > MAX_SESSIONS_PREVIEW
          ? [{
              key: "toggle-sessions",
              label: (
                <span
                  onClick={(e) => {
                    e.stopPropagation();
                    setShowAllSessions(!showAllSessions);
                  }}
                  style={{ fontSize: 12, color: "#533afd", cursor: "pointer" }}
                >
                  {showAllSessions
                    ? `收起`
                    : `查看更多 (${sessions.length - MAX_SESSIONS_PREVIEW}条)`}
                </span>
              ),
              disabled: false,
              style: { height: 28, lineHeight: "28px" },
            }]
          : []),
      ],
    },
    {
      type: "divider" as const,
    },
    {
      key: "/stock-analysis",
      icon: <StockOutlined />,
      label: "个股分析",
    },
    {
      key: "/analysis-records",
      icon: <FileSearchOutlined />,
      label: "分析记录",
    },
    {
      key: "/sync",
      icon: <SyncOutlined />,
      label: "数据同步",
    },
    {
      key: "/knowledge",
      icon: <BookOutlined />,
      label: "知识库",
    },
    {
      key: "/market",
      icon: <BarChartOutlined />,
      label: "行情数据",
      children: [
        { key: "/market/watchlist", label: "自选股" },
        { key: "/market/industry", label: "行业对比" },
      ],
    },
    {
      key: "/strategy",
      icon: <RadarChartOutlined />,
      label: "策略监控",
      disabled: true,
    },
  ];

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
          selectedKeys={selectedKeys}
          openKeys={openKeys}
          onOpenChange={(keys) => {
            setOpenKeys(keys);
            // 点击"AI 事件分析"标题展开时，同时导航到 /analysis
            if (keys.includes("analysis-group") && location.pathname !== "/analysis") {
              navigate("/analysis");
            }
          }}
          items={menuItems}
          onClick={({ key }) => {
            if (key.startsWith("session-")) {
              const sessionId = key.replace("session-", "");
              handleSelectSession(sessionId);
            } else if (key === "new-chat") {
              // handled by button click
            } else {
              navigate(key);
            }
          }}
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
        {/* 顶部搜索栏 */}
        <div style={{
          padding: "8px 24px",
          borderBottom: "1px solid #e5edf5",
          display: "flex",
          justifyContent: "flex-end",
          alignItems: "center",
          background: "#fff",
        }}>
          <StockSearch />
        </div>
        <Content
          style={{
            minHeight: "100vh",
          }}
        >
          {children}
        </Content>
      </Layout>

      {/* 全局股票行情 Drawer */}
      <StockDetailDrawer
        visible={drawerVisible}
        stockCode={drawerStockCode}
        onClose={closeDrawer}
      />
    </Layout>
  );
};

export default AppLayout;
