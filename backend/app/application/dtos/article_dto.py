"""文章相关 DTO"""

from pydantic import BaseModel, Field
from typing import Optional, List


class IndustryRefDTO(BaseModel):
    code: str
    name: str
    chain_level: Optional[int] = None


class StockRefDTO(BaseModel):
    code: str
    name: str


class ArticleListItemDTO(BaseModel):
    id: str
    title: str
    summary: str
    industries: List[IndustryRefDTO]
    stocks: List[StockRefDTO]
    event_type: str
    created_at: str
    highlight: Optional[str] = None


class ArticleDetailDTO(BaseModel):
    id: str
    title: str
    summary: str
    content: str
    event_type: str
    raw_input: str
    industries: List[IndustryRefDTO]
    stocks: List[StockRefDTO]
    chain_table: Optional[List[dict]] = None
    created_at: str
    updated_at: str


class ArticleListResponseDTO(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[ArticleListItemDTO]
