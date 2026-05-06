"""IndustryUseCase — 行业数据用例"""

from __future__ import annotations

import logging
from typing import List, Optional

from app.application.dtos.market_data_dto import IndustryOverviewDTO, SearchResultItem
from app.domain.entities.industry import Industry
from app.domain.repositories.industry_repo import IndustryRepository

logger = logging.getLogger(__name__)


class IndustryUseCase:
    """行业数据用例：获取行业列表和行业内股票对比"""

    def __init__(self, industry_repo: IndustryRepository):
        self.industry_repo = industry_repo

    async def list_level1_industries(self) -> List[Industry]:
        """获取所有一级行业列表"""
        return await self.industry_repo.list_all_level1()

    async def get_industry_overview(self, industry_code: str) -> Optional[IndustryOverviewDTO]:
        """
        获取行业概览，包含行业内股票列表。

        返回行业基本信息及关联股票。
        """
        industry = await self.industry_repo.get_by_code(industry_code)
        if industry is None:
            return None

        # 获取行业内股票
        stocks_data = await self.industry_repo.get_stocks_by_industry(industry_code)

        top_stocks = [
            SearchResultItem(
                stock_code=s["stock_code"],
                name=s["stock_name"],
                industry=industry.name,
            )
            for s in stocks_data
        ]

        return IndustryOverviewDTO(
            industry_code=industry.industry_code,
            industry_name=industry.name,
            stock_count=len(stocks_data),
            top_stocks=top_stocks,
        )

    async def get_sub_industries(self, parent_code: str) -> List[Industry]:
        """获取子行业列表"""
        return await self.industry_repo.list_by_parent(parent_code)
