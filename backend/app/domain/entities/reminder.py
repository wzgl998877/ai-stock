from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional, List


@dataclass
class Reminder:
    reminder_id: str
    title: str
    event_date: date
    user_id: str
    status: str = "pending"  # pending/reminded_3day/reminded_today/archived
    industry_tags: Optional[List[str]] = None
    create_time: Optional[datetime] = None
    update_time: Optional[datetime] = None
    deleted: str = "0"
