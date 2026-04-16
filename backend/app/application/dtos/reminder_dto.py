"""提醒相关 DTO"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date


class ReminderCreateDTO(BaseModel):
    title: str = Field(..., max_length=100, description="事件名称")
    event_date: date = Field(..., description="事件日期")
    industry_tags: Optional[List[str]] = Field(None, description="关联行业")


class ReminderUpdateDTO(BaseModel):
    title: Optional[str] = Field(None, max_length=100)
    event_date: Optional[date] = None
    industry_tags: Optional[List[str]] = None


class ReminderDTO(BaseModel):
    id: str
    title: str
    event_date: str
    industry_tags: Optional[List[str]]
    status: str
    created_at: str


class ReminderListResponseDTO(BaseModel):
    pending: List[ReminderDTO]
    archived: List[ReminderDTO]


class UnreadCountDTO(BaseModel):
    count: int


class TriggerAnalysisDTO(BaseModel):
    event_type: str
    question: str
    industry_tags: Optional[List[str]]
