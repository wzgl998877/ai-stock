"""WatchlistUseCase — 自选股管理用例"""

from __future__ import annotations

import logging
from typing import List, Optional

from app.domain.entities.watchlist import WatchlistGroup, WatchlistItem
from app.domain.repositories.watchlist_repo import WatchlistRepository
from app.domain.repositories.stock_data_repo import StockDataRepository

logger = logging.getLogger(__name__)

DEFAULT_GROUP_NAME = "默认分组"


class WatchlistUseCase:
    """自选股管理用例：包含首次访问自动创建默认分组逻辑"""

    def __init__(self, watchlist_repo: WatchlistRepository):
        self.watchlist_repo = watchlist_repo

    async def _fetch_live_quote_price(self, stock_code: str) -> Optional[float]:
        """通过分时数据源获取最新价格（与分时图同一数据源）。

        失败时返回 None，不影响添加自选股主流程。
        """
        try:
            from app.infrastructure.market.tencent_client import TencentMinuteClient
            from app.infrastructure.market.sina_client import SinaMinuteClient

            # 优先腾讯，失败 fallback 新浪
            sources = [TencentMinuteClient(), SinaMinuteClient()]
            for client in sources:
                try:
                    data = await client.fetch(stock_code)
                    if data:
                        # 最后一条的 price 就是当前最新价
                        return float(data[-1]["price"])
                except Exception as e:
                    logger.warning("数据源 %s 获取行情失败: %s", type(client).__name__, e)
                    continue
        except Exception as e:
            logger.warning("拉取股票 %s 实时行情失败: %s", stock_code, e)
        return None

    async def _ensure_default_group(self, user_id: str) -> WatchlistGroup:
        """确保用户至少有一个默认分组，首次访问时自动创建"""
        groups = await self.watchlist_repo.get_groups(user_id)
        for g in groups:
            if g.is_default:
                return g

        # 没有默认分组，创建一个
        default_group = WatchlistGroup(
            user_id=user_id,
            name=DEFAULT_GROUP_NAME,
            display_order=0,
            is_default=True,
        )
        return await self.watchlist_repo.create_group(default_group)

    async def get_groups(self, user_id: str) -> List[WatchlistGroup]:
        """获取用户所有分组（含股票数量）"""
        await self._ensure_default_group(user_id)
        groups = await self.watchlist_repo.get_groups(user_id)

        # 填充 stock_count
        for group in groups:
            group.stock_count = await self.watchlist_repo.count_items(group.id)

        return groups

    async def create_group(self, user_id: str, name: str) -> WatchlistGroup:
        """创建新分组"""
        if not name or len(name) > 10:
            raise ValueError("分组名称须1-10个字符")

        count = await self.watchlist_repo.count_groups(user_id)

        group = WatchlistGroup(
            user_id=user_id,
            name=name,
            display_order=count,
            is_default=False,
        )
        return await self.watchlist_repo.create_group(group)

    async def update_group(self, group_id: int, name: Optional[str] = None, display_order: Optional[int] = None) -> WatchlistGroup:
        """更新分组"""
        group = await self.watchlist_repo.get_group_by_id(group_id)
        if group is None:
            raise ValueError(f"分组 id={group_id} 不存在")

        if name is not None:
            group.name = name
        if display_order is not None:
            group.display_order = display_order

        return await self.watchlist_repo.update_group(group)

    async def delete_group(self, group_id: int) -> None:
        """删除分组（默认分组不可删除）"""
        group = await self.watchlist_repo.get_group_by_id(group_id)
        if group is None:
            raise ValueError(f"分组 id={group_id} 不存在")
        if group.is_default:
            raise ValueError("默认分组不可删除")

        await self.watchlist_repo.delete_group(group_id)

    async def add_stock(self, user_id: str, group_id: int, stock_code: str, stock_name: str, add_price: Optional[float] = None) -> WatchlistItem:
        """添加股票到分组"""
        # 验证分组存在且属于该用户
        group = await self.watchlist_repo.get_group_by_id(group_id)
        if group is None:
            raise ValueError(f"分组 id={group_id} 不存在")
        if group.user_id != user_id:
            raise ValueError("无权操作此分组")

        # 如果未传自选价，从数据源实时拉取
        if add_price is None:
            add_price = await self._fetch_live_quote_price(stock_code)

        item = WatchlistItem(
            group_id=group_id,
            stock_code=stock_code,
            stock_name=stock_name,
            add_price=add_price,
        )
        return await self.watchlist_repo.add_item(item)

    async def remove_stock(self, user_id: str, group_id: int, stock_code: str) -> None:
        """从分组移除股票"""
        group = await self.watchlist_repo.get_group_by_id(group_id)
        if group is None:
            raise ValueError(f"分组 id={group_id} 不存在")
        if group.user_id != user_id:
            raise ValueError("无权操作此分组")

        await self.watchlist_repo.remove_item(group_id, stock_code)

    async def get_items(self, user_id: str, group_id: int) -> List[WatchlistItem]:
        """获取分组内股票"""
        group = await self.watchlist_repo.get_group_by_id(group_id)
        if group is None:
            raise ValueError(f"分组 id={group_id} 不存在")
        if group.user_id != user_id:
            raise ValueError("无权访问此分组")

        return await self.watchlist_repo.get_items(group_id)
