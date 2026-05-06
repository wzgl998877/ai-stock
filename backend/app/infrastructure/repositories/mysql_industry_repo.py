"""MySQL Industry Repository — 按层级/code/名称查询"""

from typing import Optional, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.industry import Industry
from app.domain.repositories.industry_repo import IndustryRepository
from app.infrastructure.db.models import Industry as IndustryModel
from app.infrastructure.db.models import StockIndustry, Stock


def _to_entity(model: IndustryModel) -> Industry:
    return Industry(
        industry_code=model.industry_code,
        name=model.name,
        level=model.level,
        parent_code=model.parent_code,
        display_order=model.display_order,
    )


class MySQLIndustryRepository(IndustryRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_code(self, industry_code: str) -> Optional[Industry]:
        stmt = select(IndustryModel).where(
            IndustryModel.industry_code == industry_code,
            IndustryModel.deleted == "0",
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return _to_entity(model) if model else None

    async def list_by_level(self, level: int) -> List[Industry]:
        stmt = (
            select(IndustryModel)
            .where(IndustryModel.level == level, IndustryModel.deleted == "0")
            .order_by(IndustryModel.display_order)
        )
        result = await self.session.execute(stmt)
        return [_to_entity(m) for m in result.scalars().all()]

    async def list_by_parent(self, parent_code: str) -> List[Industry]:
        stmt = (
            select(IndustryModel)
            .where(IndustryModel.parent_code == parent_code, IndustryModel.deleted == "0")
            .order_by(IndustryModel.display_order)
        )
        result = await self.session.execute(stmt)
        return [_to_entity(m) for m in result.scalars().all()]

    async def list_all_level1(self) -> List[Industry]:
        return await self.list_by_level(1)

    async def find_by_name(self, name: str) -> Optional[Industry]:
        stmt = select(IndustryModel).where(
            IndustryModel.name == name,
            IndustryModel.deleted == "0",
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return _to_entity(model) if model else None

    async def get_stocks_by_industry(self, industry_code: str) -> List[dict]:
        """获取行业内的所有股票"""
        stmt = (
            select(
                Stock.stock_code,
                Stock.name.label("stock_name"),
                StockIndustry.industry_code,
            )
            .join(Stock, StockIndustry.stock_code == Stock.stock_code)
            .where(
                StockIndustry.industry_code == industry_code,
                StockIndustry.deleted == "0",
                Stock.is_active == True,
            )
            .order_by(Stock.stock_code)
        )
        result = await self.session.execute(stmt)
        rows = result.all()
        return [
            {
                "stock_code": row.stock_code,
                "stock_name": row.stock_name,
                "industry_code": row.industry_code,
            }
            for row in rows
        ]
