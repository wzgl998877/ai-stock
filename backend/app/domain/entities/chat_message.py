from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Any


@dataclass
class ChatMessage:
    message_id: str
    session_id: str
    role: str  # user/assistant
    content: str
    thinking_steps: Optional[List[dict]] = None  # 思维链步骤数组
    event_type: Optional[str] = None  # 本条分析的事件类型
    agent_data: Optional[dict] = None  # 多Agent中间数据(Agent状态/进度等)
    summary: Optional[str] = None  # AI生成的文章摘要
    industries: Optional[List[str]] = None  # AI生成的行业标签列表
    create_time: Optional[datetime] = None
    update_time: Optional[datetime] = None
    deleted: str = "0"
