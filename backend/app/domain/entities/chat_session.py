from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List


@dataclass
class ChatSession:
    session_id: str
    user_id: str
    title: Optional[str] = None
    event_type: Optional[str] = None  # 当前分析事件类型（可选）
    messages: List = field(default_factory=list)  # ChatMessage list
    create_time: Optional[datetime] = None
    update_time: Optional[datetime] = None
    deleted: str = "0"
