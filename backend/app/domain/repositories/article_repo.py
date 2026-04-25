from abc import ABC, abstractmethod
from typing import Optional, List, Tuple
from app.domain.entities.article import Article


class ArticleRepository(ABC):
    @abstractmethod
    async def save(self, article: Article) -> Article:
        """保存文章，同步写入 t_article_industry + t_article_stock"""
        ...

    @abstractmethod
    async def get_by_id(self, article_id: str) -> Optional[Article]:
        ...

    @abstractmethod
    async def list_articles(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
        event_type: Optional[str] = None,
    ) -> Tuple[List[Article], int]:
        """返回 (文章列表, 总数)"""
        ...

    @abstractmethod
    async def list_by_industry(
        self,
        industry_code: str,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Article], int]:
        ...

    @abstractmethod
    async def list_by_stock(
        self,
        stock_code: str,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Article], int]:
        ...

    @abstractmethod
    async def delete(self, article_id: str) -> bool:
        """软删除"""
        ...

    @abstractmethod
    async def count_by_user(self, user_id: str) -> int:
        ...

    @abstractmethod
    async def update_analysis_data(self, article_id: str, analysis_data: dict, status: str) -> None:
        """更新分析记录的 analysis_data JSON 和 status"""
        ...

    @abstractmethod
    async def list_analysis_records(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
        article_type: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Tuple[List[Article], int]:
        """查询分析记录列表（支持 article_type 和 status 过滤）"""
        ...
