"""Chat 相关 DTO"""

from pydantic import BaseModel, Field
from typing import Optional, List


class CreateSessionRequest(BaseModel):
    title: Optional[str] = None


class SessionResponse(BaseModel):
    id: str
    title: str
    event_type: Optional[str] = None
    created_at: str
    updated_at: str


class SessionListResponse(BaseModel):
    sessions: List[SessionResponse]
    total: int


class SendMessageRequest(BaseModel):
    content: str = Field(..., min_length=2, max_length=5000)
    event_type: Optional[str] = None  # 四个按钮选择的值


class MessageResponse(BaseModel):
    id: str
    role: str  # user / assistant
    content: str
    thinking_steps: Optional[List[dict]] = None
    event_type: Optional[str] = None
    created_at: str


class SessionDetailResponse(BaseModel):
    id: str
    title: str
    event_type: Optional[str] = None
    messages: List[MessageResponse]
    created_at: str
    updated_at: str
