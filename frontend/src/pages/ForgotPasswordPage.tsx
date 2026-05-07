/** ForgotPasswordPage — 忘记密码页面 */

import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Input, Button, message } from "antd";
import { MailOutlined, LockOutlined, SafetyOutlined } from "@ant-design/icons";
import * as authService from "../services/authService";

type Step = "send_code" | "reset";

const ForgotPasswordPage: React.FC = () => {
  const navigate = useNavigate();
  const [step, setStep] = useState<Step>("send_code");
  const [loading, setLoading] = useState(false);

  // Step 1
  const [email, setEmail] = useState("");
  const [codeSent, setCodeSent] = useState(false);
  const [countdown, setCountdown] = useState(0);

  // Step 2
  const [code, setCode] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  const validateEmail = (e: string) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(e);

  const handleSendCode = async () => {
    if (!email.trim()) {
      message.error("请输入邮箱");
      return;
    }
    if (!validateEmail(email.trim())) {
      message.error("请输入有效的邮箱地址");
      return;
    }
    setLoading(true);
    try {
      const res = await authService.sendResetCode(email.trim());
      message.success(res.message);
      setCodeSent(true);
      // 开始倒计时
      setCountdown(60);
      const timer = setInterval(() => {
        setCountdown((prev) => {
          if (prev <= 1) {
            clearInterval(timer);
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    } catch (err: any) {
      message.error(err.message || "发送失败，请重试");
    } finally {
      setLoading(false);
    }
  };

  const handleReset = async () => {
    if (!code.trim()) {
      message.error("请输入验证码");
      return;
    }
    if (!newPassword || newPassword.length < 6) {
      message.error("密码长度不能少于6位");
      return;
    }
    if (!confirmPassword) {
      message.error("请再次输入密码");
      return;
    }
    if (newPassword !== confirmPassword) {
      message.error("两次输入的密码不一致");
      return;
    }
    setLoading(true);
    try {
      const res = await authService.resetPassword({
        email: email.trim(),
        code,
        new_password: newPassword,
        confirm_password: confirmPassword,
      });
      message.success(res.message);
      navigate("/login", { replace: true });
    } catch (err: any) {
      message.error(err.message || "重置失败，请重试");
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !loading) {
      if (step === "send_code") handleSendCode();
      else handleReset();
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
        {/* 标题 */}
        <div style={{ textAlign: "center", marginBottom: 40 }}>
          <div
            style={{
              width: 48,
              height: 48,
              borderRadius: 10,
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              background: "#0ea5e9",
              color: "#fff",
              fontSize: 20,
              fontWeight: 300,
              marginBottom: 16,
            }}
          >
            <SafetyOutlined />
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
            {step === "send_code" ? "忘记密码" : "重置密码"}
          </h1>
          <p style={{ fontSize: 14, color: "#94a3b8", marginTop: 8 }}>
            {step === "send_code"
              ? "输入注册邮箱，我们将发送验证码"
              : "输入验证码和新密码"}
          </p>
        </div>

        {/* Step 1: 发送验证码 */}
        {step === "send_code" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <Input
              size="large"
              prefix={<MailOutlined style={{ color: "#b0b8c4" }} />}
              placeholder="请输入注册邮箱"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              onKeyDown={handleKeyDown}
            />
            <Button
              type="primary"
              size="large"
              block
              loading={loading}
              onClick={handleSendCode}
              style={{ height: 44, fontWeight: 500 }}
            >
              {countdown > 0 ? `${countdown}s 后重新发送` : "发送验证码"}
            </Button>
            {codeSent && (
              <p style={{ fontSize: 13, color: "#15be53", margin: 0, textAlign: "center" }}>
                验证码已发送，请查收邮箱
              </p>
            )}
            {codeSent && (
              <Button
                type="link"
                onClick={() => setStep("reset")}
                style={{ marginTop: 8 }}
              >
                我已收到验证码，继续重置密码 →
              </Button>
            )}
          </div>
        )}

        {/* Step 2: 验证码 + 新密码 */}
        {step === "reset" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <Input
              size="large"
              prefix={<SafetyOutlined style={{ color: "#b0b8c4" }} />}
              placeholder="请输入验证码"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              onKeyDown={handleKeyDown}
            />
            <Input.Password
              size="large"
              prefix={<LockOutlined style={{ color: "#b0b8c4" }} />}
              placeholder="新密码（至少6位）"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              onKeyDown={handleKeyDown}
            />
            <Input.Password
              size="large"
              prefix={<LockOutlined style={{ color: "#b0b8c4" }} />}
              placeholder="确认新密码"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              onKeyDown={handleKeyDown}
            />
            <Button
              type="primary"
              size="large"
              block
              loading={loading}
              onClick={handleReset}
              style={{ height: 44, fontWeight: 500 }}
            >
              重置密码
            </Button>
            <Button
              type="link"
              onClick={() => setStep("send_code")}
              style={{ marginTop: 8 }}
            >
              重新发送验证码
            </Button>
          </div>
        )}

        {/* 底部 */}
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

export default ForgotPasswordPage;
