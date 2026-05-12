from dataclasses import dataclass
from datetime import datetime, time
from typing import Optional


@dataclass
class RadarConfig:
    id: Optional[int] = None
    user_id: str = ""
    focused_industries: Optional[list] = None
    event_types: Optional[list] = None
    alert_sensitivity: str = "medium"
    quiet_hours_start: Optional[time] = None
    quiet_hours_end: Optional[time] = None
    updated_at: Optional[datetime] = None
