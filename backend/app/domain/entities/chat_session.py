from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List


@dataclass
class ChatSession:
    session_id: str
    user_id: str
    title: Optional[str] = None
    messages: List = field(default_factory=list)  # ChatMessage list
    create_time: Optional[datetime] = None
    update_time: Optional[datetime] = None
    deleted: str = "0"
