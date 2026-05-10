"""认证相关 DTO"""

from typing import Optional

from pydantic import BaseModel, EmailStr


class RegisterRequest(BaseModel):
    user_name: str
    email: str


class LoginRequest(BaseModel):
    user_name: str
    password: str


class SendResetCodeRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    email: str
    code: str
    new_password: str
    confirm_password: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str
    confirm_password: str


class UserInfoResponse(BaseModel):
    user_id: str
    user_account: str
    user_name: Optional[str] = None
    nick_name: Optional[str] = None
