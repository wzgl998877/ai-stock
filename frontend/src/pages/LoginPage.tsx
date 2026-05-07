/** LoginPage — 全屏独立登录/注册页面 */

import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Input, Button, message } from "antd";
import { UserOutlined, LockOutlined, MailOutlined } from "@ant-design/icons";
import * as authService from "../services/authService";
import { useAuthStore } from "../store/authStore";

const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const { setUser } = useAuthStore();

  const [mode, setMode] = useState<"login" | "register">("login");
  const [loading, setLoading] = useState(false);

  // 登录表单
  const [loginUserName, setLoginUserName] = useState("");
  const [loginPassword, setLoginPassword] = useState("");

  // 注册表单
  const [regUserName, setRegUserName] = useState("");
  const [regEmail, setRegEmail] = useState("");

  const validateEmail = (email: string) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);

  const handleLogin = async () => {
    if (!loginUserName.trim()) {
      message.error("请输入用户名");
      return;
    }
    if (!loginPassword) {
      message.error("请输入密码");
      return;
    }
    setLoading(true);
    try {
      const user = await authService.login(loginUserName.trim(), loginPassword);
      setUser(user);
      message.success("登录成功");
      navigate("/analysis", { replace: true });
    } catch (err: any) {
      message.error(err.message || "登录失败，请重试");
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async () => {
    if (!regUserName.trim()) {
      message.error("请输入用户名");
      return;
    }
    if (regUserName.trim().length < 2) {
      message.error("用户名至少2个字符");
      return;
    }
    if (!regEmail.trim()) {
      message.error("请输入邮箱");
      return;
    }
    if (!validateEmail(regEmail.trim())) {
      message.error("请输入有效的邮箱地址");
      return;
    }
    setLoading(true);
    try {
      const user = await authService.register(regUserName.trim(), regEmail.trim());
      setUser(user);
      message.success("注册成功！初始密码已发送到您的邮箱，请妥善保存");
      navigate("/analysis", { replace: true });
    } catch (err: any) {
      message.error(err.message || "注册失败，请重试");
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !loading) {
      if (mode === "login") handleLogin();
      else handleRegister();
    }
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "#ffffff",
      }}
    >
      <div
        style={{
          width: 420,
          padding: "48px 40px 40px",
          borderRadius: 12,
          boxShadow: "0 4px 24px rgba(0, 42, 92, 0.08)",
          border: "1px solid #e5edf5",
        }}
      >
        {/* 品牌标题 */}
        <div style={{ textAlign: "center", marginBottom: 40 }}>
          <div
            className="brand-gradient"
            style={{
              width: 48,
              height: 48,
              borderRadius: 10,
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              color: "#fff",
              fontSize: 20,
              fontWeight: 300,
              marginBottom: 16,
            }}
          >
            AI
          </div>
          <h1
            style={{
              fontSize: 28,
              fontWeight: 300,
              color: "#061b31",
              margin: 0,
              lineHeight: 1.3,
            }}
          >
            AI 投研助手
          </h1>
          <p style={{ fontSize: 14, color: "#94a3b8", marginTop: 8 }}>
            Smart Investment Research
          </p>
        </div>

        {/* 模式切换按钮 */}
        <div style={{ display: "flex", gap: 8, marginBottom: 24 }}>
          <Button
            type={mode === "login" ? "primary" : "default"}
            size="large"
            block
            onClick={() => setMode("login")}
            style={{ height: 40 }}
          >
            登录
          </Button>
          <Button
            type={mode === "register" ? "primary" : "default"}
            size="large"
            block
            onClick={() => setMode("register")}
            style={{ height: 40 }}
          >
            注册
          </Button>
        </div>

        {/* 登录表单 */}
        {mode === "login" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <Input
              size="large"
              prefix={<UserOutlined style={{ color: "#b0b8c4" }} />}
              placeholder="请输入用户名"
              value={loginUserName}
              onChange={(e) => setLoginUserName(e.target.value)}
              onKeyDown={handleKeyDown}
            />
            <Input.Password
              size="large"
              prefix={<LockOutlined style={{ color: "#b0b8c4" }} />}
              placeholder="请输入密码"
              value={loginPassword}
              onChange={(e) => setLoginPassword(e.target.value)}
              onKeyDown={handleKeyDown}
            />
            <div style={{ textAlign: "right" }}>
              <Button
                type="link"
                size="small"
                onClick={() => navigate("/forgot-password")}
                style={{ padding: 0, height: "auto" }}
              >
                忘记密码？
              </Button>
            </div>
            <Button
              type="primary"
              size="large"
              block
              loading={loading}
              onClick={handleLogin}
              style={{ height: 44, fontWeight: 500 }}
            >
              登录
            </Button>
          </div>
        )}

        {/* 注册表单 */}
        {mode === "register" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <Input
              size="large"
              prefix={<UserOutlined style={{ color: "#b0b8c4" }} />}
              placeholder="请输入用户名（至少2个字符）"
              value={regUserName}
              onChange={(e) => setRegUserName(e.target.value)}
              onKeyDown={handleKeyDown}
            />
            <Input
              size="large"
              prefix={<MailOutlined style={{ color: "#b0b8c4" }} />}
              placeholder="请输入邮箱（初始密码将发送到此邮箱）"
              value={regEmail}
              onChange={(e) => setRegEmail(e.target.value)}
              onKeyDown={handleKeyDown}
            />
            <Button
              type="primary"
              size="large"
              block
              loading={loading}
              onClick={handleRegister}
              style={{ height: 44, fontWeight: 500 }}
            >
              注册
            </Button>
            <p style={{ fontSize: 12, color: "#98a2b3", margin: 0, textAlign: "center" }}>
              注册后系统将自动发送初始密码到您的邮箱
            </p>
          </div>
        )}

        {/* 底部提示 */}
        <p
          style={{
            textAlign: "center",
            fontSize: 12,
            color: "#98a2b3",
            marginTop: 32,
            lineHeight: 1.6,
          }}
        >
          本工具仅供投研参考，不构成任何投资建议
        </p>
      </div>
    </div>
  );
};

export default LoginPage;
