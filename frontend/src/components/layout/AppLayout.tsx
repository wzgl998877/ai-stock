/** AppLayout — 左右布局框架（侧边栏 + 主区域） — Stripe Design */

import React, { useEffect, useCallback, useState } from "react";
import { Layout, Menu, Typography, Button, Popconfirm, message, Tooltip, Dropdown, Drawer, Modal, Form, Input } from "antd";
import {
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
  BellOutlined,
  LockOutlined,
} from "@ant-design/icons";
import { useLocation, useNavigate } from "react-router-dom";
import type { MenuProps } from "antd";
import { useChatStore } from "../../store/chatStore";
import StockDetailDrawer from "../stock/StockDetailDrawer";
import AlertBell from "./AlertBell";
import { useStockDrawerStore } from "../../store/stockDrawerStore";
import * as chatService from "../../services/chatService";
import * as authService from "../../services/authService";
import { useAuthStore } from "../../store/authStore";

const { Sider, Content, Header } = Layout;
const { Text, Paragraph } = Typography;

const AppLayout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const isEventAnalysisPage = location.pathname === "/analysis";

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

  const [openKeys, setOpenKeys] = useState<string[]>([]);
  const [showAllSessions, setShowAllSessions] = useState(false);

  const { visible: drawerVisible, stockCode: drawerStockCode, close: closeDrawer } = useStockDrawerStore();
  const { user, logout } = useAuthStore();

  // 通知抽屉
  const [notificationOpen, setNotificationOpen] = useState(false);

  // 修改密码弹框
  const [changePwOpen, setChangePwOpen] = useState(false);
  const [changePwLoading, setChangePwLoading] = useState(false);
  const [changePwForm] = Form.useForm();

  const MAX_SESSIONS_PREVIEW = 5;

  // 按 session_type 过滤事件分析会话
  const filteredSessions = sessions.filter(
    s => (s as any).session_type === "event_analysis" || !s.event_type
  );

  const displayedSessions = showAllSessions ? filteredSessions : filteredSessions.slice(0, MAX_SESSIONS_PREVIEW);

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
    if (isEventAnalysisPage) {
      loadSessions();
    }
  }, [isEventAnalysisPage, loadSessions]);

  // 每日首次登录弹出晨报
  const [briefingVisible, setBriefingVisible] = useState(false);
  const [briefingData, setBriefingData] = useState<any>(null);
  useEffect(() => {
    const checkBriefing = async () => {
      const today = new Date().toISOString().slice(0, 10);
      const key = `briefing_seen_${today}`;
      if (localStorage.getItem(key)) return;
      try {
        const res = await fetch("/api/v1/event-radar/briefing/today", {
          headers: { Authorization: `Bearer ${localStorage.getItem("token")}` },
        });
        if (res.ok) {
          const data = await res.json();
          setBriefingData(data);
          setBriefingVisible(true);
          localStorage.setItem(key, "1");
        }
      } catch {}
    };
    checkBriefing();
  }, []);

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
        reasoning: "",
        thinking_steps: m.thinking_steps,
        event_type: m.event_type,
        summary: m.summary || "",
        industries: m.industries || [],
        created_at: m.created_at,
      }));

      // 从最后一条 assistant 消息中提取 summary 和 industries
      const lastAssistantMsg = [...loadedMessages].reverse().find((m) => m.role === "assistant");
      if (lastAssistantMsg) {
        useChatStore.getState().setSummary(lastAssistantMsg.summary || "");
        useChatStore.getState().setIndustries(lastAssistantMsg.industries || []);
      }

      loadHistory(loadedMessages, detail.title);
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

  // 修改密码
  const handleChangePw = async () => {
    const values = await changePwForm.validateFields();
    if (values.new_password !== values.confirm_password) {
      message.error("两次输入的密码不一致");
      return;
    }
    setChangePwLoading(true);
    try {
      const res = await authService.changePassword({
        old_password: values.old_password,
        new_password: values.new_password,
        confirm_password: values.confirm_password,
      });
      message.success(res.message + "，请重新登录");
      setChangePwOpen(false);
      logout();
      navigate("/login", { replace: true });
    } catch (err: any) {
      message.error(err.message || "修改失败，请重试");
    } finally {
      setChangePwLoading(false);
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
      key: "/analysis",
      icon: <MessageOutlined />,
      label: "事件分析",
    },
    {
      key: "/event-radar",
      icon: <RadarChartOutlined />,
      label: "事件雷达",
    },
    {
      key: "stock-group",
      icon: <StockOutlined />,
      label: "个股分析",
      children: [
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
    {
      key: "tools-group",
      icon: <SyncOutlined />,
      label: "数据与工具",
      children: [
        { key: "/sync", label: "数据同步" },
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
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <div
              className="brand-gradient"
              style={{
                width: 34,
                height: 34,
                borderRadius: 8,
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
            <Text
              style={{
                fontSize: 16,
                color: "#061b31",
                fontWeight: 500,
                fontFeatureSettings: "'ss01' on",
                letterSpacing: "-0.3px",
              }}
            >
              AI 投研助手
            </Text>
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

        {/* 会话历史 — 仅事件分析页面显示 */}
        {isEventAnalysisPage && (
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
            {filteredSessions.length === 0 ? (
              <div style={{ textAlign: "center", padding: "20px 0", color: "#d1d5db" }}>
                <MessageOutlined style={{ fontSize: 24, marginBottom: 8 }} />
                <div style={{ fontSize: 12, color: "#94a3b8" }}>暂无对话记录</div>
              </div>
            ) : (
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
                          fontSize: 14,
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
                          fontSize: 12,
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
                {filteredSessions.length > MAX_SESSIONS_PREVIEW && (
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
                      : `查看更多 (${filteredSessions.length - MAX_SESSIONS_PREVIEW})`}
                  </span>
                )}
              </div>
            )}
          </div>
        )}

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
              fontSize: 12,
              color: "#b0b8c4",
              margin: 0,
              lineHeight: 1.5,
              fontFeatureSettings: "'ss01' on",
              textAlign: "center",
            }}
          >
            仅供投研参考，不构成投资建议
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
        {/* 顶部 Header */}
        <Header
          style={{
            height: 56,
            lineHeight: "56px",
            padding: "0 24px",
            background: "#ffffff",
            borderBottom: "1px solid #e5edf5",
            display: "flex",
            alignItems: "center",
            justifyContent: "flex-end",
            position: "sticky",
            top: 0,
            zIndex: 9,
          }}
        >
          {/* 右侧：通知铃铛 + 用户信息 */}
          <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
            {/* 通知铃铛 */}
            <AlertBell />

            {/* 欢迎文字 */}
            {user && (
              <Text style={{ fontSize: 14, color: "#64748d", fontFeatureSettings: "'ss01' on" }}>
                欢迎您，<Text style={{ color: "#061b31", fontWeight: 500 }}>{user.user_name || user.user_account}</Text>
              </Text>
            )}

            {/* 用户下拉菜单 */}
            <Dropdown
              menu={{
                items: [
                  {
                    key: "change-password",
                    icon: <LockOutlined />,
                    label: "修改密码",
                    onClick: () => {
                      changePwForm.resetFields();
                      setChangePwOpen(true);
                    },
                  },
                  {
                    key: "logout",
                    icon: <LogoutOutlined />,
                    label: "退出登录",
                    onClick: () => {
                      logout();
                      navigate("/login", { replace: true });
                    },
                  },
                ],
              }}
              placement="bottomRight"
              trigger={["click"]}
            >
              <div
                style={{
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  gap: 6,
                  padding: "4px 8px",
                  borderRadius: 6,
                  transition: "background 0.2s",
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = "#f6f9fc";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = "transparent";
                }}
              >
                <div
                  style={{
                    width: 32,
                    height: 32,
                    borderRadius: "50%",
                    background: "linear-gradient(135deg, #533afd, #0ea5e9)",
                    color: "#fff",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontSize: 14,
                    fontWeight: 500,
                    fontFeatureSettings: "'ss01' on",
                  }}
                >
                  {(user?.user_name || user?.user_account || "U").charAt(0).toUpperCase()}
                </div>
              </div>
            </Dropdown>
          </div>
        </Header>

        <Content style={{ minHeight: "calc(100vh - 56px)" }}>{children}</Content>
      </Layout>

      {/* 全局股票行情 Drawer */}
      <StockDetailDrawer
        visible={drawerVisible}
        stockCode={drawerStockCode}
        onClose={closeDrawer}
      />

      {/* 通知 Drawer */}
      <Drawer
        title="消息通知"
        placement="right"
        width={360}
        open={notificationOpen}
        onClose={() => setNotificationOpen(false)}
      >
        <div style={{ textAlign: "center", padding: "60px 0", color: "#94a3b8" }}>
          <BellOutlined style={{ fontSize: 40, marginBottom: 16, color: "#d1d5db" }} />
          <p style={{ fontSize: 14, margin: 0 }}>暂无消息通知</p>
        </div>
      </Drawer>

      {/* 修改密码 Modal */}
      <Modal
        title="修改密码"
        open={changePwOpen}
        onCancel={() => setChangePwOpen(false)}
        onOk={handleChangePw}
        confirmLoading={changePwLoading}
        okText="确认"
        cancelText="取消"
        maskClosable={false}
      >
        <Form form={changePwForm} layout="vertical" style={{ marginTop: 8 }}>
          <Form.Item name="old_password" label="原密码" rules={[{ required: true, message: "请输入原密码" }]}>
            <Input.Password prefix={<LockOutlined style={{ color: "#b0b8c4" }} />} placeholder="请输入原密码" />
          </Form.Item>
          <Form.Item
            name="new_password"
            label="新密码"
            rules={[{ required: true, message: "请输入新密码" }, { min: 6, message: "密码至少6位" }]}
          >
            <Input.Password prefix={<LockOutlined style={{ color: "#b0b8c4" }} />} placeholder="新密码（至少6位）" />
          </Form.Item>
          <Form.Item name="confirm_password" label="确认新密码" rules={[{ required: true, message: "请再次输入新密码" }]}>
            <Input.Password prefix={<LockOutlined style={{ color: "#b0b8c4" }} />} placeholder="确认新密码" />
          </Form.Item>
        </Form>
      </Modal>

      {/* 晨报弹窗 */}
      <Modal
        title="📰 今日投资影响晨报"
        open={briefingVisible}
        onCancel={() => setBriefingVisible(false)}
        footer={null}
        width={520}
      >
        {briefingData && (
          <div>
            <p style={{ fontSize: 15, fontWeight: 500, marginBottom: 12 }}>
              {briefingData.ai_summary || "暂无重要事件"}
            </p>
            {briefingData.content?.impact_events?.length > 0 && (
              <div style={{ marginBottom: 12 }}>
                <Text type="secondary" style={{ fontSize: 12 }}>影响事件</Text>
                <ul style={{ paddingLeft: 16, margin: "4px 0" }}>
                  {briefingData.content.impact_events.slice(0, 5).map((e: any, i: number) => (
                    <li key={i} style={{ fontSize: 13, marginBottom: 2 }}>
                      <Text type={e.sentiment === "positive" ? "success" : e.sentiment === "negative" ? "danger" : undefined}>
                        {e.sentiment === "positive" ? "▲" : e.sentiment === "negative" ? "▼" : "—"}
                      </Text>{" "}
                      {e.title}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            <p style={{ fontSize: 11, color: "#94a3b8", marginTop: 8 }}>
              以上为 AI 分析参考，不构成投资建议
            </p>
          </div>
        )}
      </Modal>
    </Layout>
  );
};

export default AppLayout;
