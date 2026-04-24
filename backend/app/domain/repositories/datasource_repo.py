"""Repository interfaces for data source configuration."""

from abc import ABC, abstractmethod
from typing import Optional, List
from app.domain.models.stock_data import DataSourceConfig, SourceType


class DataSourceRepository(ABC):
    @abstractmethod
    async def get_all(self) -> List[DataSourceConfig]:
        """获取所有数据源配置"""
        ...

    @abstractmethod
    async def get_by_type(self, source_type: SourceType) -> Optional[DataSourceConfig]:
        """根据数据源类型获取配置"""
        ...

    @abstractmethod
    async def save(self, config: DataSourceConfig) -> DataSourceConfig:
        """保存配置（新增或更新）"""
        ...

    @abstractmethod
    async def update(self, source_type: SourceType, **kwargs) -> DataSourceConfig:
        """更新指定数据源的配置字段"""
        ...

    @abstractmethod
    async def delete(self, source_type: SourceType) -> bool:
        """删除数据源配置"""
        ...

    @abstractmethod
    async def is_configured(self, source_type: SourceType) -> bool:
        """检查数据源是否已配置有效凭证"""
        ...
