from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional


@dataclass
class MorningBriefing:
    id: Optional[int] = None
    user_id: str = ""
    briefing_date: Optional[date] = None
    ai_summary: Optional[str] = None
    content: Optional[dict] = None
    is_read: bool = False
    created_at: Optional[datetime] = None
