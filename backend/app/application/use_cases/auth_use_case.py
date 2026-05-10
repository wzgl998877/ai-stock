"""认证用例 — 注册 & 登录 & 忘记密码"""

import random
import time
import uuid

from app.domain.entities.user import User
from app.domain.repositories.user_repo import UserRepository
from app.domain.services.password_hasher import hash_password, verify_password
from app.core.exceptions import InvalidInputError, AuthenticationError
from app.core.email import send_email

DEFAULT_PASSWORD = "123456"

# 验证码存储: {email: (code, expire_time)}
_reset_codes: dict[str, tuple[str, float]] = {}
CODE_EXPIRE = 300  # 5 分钟


class AuthUseCase:
    """认证业务逻辑"""

    def __init__(self, user_repo: UserRepository):
        self._user_repo = user_repo

    async def register(self, user_name: str, email: str) -> User:
        """注册新用户 — 用户名 + 邮箱，系统自动发送初始密码"""
        user_name = user_name.strip()
        if not user_name:
            raise InvalidInputError("用户名不能为空")
        if len(user_name) < 2:
            raise InvalidInputError("用户名至少2个字符")

        email = email.strip()
        if not email:
            raise InvalidInputError("邮箱不能为空")
        if "@" not in email:
            raise InvalidInputError("请输入有效的邮箱地址")

        # 检查用户名唯一性
        existing_user = await self._user_repo.find_by_account(user_name)
        if existing_user:
            raise InvalidInputError("该用户名已被注册")

        # 检查邮箱唯一性
        existing_email = await self._user_repo.find_by_email(email)
        if existing_email:
            raise InvalidInputError("该邮箱已被注册")

        # 加密默认密码
        hashed, salt = hash_password(DEFAULT_PASSWORD)
        password_field = f"{salt}:{hashed}"

        user = User(
            user_id=uuid.uuid4().hex,
            user_account=user_name,
            password=password_field,
            user_name=user_name,
            email=email,
            nick_name=user_name,
            status="0",
            user_type="0",
            deleted="0",
        )
        user = await self._user_repo.create(user)

        # 发送初始密码邮件
        body = f"""
        <h3>欢迎注册 AI 投研助手</h3>
        <p>您的初始密码为：</p>
        <p style="font-size: 24px; font-weight: bold; color: #533afd;">{DEFAULT_PASSWORD}</p>
        <p>请使用用户名 <b>{user_name}</b> 和密码登录后及时修改密码。</p>
        <p>本工具仅供投研参考，不构成任何投资建议。</p>
        """
        send_email(email, "AI 投研助手 — 注册成功", body)

        return user

    async def login(self, user_name: str, password: str) -> User:
        """用户名 + 密码登录"""
        if not user_name or not password:
            raise AuthenticationError("用户名和密码不能为空")

        user = await self._user_repo.find_by_account(user_name.strip())
        if not user:
            raise AuthenticationError("用户名或密码错误")

        # 解析 salt:hash 格式
        parts = user.password.split(":", 1)
        if len(parts) != 2:
            raise AuthenticationError("用户名或密码错误")

        salt, hashed = parts
        if not verify_password(password, hashed, salt):
            raise AuthenticationError("用户名或密码错误")

        # 更新最后登录时间
        await self._user_repo.update_last_login(user.user_id)

        return user

    def send_reset_code(self, email: str) -> str:
        """发送重置验证码"""
        if not email or "@" not in email:
            raise InvalidInputError("请输入有效的邮箱地址")

        code = f"{random.randint(100000, 999999)}"
        _reset_codes[email] = (code, time.time() + CODE_EXPIRE)

        body = f"""
        <h3>密码重置验证</h3>
        <p>您的验证码为：</p>
        <p style="font-size: 32px; font-weight: bold; color: #533afd; letter-spacing: 8px;">{code}</p>
        <p>验证码 5 分钟内有效，如非本人操作请忽略。</p>
        """
        send_email(email, "AI 投研助手 — 密码重置", body)

        return code

    async def reset_password(self, email: str, code: str, new_password: str, confirm_password: str) -> bool:
        """验证码 + 重置密码"""
        email = email.strip()

        if not new_password or len(new_password) < 6:
            raise InvalidInputError("密码长度不能少于6位")

        if new_password != confirm_password:
            raise InvalidInputError("两次输入的密码不一致")

        # 检查用户是否存在（通过邮箱查找）
        user = await self._user_repo.find_by_email(email)
        if not user:
            raise InvalidInputError("该邮箱未注册")

        # 验证验证码
        stored = _reset_codes.get(email)
        if not stored:
            raise InvalidInputError("验证码不存在或已过期，请重新发送")

        stored_code, expire_time = stored
        if time.time() > expire_time:
            _reset_codes.pop(email, None)
            raise InvalidInputError("验证码已过期，请重新发送")

        if code.strip() != stored_code:
            raise InvalidInputError("验证码错误")

        # 重置密码
        hashed, salt = hash_password(new_password)
        password_field = f"{salt}:{hashed}"
        await self._user_repo.update_password(user.user_id, password_field)
        return True

    async def change_password(
        self, user_id: str, old_password: str, new_password: str, confirm_password: str
    ) -> bool:
        """修改密码 — 需验证原密码"""
        if not new_password or len(new_password) < 6:
            raise InvalidInputError("密码长度不能少于6位")

        if new_password != confirm_password:
            raise InvalidInputError("两次输入的密码不一致")

        user = await self._user_repo.find_by_user_id(user_id)
        if not user:
            raise InvalidInputError("用户不存在")

        # 验证原密码
        parts = user.password.split(":", 1)
        if len(parts) != 2:
            raise InvalidInputError("原密码格式错误")

        salt, hashed = parts
        if not verify_password(old_password, hashed, salt):
            raise InvalidInputError("原密码错误")

        # 设置新密码
        new_hashed, new_salt = hash_password(new_password)
        password_field = f"{new_salt}:{new_hashed}"
        await self._user_repo.update_password(user.user_id, password_field)
        return True
