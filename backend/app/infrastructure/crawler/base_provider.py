"""信息源抽象基类"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class CrawledArticle:
    title: str
    url: str
    content: str = ""
    source: str = ""
    published_at: Optional[datetime] = None


class BaseEventProvider(ABC):
    @abstractmethod
    async def fetch_latest(self, limit: int = 50) -> list[CrawledArticle]:
        """获取最新财经快讯"""
        ...

    @abstractmethod
    async def fetch_by_stock(self, stock_code: str, limit: int = 20) -> list[CrawledArticle]:
        """按股票代码搜索相关新闻"""
        ...

    @abstractmethod
    async def fetch_by_keyword(self, keyword: str, limit: int = 20) -> list[CrawledArticle]:
        """按关键词搜索新闻"""
        ...
