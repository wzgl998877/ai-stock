"""MySQL Repository implementation for stock indicators (技术指标)."""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.stock_indicator import StockIndicator
from app.domain.repositories.stock_indicator_repo import StockIndicatorRepository
from app.infrastructure.db.models import StockIndicatorModel


def _to_entity(model: StockIndicatorModel) -> StockIndicator:
    """ORM Model -> Domain Entity"""
    return StockIndicator(
        id=model.id,
        stock_code=model.stock_code,
        trade_date=model.trade_date,
        period=model.period,
        ma5=model.ma5,
        ma10=model.ma10,
        ma20=model.ma20,
        macd_dif=model.macd_dif,
        macd_dea=model.macd_dea,
        macd_bar=model.macd_bar,
        kdj_k=model.kdj_k,
        kdj_d=model.kdj_d,
        kdj_j=model.kdj_j,
        data_source=model.data_source,
        create_time=model.create_time,
        update_time=model.update_time,
    )


class MySQLStockIndicatorRepository(StockIndicatorRepository):
    """MySQL implementation of StockIndicatorRepository"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_indicators(
        self,
        stock_code: str,
        period: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[StockIndicator]:
        conditions = [
            StockIndicatorModel.stock_code == stock_code,
            StockIndicatorModel.period == period,
        ]
        if start_date:
            conditions.append(StockIndicatorModel.trade_date >= start_date)
        if end_date:
            conditions.append(StockIndicatorModel.trade_date <= end_date)

        stmt = (
            select(StockIndicatorModel)
            .where(and_(*conditions))
            .order_by(StockIndicatorModel.trade_date.asc())
        )
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return [_to_entity(m) for m in models]

    async def upsert_batch(self, indicators: List[StockIndicator]) -> None:
        """批量 upsert 技术指标数据"""
        for indicator in indicators:
            # 查找是否已存在
            stmt = select(StockIndicatorModel).where(
                StockIndicatorModel.stock_code == indicator.stock_code,
                StockIndicatorModel.trade_date == indicator.trade_date,
                StockIndicatorModel.period == indicator.period,
            )
            result = await self.session.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                existing.ma5 = indicator.ma5
                existing.ma10 = indicator.ma10
                existing.ma20 = indicator.ma20
                existing.macd_dif = indicator.macd_dif
                existing.macd_dea = indicator.macd_dea
                existing.macd_bar = indicator.macd_bar
                existing.kdj_k = indicator.kdj_k
                existing.kdj_d = indicator.kdj_d
                existing.kdj_j = indicator.kdj_j
                existing.data_source = indicator.data_source
                existing.update_time = datetime.now()
            else:
                model = StockIndicatorModel(
                    stock_code=indicator.stock_code,
                    trade_date=indicator.trade_date,
                    period=indicator.period,
                    ma5=indicator.ma5,
                    ma10=indicator.ma10,
                    ma20=indicator.ma20,
                    macd_dif=indicator.macd_dif,
                    macd_dea=indicator.macd_dea,
                    macd_bar=indicator.macd_bar,
                    kdj_k=indicator.kdj_k,
                    kdj_d=indicator.kdj_d,
                    kdj_j=indicator.kdj_j,
                    data_source=indicator.data_source,
                )
                self.session.add(model)

        await self.session.flush()
