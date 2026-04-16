from abc import ABC, abstractmethod
from typing import List, Tuple
from app.domain.entities.article import Article


class SearchRepository(ABC):
    @abstractmethod
    async def search(
        self,
        query: str,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Article], int]:
        """FULLTEXT 搜索，返回 (结果列表, 总数)"""
        ...

    @abstractmethod
    async def search_by_industry(
        self,
        query: str,
        industry_code: str,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Article], int]:
        ...

    @abstractmethod
    async def search_by_stock(
        self,
        query: str,
        stock_code: str,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Article], int]:
        ...
