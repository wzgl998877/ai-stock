from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class UserAlert:
    id: Optional[int] = None
    user_id: str = ""
    user_impact_id: int = 0
    priority: str = "P1"
    title: str = ""
    summary: Optional[str] = None
    is_read: bool = False
    created_at: Optional[datetime] = None
