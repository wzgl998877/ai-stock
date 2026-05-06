"""文章-股票关联Repository接口"""

from abc import ABC, abstractmethod
from typing import List
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class ArticleStockInfo:
    """文章-股票关联信息"""
    article_id: str
    stock_code: str
    stock_name: str
    # 运行时填充
    title: Optional[str] = None
    summary: Optional[str] = None
    saved_at: Optional[datetime] = None


class ArticleStockRepository(ABC):
    """文章-股票关联数据访问接口"""

    @abstractmethod
    async def get_by_stock(self, stock_code: str, limit: int = 50) -> List[ArticleStockInfo]:
        """根据股票代码查询关联文章"""
        ...

    @abstractmethod
    async def get_by_article(self, article_id: str) -> List[ArticleStockInfo]:
        """根据文章ID查询关联股票"""
        ...
