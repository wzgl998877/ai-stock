"""技术指标Repository接口"""

from abc import ABC, abstractmethod
from typing import List, Optional

from app.domain.entities.stock_indicator import StockIndicator


class StockIndicatorRepository(ABC):
    """技术指标数据访问接口"""

    @abstractmethod
    async def get_indicators(
        self,
        stock_code: str,
        period: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[StockIndicator]:
        """获取技术指标数据"""
        ...

    @abstractmethod
    async def upsert_batch(self, indicators: List[StockIndicator]) -> None:
        """批量插入/更新技术指标"""
        ...
