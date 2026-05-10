"""认证路由 — 注册 / 登录 / 忘记密码 / 当前用户"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.dtos.auth_dto import (
    RegisterRequest, LoginRequest, UserInfoResponse,
    SendResetCodeRequest, ResetPasswordRequest,
    ChangePasswordRequest,
)
from app.application.use_cases.auth_use_case import AuthUseCase
from app.core.database import get_db
from app.core.deps import CurrentUser, get_current_user
from app.infrastructure.repositories.mysql_user_repo import MySQLUserRepository

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _to_response(user) -> UserInfoResponse:
    return UserInfoResponse(
        user_id=user.user_id,
        user_account=user.user_account,
        user_name=user.user_name,
        nick_name=user.nick_name,
    )


@router.post("/register", response_model=UserInfoResponse)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """注册新用户 — 用户名 + 邮箱，系统发送初始密码"""
    repo = MySQLUserRepository(db)
    use_case = AuthUseCase(repo)
    user = await use_case.register(body.user_name, body.email)
    await db.commit()
    return _to_response(user)


@router.post("/login", response_model=UserInfoResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    """用户名 + 密码登录"""
    repo = MySQLUserRepository(db)
    use_case = AuthUseCase(repo)
    user = await use_case.login(body.user_name, body.password)
    await db.commit()
    return _to_response(user)


@router.post("/forgot-password/send-code")
async def send_reset_code(body: SendResetCodeRequest, db: AsyncSession = Depends(get_db)):
    """发送密码重置验证码"""
    repo = MySQLUserRepository(db)
    use_case = AuthUseCase(repo)
    code = use_case.send_reset_code(body.email)
    return {"message": "验证码已发送到邮箱", "code": code}  # code 仅开发调试用，生产应删除


@router.post("/forgot-password/reset")
async def reset_password(body: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    """验证码 + 重置密码"""
    repo = MySQLUserRepository(db)
    use_case = AuthUseCase(repo)
    await use_case.reset_password(body.email, body.code, body.new_password, body.confirm_password)
    # 清除验证码
    from app.application.use_cases.auth_use_case import _reset_codes
    _reset_codes.pop(body.email, None)
    await db.commit()
    return {"message": "密码已重置，请使用新密码登录"}


@router.post("/change-password")
async def change_password(body: ChangePasswordRequest, current_user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """修改密码 — 需验证原密码"""
    repo = MySQLUserRepository(db)
    use_case = AuthUseCase(repo)
    await use_case.change_password(current_user.user_id, body.old_password, body.new_password, body.confirm_password)
    await db.commit()
    return {"message": "密码修改成功"}


@router.get("/me", response_model=UserInfoResponse)
async def get_me(current_user: CurrentUser = Depends(get_current_user)):
    """获取当前用户信息（从请求头解析）"""
    return UserInfoResponse(
        user_id=current_user.user_id,
        user_account=current_user.user_account,
        user_name=current_user.user_name,
    )
