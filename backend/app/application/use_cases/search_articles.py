"""搜索用例 — FULLTEXT 全文搜索"""

import logging
from typing import List, Optional, Tuple

from app.domain.entities.article import Article
from app.domain.repositories.search_repo import SearchRepository

logger = logging.getLogger(__name__)


class SearchArticlesUseCase:
    """全文搜索知识库文章"""

    def __init__(self, search_repo: SearchRepository):
        self.search_repo = search_repo

    async def execute(
        self,
        query: str,
        user_id: str,
        industry_code: Optional[str] = None,
        stock_code: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Article], int]:
        if industry_code:
            return await self.search_repo.search_by_industry(
                query, industry_code, user_id, page, page_size,
            )
        elif stock_code:
            return await self.search_repo.search_by_stock(
                query, stock_code, user_id, page, page_size,
            )
        else:
            return await self.search_repo.search(
                query, user_id, page, page_size,
            )
