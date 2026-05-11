"""文章相关 DTO"""

from pydantic import BaseModel, Field
from typing import Optional, List


class IndustryRefDTO(BaseModel):
    code: str
    name: str
    chain_level: Optional[int] = None
    sentiment: Optional[str] = None


class StockRefDTO(BaseModel):
    code: str
    name: str
    sentiment: Optional[str] = None


class ArticleListItemDTO(BaseModel):
    id: str
    title: str
    summary: str
    industries: List[IndustryRefDTO]
    stocks: List[StockRefDTO]
    event_type: str
    created_at: str
    highlight: Optional[str] = None
    analysis_data: Optional[dict] = None  # 个股分析结构化数据
    status: Optional[str] = None  # in_progress / completed / stopped
    analysis_mode: Optional[str] = None  # quick / full (从 analysis_data.mode 读取)


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
    analysis_data: Optional[dict] = None
    status: Optional[str] = None
    analysis_mode: Optional[str] = None


class ArticleListResponseDTO(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[ArticleListItemDTO]
