"""事件雷达 DTO — Pydantic 请求/响应模型"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# --- 请求 ---

class ImpactQueryParams(BaseModel):
    status: Optional[str] = Field(default="all", pattern="^(active|archived|all)$")
    date: Optional[str] = Field(default=None, description="YYYY-MM-DD")


class RadarConfigUpdate(BaseModel):
    focused_industries: Optional[list[str]] = None
    event_types: Optional[list[str]] = None
    alert_sensitivity: Optional[str] = Field(default="medium", pattern="^(high|medium|low)$")
    quiet_hours_start: Optional[str] = None
    quiet_hours_end: Optional[str] = None


# --- 响应 ---

class MatchedStockDTO(BaseModel):
    code: str
    name: str = ""
    direction: str = "neutral"
    confidence: float = 0.0
    reason: str = ""


class MatchedIndustryDTO(BaseModel):
    name: str
    direction: str = "neutral"


class ImpactEventDTO(BaseModel):
    id: int
    event_id: int
    title: str
    summary: Optional[str] = None
    event_type: Optional[str] = None
    sentiment: Optional[str] = None
    importance: Optional[str] = None
    source_count: int = 1
    matched_stocks: list[MatchedStockDTO] = []
    matched_industries: list[MatchedIndustryDTO] = []
    priority: str = "P2"
    is_read: bool = False
    has_ai_insight: bool = False
    has_related_analysis: bool = False
    first_seen_at: Optional[datetime] = None
    source_name: str = ""
    source_url: str = ""


class StatsDTO(BaseModel):
    today_total: int = 0
    today_positive: int = 0
    today_negative: int = 0
    today_neutral: int = 0
    affected_stocks_count: int = 0
    week_total: int = 0


class ImpactListResponse(BaseModel):
    active_impacts: list[ImpactEventDTO] = []
    archived_impacts: list[ImpactEventDTO] = []
    stats: StatsDTO = StatsDTO()
    last_scan_at: Optional[datetime] = None


class ArticleDTO(BaseModel):
    article_id: int
    title: str
    content: Optional[str] = None
    source: str = ""
    url: str = ""
    published_at: Optional[datetime] = None


class AiInsightDTO(BaseModel):
    event_nature: str = ""
    affected_industries_detail: list[dict] = []
    stock_impact_reasons: list[dict] = []


class ImpactDetailDTO(BaseModel):
    id: int
    event_id: int
    title: str
    summary: Optional[str] = None
    event_type: Optional[str] = None
    sentiment: Optional[str] = None
    importance: Optional[str] = None
    source_count: int = 1
    matched_stocks: list[MatchedStockDTO] = []
    matched_industries: list[MatchedIndustryDTO] = []
    priority: str = "P2"
    is_read: bool = False
    first_seen_at: Optional[datetime] = None
    articles: list[ArticleDTO] = []
    ai_insight: Optional[AiInsightDTO] = None
    related_analyses: list[dict] = []


class AlertDTO(BaseModel):
    id: int
    priority: str
    title: str
    summary: Optional[str] = None
    user_impact_id: int = 0
    is_read: bool = False
    created_at: Optional[datetime] = None


class AlertListResponse(BaseModel):
    alerts: list[AlertDTO] = []


class UnreadCountResponse(BaseModel):
    count: int = 0


class BriefingContentDTO(BaseModel):
    impact_events: list[dict] = []
    portfolio_overview: list[dict] = []
    today_focus: list[dict] = []


class BriefingDTO(BaseModel):
    id: int
    briefing_date: str = ""
    ai_summary: Optional[str] = None
    content: Optional[BriefingContentDTO] = None
    is_read: bool = False
    created_at: Optional[datetime] = None


class BriefingHistoryDTO(BaseModel):
    id: int
    briefing_date: str = ""
    ai_summary: Optional[str] = None
    is_read: bool = False


class BriefingHistoryResponse(BaseModel):
    briefings: list[BriefingHistoryDTO] = []


class RadarConfigDTO(BaseModel):
    focused_industries: list[str] = []
    event_types: list[str] = []
    alert_sensitivity: str = "medium"
    quiet_hours_start: Optional[str] = None
    quiet_hours_end: Optional[str] = None


class StockImpactDTO(BaseModel):
    code: str
    name: str = ""
    impact_count_24h: int = 0
    direction: str = "neutral"
    recent_impacts: list[dict] = []


class StockImpactResponse(BaseModel):
    stocks: list[StockImpactDTO] = []
