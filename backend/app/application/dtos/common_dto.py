"""通用 DTO — 行业、股票"""

from pydantic import BaseModel
from typing import Optional


class IndustryDTO(BaseModel):
    code: str
    name: str
    article_count: Optional[int] = None


class StockDTO(BaseModel):
    code: str
    name: str
    article_count: Optional[int] = None
