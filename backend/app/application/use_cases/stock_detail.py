"""StockDetailUseCase — 股票详情聚合用例"""

from __future__ import annotations

import logging
from typing import Optional

from app.application.dtos.market_data_dto import StockDetailDTO
from app.domain.repositories.stock_data_repo import StockDataRepository
from app.domain.repositories.article_stock_repo import ArticleStockRepository

logger = logging.getLogger(__name__)


class StockDetailUseCase:
    """股票详情聚合用例：组装 basic + quote + financial + 关联文章"""

    def __init__(
        self,
        stock_data_repo: StockDataRepository,
        article_stock_repo: ArticleStockRepository,
    ):
        self.stock_data_repo = stock_data_repo
        self.article_stock_repo = article_stock_repo

    async def get_detail(self, stock_code: str) -> Optional[StockDetailDTO]:
        """
        获取股票聚合详情。

        聚合数据源：
        1. 基础信息（StockBasicInfo）
        2. 实时行情（MarketQuote）
        3. 财务数据（StockFinancial，取最近一期）
        4. 关联文章列表
        """
        # 1. 基础信息
        basic = await self.stock_data_repo.get_basic(stock_code)
        if basic is None:
            return None

        dto = StockDetailDTO(
            stock_code=basic.code,
            name=basic.name,
            exchange=basic.exchange,
            industry=basic.industry,
            list_date=basic.list_date,
        )

        # 2. 实时行情
        quote = await self.stock_data_repo.get_quote(stock_code)
        if quote:
            dto.price = quote.price
            dto.change_pct = quote.change_pct
            dto.change_amount = quote.change_amount
            dto.open_price = quote.open_price
            dto.high_price = quote.high_price
            dto.low_price = quote.low_price
            dto.pre_close = quote.pre_close
            dto.volume = quote.volume
            dto.amount = quote.amount
            dto.quote_time = quote.quote_time

        # 3. 财务数据（取最近一期）
        financials = await self.stock_data_repo.get_financial(stock_code)
        if financials:
            latest = financials[0]
            dto.report_date = latest.report_date
            dto.roe = latest.roe
            dto.net_profit = latest.net_profit
            dto.revenue = latest.revenue
            dto.eps = latest.eps
            dto.gross_margin = latest.gross_margin
            dto.debt_ratio = latest.debt_ratio

        # 4. 关联文章
        try:
            article_infos = await self.article_stock_repo.get_by_stock(stock_code, limit=10)
            dto.related_articles = [
                {
                    "article_id": info.article_id,
                    "title": info.title or "",
                    "summary": info.summary or "",
                    "saved_at": info.saved_at.isoformat() if info.saved_at else None,
                }
                for info in article_infos
            ]
        except Exception as e:
            logger.warning(f"Failed to load related articles for {stock_code}: {e}")
            dto.related_articles = []

        return dto
