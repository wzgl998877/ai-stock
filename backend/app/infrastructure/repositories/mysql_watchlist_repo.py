"""MySQL Repository implementation for watchlist (自选股)."""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.watchlist import WatchlistGroup, WatchlistItem
from app.domain.repositories.watchlist_repo import WatchlistRepository
from app.infrastructure.db.models import WatchlistGroupModel, WatchlistItemModel


def _group_to_entity(model: WatchlistGroupModel) -> WatchlistGroup:
    """ORM Model -> Domain Entity"""
    return WatchlistGroup(
        id=model.id,
        user_id=model.user_id,
        name=model.name,
        display_order=model.display_order,
        is_default=model.is_default,
        create_time=model.create_time,
        update_time=model.update_time,
    )


def _item_to_entity(model: WatchlistItemModel) -> WatchlistItem:
    """ORM Model -> Domain Entity"""
    return WatchlistItem(
        id=model.id,
        group_id=model.group_id,
        stock_code=model.stock_code,
        stock_name=model.stock_name,
        add_time=model.add_time,
        create_time=model.create_time,
    )


class MySQLWatchlistRepository(WatchlistRepository):
    """MySQL implementation of WatchlistRepository"""

    def __init__(self, session: AsyncSession):
        self.session = session

    # --- Group operations ---

    async def get_groups(self, user_id: str) -> List[WatchlistGroup]:
        stmt = (
            select(WatchlistGroupModel)
            .where(WatchlistGroupModel.user_id == user_id)
            .order_by(WatchlistGroupModel.display_order, WatchlistGroupModel.id)
        )
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return [_group_to_entity(m) for m in models]

    async def get_group_by_id(self, group_id: int) -> Optional[WatchlistGroup]:
        stmt = select(WatchlistGroupModel).where(WatchlistGroupModel.id == group_id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return _group_to_entity(model) if model else None

    async def create_group(self, group: WatchlistGroup) -> WatchlistGroup:
        model = WatchlistGroupModel(
            user_id=group.user_id,
            name=group.name,
            display_order=group.display_order,
            is_default=group.is_default,
        )
        self.session.add(model)
        await self.session.flush()
        return _group_to_entity(model)

    async def update_group(self, group: WatchlistGroup) -> WatchlistGroup:
        stmt = select(WatchlistGroupModel).where(WatchlistGroupModel.id == group.id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            raise ValueError(f"WatchlistGroup id={group.id} not found")
        model.name = group.name
        model.display_order = group.display_order
        model.update_time = datetime.now()
        await self.session.flush()
        return _group_to_entity(model)

    async def delete_group(self, group_id: int) -> None:
        # CASCADE will delete associated items automatically
        stmt = delete(WatchlistGroupModel).where(WatchlistGroupModel.id == group_id)
        await self.session.execute(stmt)
        await self.session.flush()

    async def count_groups(self, user_id: str) -> int:
        stmt = select(func.count()).select_from(WatchlistGroupModel).where(
            WatchlistGroupModel.user_id == user_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    # --- Item operations ---

    async def get_items(self, group_id: int) -> List[WatchlistItem]:
        stmt = (
            select(WatchlistItemModel)
            .where(WatchlistItemModel.group_id == group_id)
            .order_by(WatchlistItemModel.add_time.desc())
        )
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return [_item_to_entity(m) for m in models]

    async def add_item(self, item: WatchlistItem) -> WatchlistItem:
        """添加股票到分组（幂等：如果已存在则直接返回）"""
        existing = await self.find_item(item.group_id, item.stock_code)
        if existing:
            return existing

        model = WatchlistItemModel(
            group_id=item.group_id,
            stock_code=item.stock_code,
            stock_name=item.stock_name,
        )
        self.session.add(model)
        await self.session.flush()
        return _item_to_entity(model)

    async def remove_item(self, group_id: int, stock_code: str) -> None:
        stmt = delete(WatchlistItemModel).where(
            WatchlistItemModel.group_id == group_id,
            WatchlistItemModel.stock_code == stock_code,
        )
        await self.session.execute(stmt)
        await self.session.flush()

    async def find_item(self, group_id: int, stock_code: str) -> Optional[WatchlistItem]:
        stmt = select(WatchlistItemModel).where(
            WatchlistItemModel.group_id == group_id,
            WatchlistItemModel.stock_code == stock_code,
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return _item_to_entity(model) if model else None

    async def count_items(self, group_id: int) -> int:
        stmt = select(func.count()).select_from(WatchlistItemModel).where(
            WatchlistItemModel.group_id == group_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()
