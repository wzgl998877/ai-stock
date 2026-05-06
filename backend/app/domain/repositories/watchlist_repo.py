"""自选股Repository接口"""

from abc import ABC, abstractmethod
from typing import List, Optional

from app.domain.entities.watchlist import WatchlistGroup, WatchlistItem


class WatchlistRepository(ABC):
    """自选股数据访问接口"""

    @abstractmethod
    async def get_groups(self, user_id: str) -> List[WatchlistGroup]:
        """获取用户所有分组"""
        ...

    @abstractmethod
    async def get_group_by_id(self, group_id: int) -> Optional[WatchlistGroup]:
        """根据ID获取分组"""
        ...

    @abstractmethod
    async def create_group(self, group: WatchlistGroup) -> WatchlistGroup:
        """创建分组"""
        ...

    @abstractmethod
    async def update_group(self, group: WatchlistGroup) -> WatchlistGroup:
        """更新分组"""
        ...

    @abstractmethod
    async def delete_group(self, group_id: int) -> None:
        """删除分组"""
        ...

    @abstractmethod
    async def count_groups(self, user_id: str) -> int:
        """统计用户分组数量"""
        ...

    @abstractmethod
    async def get_items(self, group_id: int) -> List[WatchlistItem]:
        """获取分组内所有股票"""
        ...

    @abstractmethod
    async def add_item(self, item: WatchlistItem) -> WatchlistItem:
        """添加股票到分组（幂等）"""
        ...

    @abstractmethod
    async def remove_item(self, group_id: int, stock_code: str) -> None:
        """从分组移除股票"""
        ...

    @abstractmethod
    async def find_item(self, group_id: int, stock_code: str) -> Optional[WatchlistItem]:
        """查找分组内是否已有某股票"""
        ...

    @abstractmethod
    async def count_items(self, group_id: int) -> int:
        """统计分组内股票数量"""
        ...
