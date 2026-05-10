/** Auth API Service */

import api from "./api";

export interface UserInfo {
  user_id: string;
  user_account: string;
  user_name: string | null;
  nick_name: string | null;
}

/** 用户登录 — 用户名 + 密码 */
export async function login(userName: string, password: string): Promise<UserInfo> {
  const res = await api.post("/api/auth/login", { user_name: userName, password });
  return res.data;
}

/** 用户注册 — 用户名 + 邮箱，系统自动发送初始密码 */
export async function register(
  userName: string,
  email: string
): Promise<UserInfo> {
  const res = await api.post("/api/auth/register", { user_name: userName, email });
  return res.data;
}

/** 发送密码重置验证码 */
export async function sendResetCode(email: string): Promise<{ message: string; code?: string }> {
  const res = await api.post("/api/auth/forgot-password/send-code", { email });
  return res.data;
}

/** 重置密码 */
export async function resetPassword(params: {
  email: string;
  code: string;
  new_password: string;
  confirm_password: string;
}): Promise<{ message: string }> {
  const res = await api.post("/api/auth/forgot-password/reset", params);
  return res.data;
}

/** 修改密码 */
export async function changePassword(params: {
  old_password: string;
  new_password: string;
  confirm_password: string;
}): Promise<{ message: string }> {
  const res = await api.post("/api/auth/change-password", params);
  return res.data;
}

/** 获取当前用户信息 */
export async function getCurrentUser(): Promise<UserInfo> {
  const res = await api.get("/api/auth/me");
  return res.data;
}
