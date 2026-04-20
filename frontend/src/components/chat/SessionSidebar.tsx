/** SessionSidebar — 会话列表侧边栏 */

import React, { useEffect, useCallback } from "react";
import { Button, Typography, Popconfirm } from "antd";
import { DeleteOutlined, PlusOutlined } from "@ant-design/icons";
import { useChatStore } from "../../store/chatStore";
import * as chatService from "../../services/chatService";

const { Text } = Typography;

interface Props {
  onNewChat: () => void;
  onSelectSession: (id: string) => void;
}

const SessionSidebar: React.FC<Props> = ({ onNewChat, onSelectSession }) => {
  const { sessions, currentSessionId, setSessions, removeSession } = useChatStore();

  // 初始化时加载会话列表
  const loadSessions = useCallback(async () => {
    try {
      const res = await chatService.listSessions();
      setSessions(res.sessions);
    } catch {
      // 静默失败
    }
  }, [setSessions]);

  useEffect(() => {
    loadSessions();
  }, [loadSessions]);

  const handleDelete = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    try {
      await chatService.deleteSession(id);
      removeSession(id);
    } catch {
      // 静默失败
    }
  };

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

  return (
    <div
      style={{
        width: 260,
        borderRight: "1px solid #e5edf5",
        background: "#f8fafc",
        display: "flex",
        flexDirection: "column",
        flexShrink: 0,
      }}
    >
      {/* 新建对话按钮 */}
      <div style={{ padding: "16px 12px 8px" }}>
        <Button
          block
          icon={<PlusOutlined />}
          onClick={onNewChat}
          style={{
            borderRadius: 6,
            fontWeight: 400,
            border: "1px solid #e5edf5",
            background: "#fff",
            height: 36,
          }}
        >
          新建对话
        </Button>
      </div>

      {/* 会话列表 */}
      <div
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "4px 8px",
        }}
      >
        {sessions.map((session) => (
          <div
            key={session.id}
            onClick={() => onSelectSession(session.id)}
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              padding: "8px 10px",
              marginBottom: 2,
              borderRadius: 6,
              cursor: "pointer",
              background:
                currentSessionId === session.id
                  ? "#eef2ff"
                  : "transparent",
              transition: "background 0.15s",
            }}
            onMouseEnter={(e) => {
              if (currentSessionId !== session.id) {
                e.currentTarget.style.background = "#f1f5f9";
              }
            }}
            onMouseLeave={(e) => {
              if (currentSessionId !== session.id) {
                e.currentTarget.style.background = "transparent";
              }
            }}
          >
            <div style={{ flex: 1, minWidth: 0 }}>
              <Text
                ellipsis
                style={{
                  fontSize: 13,
                  color: currentSessionId === session.id ? "#533afd" : "#273951",
                  fontWeight: currentSessionId === session.id ? 500 : 400,
                  display: "block",
                  lineHeight: "20px",
                }}
              >
                {session.title || "新对话"}
              </Text>
              <Text
                style={{
                  fontSize: 11,
                  color: "#94a3b8",
                  lineHeight: "16px",
                }}
              >
                {formatDate(session.created_at)}
              </Text>
            </div>
            <Popconfirm
              title="删除此对话？"
              onConfirm={(e) => handleDelete(e as React.MouseEvent, session.id)}
              onCancel={(e) => e?.stopPropagation()}
              okText="删除"
              cancelText="取消"
            >
              <Button
                type="text"
                size="small"
                icon={<DeleteOutlined />}
                onClick={(e) => e.stopPropagation()}
                style={{
                  color: "#94a3b8",
                  fontSize: 12,
                  minWidth: 24,
                  width: 24,
                  height: 24,
                }}
              />
            </Popconfirm>
          </div>
        ))}

        {sessions.length === 0 && (
          <div style={{ padding: "24px 0", textAlign: "center" }}>
            <Text style={{ fontSize: 12, color: "#94a3b8" }}>
              暂无对话
            </Text>
          </div>
        )}
      </div>
    </div>
  );
};

export default SessionSidebar;
