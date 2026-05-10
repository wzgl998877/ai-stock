"""分析相关 DTO"""

from pydantic import BaseModel, Field
from typing import Optional, List


class AnalysisRequestDTO(BaseModel):
    event_type: str = Field(..., description="事件类型", examples=["geopolitical"])
    question: str = Field(..., min_length=10, max_length=500, description="事件描述")


class SaveArticleDTO(BaseModel):
    title: str = Field(..., max_length=50, description="文章标题")
    summary: str = Field(..., max_length=200, description="文章摘要")
    content: str = Field(..., description="完整 Markdown 正文")
    event_type: str = Field(..., description="事件类型")
    raw_input: str = Field(..., max_length=500, description="用户原始输入")
    industry_codes: List[str] = Field(..., description="行业代码列表", examples=[["410000", "240000"]])
    stock_refs: List["StockRefDTO"] = Field(default_factory=list, description="股票引用列表")
    chain_table: Optional[List[dict]] = Field(None, description="产业链传导表")


class StockRefDTO(BaseModel):
    code: str = Field(..., description="股票代码")
    name: str = Field(..., description="股票名称")


class SimilarityRequestDTO(BaseModel):
    question: str = Field(..., min_length=2, description="用户输入")
    top_k: int = Field(3, ge=1, le=10, description="返回最多条数")


class SaveArticleResponseDTO(BaseModel):
    id: str
    title: str
    industry_count: int
    created_at: str


class SimilarArticleDTO(BaseModel):
    id: str
    title: str
    summary: str
    industry_tags: List[str]
    created_at: str
    similarity: float


class ExtractIndustriesRequestDTO(BaseModel):
    content: str = Field(..., description="分析内容（LLM 输出的完整文本）")
    event_type: str = Field(..., description="事件类型，用于选择对应 prompt")


class ExtractIndustriesResponseDTO(BaseModel):
    industries: List[str] = Field(..., description="提取出的申万一级行业名称列表")
