"""IndicatorCalcUseCase — 技术指标计算用例"""

from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal
from typing import List, Optional

from app.domain.entities.stock_indicator import StockIndicator
from app.domain.repositories.stock_data_repo import StockDataRepository
from app.domain.repositories.stock_indicator_repo import StockIndicatorRepository
from app.domain.services.indicator_service import IndicatorService

logger = logging.getLogger(__name__)


class IndicatorCalcUseCase:
    """技术指标计算用例：调用 IndicatorService 计算，处理缓存"""

    def __init__(
        self,
        stock_data_repo: StockDataRepository,
        indicator_repo: StockIndicatorRepository,
        indicator_service: Optional[IndicatorService] = None,
    ):
        self.stock_data_repo = stock_data_repo
        self.indicator_repo = indicator_repo
        self.indicator_service = indicator_service or IndicatorService()

    async def get_indicators(
        self,
        stock_code: str,
        period: str = "daily",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        force_recalc: bool = False,
    ) -> List[StockIndicator]:
        """
        获取技术指标。

        策略：
        1. 如果 force_recalc=False，先查缓存
        2. 缓存有数据则直接返回
        3. 否则从 K 线数据重新计算并写入缓存
        """
        if not force_recalc:
            cached = await self.indicator_repo.get_indicators(
                stock_code=stock_code,
                period=period,
                start_date=start_date,
                end_date=end_date,
            )
            if cached:
                return cached

        # 从 K 线数据计算
        daily_quotes = await self.stock_data_repo.get_daily(
            code=stock_code,
            start_date=start_date,
            end_date=end_date,
            period=period,
        )

        if not daily_quotes:
            return []

        # 提取价格序列
        close_prices: List[Decimal] = []
        high_prices: List[Decimal] = []
        low_prices: List[Decimal] = []
        trade_dates: List[date] = []

        for q in daily_quotes:
            if q.close_price is not None:
                close_prices.append(q.close_price)
                high_prices.append(q.high_price or q.close_price)
                low_prices.append(q.low_price or q.close_price)
                trade_dates.append(q.trade_date)

        if not close_prices:
            return []

        # 计算指标
        indicators = self.indicator_service.compute_all(
            close_prices=close_prices,
            high_prices=high_prices,
            low_prices=low_prices,
            trade_dates=trade_dates,
            stock_code=stock_code,
            period=period,
        )

        # 写入缓存
        try:
            await self.indicator_repo.upsert_batch(indicators)
        except Exception as e:
            logger.warning(f"Failed to cache indicators for {stock_code}: {e}")

        return indicators
