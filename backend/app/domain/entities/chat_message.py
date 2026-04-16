from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class ChatMessage:
    message_id: str
    session_id: str
    role: str  # user/assistant/system
    content: str
    create_time: Optional[datetime] = None
    update_time: Optional[datetime] = None
    deleted: str = "0"
