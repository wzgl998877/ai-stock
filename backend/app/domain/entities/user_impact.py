from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class UserImpact:
    id: Optional[int] = None
    user_id: str = ""
    event_id: int = 0
    matched_stocks: Optional[list] = None
    matched_industries: Optional[list] = None
    priority: str = "P2"
    is_read: bool = False
    is_alert_sent: bool = False
    created_at: Optional[datetime] = None
