/** AppLayout — 左右布局框架（侧边栏 + 主区域） — Stripe Design */

import React, { useEffect, useCallback, useState } from "react";
import { Layout, Menu, Typography, Button, Popconfirm, message, Tooltip } from "antd";
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
  MessageOutlined,
  LogoutOutlined,
} from "@ant-design/icons";
import { useLocation, useNavigate } from "react-router-dom";
import type { MenuProps } from "antd";
import { useChatStore } from "../../store/chatStore";
import StockDetailDrawer from "../stock/StockDetailDrawer";
import { useStockDrawerStore } from "../../store/stockDrawerStore";
import * as chatService from "../../services/chatService";
import { useAuthStore } from "../../store/authStore";

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
  const { user, logout } = useAuthStore();

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
  const selectedKeys = [location.pathname];

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

  // 一级菜单 → 二级菜单
  const menuItems: MenuProps["items"] = [
    {
      key: "analysis-group",
      icon: <ExperimentOutlined />,
      label: "智能分析",
      children: [
        { key: "/analysis", icon: <MessageOutlined />, label: "AI 事件分析" },
        { key: "/stock-analysis", icon: <StockOutlined />, label: "个股分析" },
        { key: "/analysis-records", icon: <FileSearchOutlined />, label: "分析记录" },
      ],
    },
    {
      key: "/knowledge",
      icon: <BookOutlined />,
      label: "知识库",
    },
    {
      key: "tools-group",
      icon: <SyncOutlined />,
      label: "数据与工具",
      children: [
        { key: "/sync", label: "数据同步" },
      ],
    },
    {
      key: "market-group",
      icon: <BarChartOutlined />,
      label: "行情数据",
      children: [
        { key: "/market/watchlist", label: "自选股" },
        { key: "/market/industry", label: "行业对比" },
        {
          key: "/strategy",
          icon: <RadarChartOutlined />,
          label: (
            <Tooltip title="即将推出" placement="right">
              <span>策略监控</span>
            </Tooltip>
          ),
          disabled: true,
        },
      ],
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
          overflowY: "auto",
        }}
      >
        {/* 品牌区域 */}
        <div
          style={{
            padding: "20px 20px 16px",
            borderBottom: "1px solid #e5edf5",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <div
              className="brand-gradient"
              style={{
                width: 34,
                height: 34,
                borderRadius: 6,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "#fff",
                fontSize: 16,
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
                  lineHeight: 1.3,
                }}
              >
                AI 投研助手
              </Text>
              <Text
                style={{
                  fontSize: 11,
                  color: "#94a3b8",
                  lineHeight: 1.2,
                  fontFeatureSettings: "'ss01' on",
                }}
              >
                Smart Investment Research
              </Text>
            </div>
          </div>
        </div>

        {/* 导航菜单 — 纯二级结构 */}
        <Menu
          mode="inline"
          selectedKeys={selectedKeys}
          openKeys={openKeys}
          onOpenChange={(keys) => setOpenKeys(keys)}
          items={menuItems}
          onClick={({ key }) => {
            if (key.startsWith("/")) {
              navigate(key);
            }
          }}
          style={{
            border: "none",
            padding: "0 8px",
          }}
        />

        {/* 会话历史 — 仅在 AI 事件分析页面显示 */}
        {isAnalysisPage && (
          <div
            style={{
              borderTop: "1px solid #e5edf5",
              padding: "12px 12px 8px",
              flexShrink: 0,
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: 8,
                paddingLeft: 4,
              }}
            >
              <Text
                style={{
                  fontSize: 12,
                  color: "#94a3b8",
                  fontWeight: 500,
                  fontFeatureSettings: "'ss01' on",
                }}
              >
                对话历史
              </Text>
              <Button
                type="text"
                icon={<PlusOutlined />}
                size="small"
                onClick={handleNewChat}
                style={{
                  fontSize: 13,
                  color: "#533afd",
                  padding: "0 4px",
                  height: 24,
                }}
              >
                新建
              </Button>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
              {displayedSessions.map((session) => (
                <div
                  key={session.id}
                  onClick={() => handleSelectSession(session.id)}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    padding: "6px 8px",
                    borderRadius: 4,
                    cursor: "pointer",
                    background:
                      currentSessionId === session.id
                        ? "rgba(83, 58, 253, 0.06)"
                        : "transparent",
                    borderLeft:
                      currentSessionId === session.id
                        ? "2px solid #533afd"
                        : "2px solid transparent",
                    transition: "background 0.15s",
                  }}
                  onMouseEnter={(e) => {
                    if (currentSessionId !== session.id) {
                      e.currentTarget.style.background = "#f6f9fc";
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (currentSessionId !== session.id) {
                      e.currentTarget.style.background = "transparent";
                    }
                  }}
                >
                  <div style={{ flex: 1, minWidth: 0, overflow: "hidden" }}>
                    <div
                      style={{
                        fontSize: 13,
                        color: currentSessionId === session.id ? "#533afd" : "#273951",
                        fontWeight: currentSessionId === session.id ? 500 : 400,
                        whiteSpace: "nowrap",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        lineHeight: "18px",
                        fontFeatureSettings: "'ss01' on",
                      }}
                    >
                      {session.title || "新对话"}
                    </div>
                    <div
                      style={{
                        fontSize: 11,
                        color: "#94a3b8",
                        lineHeight: "15px",
                      }}
                    >
                      {formatDate(session.created_at)}
                    </div>
                  </div>
                  <Popconfirm
                    title="删除此对话？"
                    onConfirm={(e) =>
                      handleDeleteSession(e as React.MouseEvent, session.id)
                    }
                    onCancel={(e) => e?.stopPropagation()}
                    okText="删除"
                    cancelText="取消"
                  >
                    <DeleteOutlined
                      onClick={(e) => e.stopPropagation()}
                      style={{
                        fontSize: 12,
                        color: "#b0b8c4",
                        flexShrink: 0,
                        marginLeft: 4,
                        padding: 4,
                        cursor: "pointer",
                        transition: "color 0.2s",
                      }}
                      onMouseEnter={(e) =>
                        (e.currentTarget.style.color = "#ea2261")
                      }
                      onMouseLeave={(e) =>
                        (e.currentTarget.style.color = "#b0b8c4")
                      }
                    />
                  </Popconfirm>
                </div>
              ))}
              {/* 查看更多 / 收起 */}
              {sessions.length > MAX_SESSIONS_PREVIEW && (
                <span
                  onClick={() => setShowAllSessions(!showAllSessions)}
                  style={{
                    fontSize: 12,
                    color: "#533afd",
                    cursor: "pointer",
                    padding: "4px 8px",
                    lineHeight: "18px",
                    fontFeatureSettings: "'ss01' on",
                  }}
                >
                  {showAllSessions
                    ? "收起"
                    : `查看更多 (${sessions.length - MAX_SESSIONS_PREVIEW})`}
                </span>
              )}
            </div>
          </div>
        )}

        {/* 底部免责声明 + 用户信息 */}
        <div
          style={{
            marginTop: "auto",
            padding: "16px 20px",
            borderTop: "1px solid #e5edf5",
          }}
        >
          {user && (
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8 }}>
              <Text style={{ fontSize: 13, color: "#273951", fontWeight: 500, fontFeatureSettings: "'ss01' on" }}>
                {user.user_name || user.user_account}
              </Text>
              <Button
                type="text"
                icon={<LogoutOutlined />}
                size="small"
                onClick={() => {
                  logout();
                  navigate("/login", { replace: true });
                }}
                style={{ fontSize: 12, color: "#94a3b8", padding: "0 4px", height: 22 }}
              >
                退出
              </Button>
            </div>
          )}
          <Paragraph
            style={{
              fontSize: 12,
              color: "#98a2b3",
              margin: 0,
              lineHeight: 1.5,
              fontFeatureSettings: "'ss01' on",
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
        <Content style={{ minHeight: "100vh" }}>{children}</Content>
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
