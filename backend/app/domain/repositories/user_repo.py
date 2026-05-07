"""用户仓储抽象接口"""

from abc import ABC, abstractmethod
from typing import Optional

from app.domain.entities.user import User


class UserRepository(ABC):
    """用户数据访问接口"""

    @abstractmethod
    async def find_by_account(self, account: str) -> Optional[User]:
        """根据账号查找用户"""

    @abstractmethod
    async def find_by_email(self, email: str) -> Optional[User]:
        """根据邮箱查找用户"""

    @abstractmethod
    async def find_by_user_id(self, user_id: str) -> Optional[User]:
        """根据用户ID查找用户"""

    @abstractmethod
    async def create(self, user: User) -> User:
        """创建用户"""

    @abstractmethod
    async def update_last_login(self, user_id: str) -> None:
        """更新最后登录时间"""

    @abstractmethod
    async def update_password(self, user_id: str, hashed_password: str) -> None:
        """更新密码"""
