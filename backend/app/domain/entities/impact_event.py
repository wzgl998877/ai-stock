from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class ImpactEvent:
    event_id: Optional[int] = None
    title: str = ""
    summary: Optional[str] = None
    event_type: Optional[str] = None
    sentiment: Optional[str] = None
    importance: Optional[str] = None
    affected_industries: Optional[list] = None
    affected_stocks: Optional[list] = None
    source_count: int = 1
    first_seen_at: Optional[datetime] = None
    last_seen_at: Optional[datetime] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
