"""Chat 相关 DTO"""

from pydantic import BaseModel, Field
from typing import Optional, List


class CreateSessionRequest(BaseModel):
    title: Optional[str] = None
    event_type: Optional[str] = None
    config: Optional[dict] = None  # 个股分析配置参数


class SessionResponse(BaseModel):
    id: str
    title: str
    event_type: Optional[str] = None
    session_type: Optional[str] = None
    created_at: str
    updated_at: str


class SessionListResponse(BaseModel):
    sessions: List[SessionResponse]
    total: int


class SendMessageRequest(BaseModel):
    content: str = Field(..., min_length=2, max_length=5000)
    event_type: Optional[str] = None  # 事件类型或 stock_analysis
    config: Optional[dict] = None  # 个股分析配置参数


class MessageResponse(BaseModel):
    id: str
    role: str  # user / assistant
    content: str
    thinking_steps: Optional[List[dict]] = None
    event_type: Optional[str] = None
    summary: Optional[str] = None  # AI生成的文章摘要
    industries: Optional[List[str]] = None  # AI生成的行业标签
    created_at: str


class SessionDetailResponse(BaseModel):
    id: str
    title: str
    event_type: Optional[str] = None
    session_type: Optional[str] = None
    messages: List[MessageResponse]
    created_at: str
    updated_at: str
