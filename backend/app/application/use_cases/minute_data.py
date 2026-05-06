"""分时数据查询用例。

调用 MinuteClient 获取原始数据，转换为 MinuteQuote 领域实体。
"""

from decimal import Decimal
from typing import List

from app.domain.entities.minute_quote import MinuteQuote
from app.infrastructure.market.minute_client import MinuteClient


class MinuteDataUseCase:
    """分时数据查询用例。"""

    def __init__(self) -> None:
        self._client = MinuteClient()

    async def get_minute_data(self, code: str) -> List[MinuteQuote]:
        """获取指定股票的分时数据。"""
        raw_items = await self._client.get_minute_data(code)

        quotes: List[MinuteQuote] = []
        for item in raw_items:
            quote = MinuteQuote(
                stock_code=code,
                time=item["time"],
                price=Decimal(str(item["price"])),
                volume=Decimal(str(item["volume"])),
                avg_price=Decimal(str(item["avg_price"])) if item.get("avg_price") else None,
            )
            quotes.append(quote)

        return quotes
