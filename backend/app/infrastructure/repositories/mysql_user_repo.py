"""MySQL 用户仓储实现"""

from datetime import datetime
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.user import User as UserEntity
from app.domain.repositories.user_repo import UserRepository
from app.infrastructure.db.models import User as UserModel


class MySQLUserRepository(UserRepository):
    """MySQL 用户仓储"""

    def __init__(self, db: AsyncSession):
        self._db = db

    def _to_entity(self, model: UserModel) -> UserEntity:
        """ORM 模型转领域实体"""
        return UserEntity(
            user_id=model.user_id,
            user_account=model.user_account,
            password=model.password,
            user_name=model.user_name,
            email=model.email,
            nick_name=model.nick_name,
            icon_url=model.icon_url,
            gender=model.gender,
            mobile=model.mobile,
            user_type=model.user_type,
            status=model.status,
            last_login=model.last_login,
            create_time=model.create_time,
            update_time=model.update_time,
            deleted=model.deleted,
        )

    async def find_by_account(self, account: str) -> Optional[UserEntity]:
        stmt = select(UserModel).where(
            UserModel.user_account == account,
            UserModel.deleted == "0",
        )
        result = await self._db.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def find_by_email(self, email: str) -> Optional[UserEntity]:
        stmt = select(UserModel).where(
            UserModel.email == email,
            UserModel.deleted == "0",
        )
        result = await self._db.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def find_by_user_id(self, user_id: str) -> Optional[UserEntity]:
        stmt = select(UserModel).where(
            UserModel.user_id == user_id,
            UserModel.deleted == "0",
        )
        result = await self._db.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def create(self, user: UserEntity) -> UserEntity:
        model = UserModel(
            user_id=user.user_id,
            user_account=user.user_account,
            password=user.password,
            user_name=user.user_name,
            email=user.email,
            nick_name=user.nick_name,
            status=user.status,
            user_type=user.user_type,
            deleted="0",
        )
        self._db.add(model)
        await self._db.flush()
        return user

    async def update_last_login(self, user_id: str) -> None:
        stmt = (
            update(UserModel)
            .where(UserModel.user_id == user_id)
            .values(last_login=datetime.now())
        )
        await self._db.execute(stmt)

    async def update_password(self, user_id: str, hashed_password: str) -> None:
        stmt = (
            update(UserModel)
            .where(UserModel.user_id == user_id)
            .values(password=hashed_password)
        )
        await self._db.execute(stmt)
