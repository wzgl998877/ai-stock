from abc import ABC, abstractmethod
from typing import List, Optional
from app.domain.entities.industry import Industry


class IndustryRepository(ABC):
    @abstractmethod
    async def get_by_code(self, industry_code: str) -> Optional[Industry]: ...

    @abstractmethod
    async def list_by_level(self, level: int) -> List[Industry]: ...

    @abstractmethod
    async def list_by_parent(self, parent_code: str) -> List[Industry]: ...

    @abstractmethod
    async def list_all_level1(self) -> List[Industry]:
        """获取全部一级行业"""
        ...

    @abstractmethod
    async def find_by_name(self, name: str) -> Optional[Industry]:
        """按名称精确匹配"""
        ...

    @abstractmethod
    async def get_stocks_by_industry(self, industry_code: str) -> List[dict]:
        """获取行业内的所有股票（返回包含 stock_code, stock_name, industry_code 的字典列表）"""
        ...
