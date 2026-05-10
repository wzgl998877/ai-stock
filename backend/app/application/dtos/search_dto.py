"""搜索相关 DTO"""

from pydantic import BaseModel, Field
from typing import Optional, List


class SearchRequestDTO(BaseModel):
    query: str = Field(..., min_length=1, description="搜索关键词")
    max_results: int = Field(5, ge=1, le=20, description="最大结果数")
    days: int = Field(7, ge=1, le=30, description="搜索时间范围（天）")


class StockNewsSearchRequestDTO(BaseModel):
    stock_code: str = Field(..., min_length=1, description="股票代码，如 000001")
    stock_name: str = Field("", description="股票名称，如 平安银行")
    max_results: int = Field(5, ge=1, le=20, description="最大结果数")
    focus_keywords: Optional[List[str]] = Field(None, description="关注关键词列表")


class ComprehensiveIntelRequestDTO(BaseModel):
    stock_code: str = Field(..., min_length=1, description="股票代码")
    stock_name: str = Field("", description="股票名称")
    max_searches: int = Field(3, ge=1, le=6, description="最大搜索维度数")
