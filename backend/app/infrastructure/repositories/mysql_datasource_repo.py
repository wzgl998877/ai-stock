"""MySQL Data Source Repository — 操作 t_datasource_config"""

import os
from typing import Optional, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from cryptography.fernet import Fernet, InvalidToken

from app.domain.models.stock_data import DataSourceConfig, SourceType
from app.domain.repositories.datasource_repo import DataSourceRepository
from app.infrastructure.db.models import DataSourceConfigModel
from app.core.config import settings


def _get_fernet() -> Optional[Fernet]:
    """获取 Fernet 加密实例，如果未配置密钥则返回 None（明文模式）。"""
    key = settings.datasource_encryption_key or os.environ.get("DATASOURCE_ENCRYPTION_KEY", "")
    if not key:
        return None
    return Fernet(key.encode())


def _encrypt_api_key(api_key: Optional[str]) -> Optional[str]:
    """加密 api_key。如果未配置加密密钥，则明文存储。"""
    if api_key is None:
        return None
    fernet = _get_fernet()
    if fernet is None:
        return api_key
    try:
        return fernet.encrypt(api_key.encode()).decode()
    except Exception:
        # 加密失败时降级为明文存储
        return api_key


def _decrypt_api_key(encrypted_key: Optional[str]) -> Optional[str]:
    """解密 api_key。如果未配置加密密钥，则直接返回（明文模式）。"""
    if encrypted_key is None:
        return None
    fernet = _get_fernet()
    if fernet is None:
        return encrypted_key
    try:
        return fernet.decrypt(encrypted_key.encode()).decode()
    except InvalidToken:
        # 可能为旧明文数据，直接返回
        return encrypted_key


def _to_entity(model: DataSourceConfigModel) -> DataSourceConfig:
    """ORM model → Domain entity"""
    return DataSourceConfig(
        id=model.id,
        source_type=SourceType(model.source_type),
        api_key=_decrypt_api_key(model.api_key),
        is_enabled=model.is_enabled,
        priority=model.priority,
        config_json=model.config_json,
        create_time=model.create_time,
        update_time=model.update_time,
    )


class MySQLDataSourceRepository(DataSourceRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all(self) -> List[DataSourceConfig]:
        stmt = select(DataSourceConfigModel).order_by(DataSourceConfigModel.priority)
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return [_to_entity(m) for m in models]

    async def get_by_type(self, source_type: SourceType) -> Optional[DataSourceConfig]:
        stmt = select(DataSourceConfigModel).where(
            DataSourceConfigModel.source_type == source_type.value
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return _to_entity(model) if model else None

    async def save(self, config: DataSourceConfig) -> DataSourceConfig:
        encrypted_key = _encrypt_api_key(config.api_key)

        # 先查找是否已存在
        stmt = select(DataSourceConfigModel).where(
            DataSourceConfigModel.source_type == config.source_type.value
        )
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            # 更新已有记录
            existing.api_key = encrypted_key
            existing.is_enabled = config.is_enabled
            existing.priority = config.priority
            existing.config_json = config.config_json
        else:
            # 创建新记录
            model = DataSourceConfigModel(
                source_type=config.source_type.value,
                api_key=encrypted_key,
                is_enabled=config.is_enabled,
                priority=config.priority,
                config_json=config.config_json,
            )
            self.session.add(model)

        await self.session.flush()

        # 返回更新后的实体
        stmt = select(DataSourceConfigModel).where(
            DataSourceConfigModel.source_type == config.source_type.value
        )
        result = await self.session.execute(stmt)
        saved = result.scalar_one()
        return _to_entity(saved)

    async def update(self, source_type: SourceType, **kwargs) -> DataSourceConfig:
        stmt = select(DataSourceConfigModel).where(
            DataSourceConfigModel.source_type == source_type.value
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            raise ValueError(f"DataSourceConfig not found: {source_type.value}")

        # 如果 kwargs 中包含 api_key，需要加密
        if "api_key" in kwargs:
            kwargs["api_key"] = _encrypt_api_key(kwargs["api_key"])

        for field_name, value in kwargs.items():
            if hasattr(model, field_name):
                setattr(model, field_name, value)

        await self.session.flush()

        # 重新查询以获取最新数据
        stmt = select(DataSourceConfigModel).where(
            DataSourceConfigModel.source_type == source_type.value
        )
        result = await self.session.execute(stmt)
        updated = result.scalar_one()
        return _to_entity(updated)

    async def delete(self, source_type: SourceType) -> bool:
        stmt = select(DataSourceConfigModel).where(
            DataSourceConfigModel.source_type == source_type.value
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            return False
        await self.session.delete(model)
        await self.session.flush()
        return True

    async def is_configured(self, source_type: SourceType) -> bool:
        stmt = select(DataSourceConfigModel).where(
            DataSourceConfigModel.source_type == source_type.value,
            DataSourceConfigModel.is_enabled == True,  # noqa: E712
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            return False

        config = _to_entity(model)
        return config.is_configured()
