from abc import ABC, abstractmethod
from typing import Optional, List
from app.domain.entities.stock import Stock


class StockRepository(ABC):
    @abstractmethod
    async def get_by_code(self, stock_code: str) -> Optional[Stock]: ...

    @abstractmethod
    async def find_by_name(self, name: str) -> Optional[Stock]: ...

    @abstractmethod
    async def list_by_codes(self, codes: List[str]) -> List[Stock]: ...
