from abc import ABC, abstractmethod
from typing import Optional, List
from app.domain.entities.chat_session import ChatSession
from app.domain.entities.chat_message import ChatMessage


class ChatRepository(ABC):
    # Session
    @abstractmethod
    async def create_session(self, session: ChatSession) -> ChatSession: ...

    @abstractmethod
    async def get_session(self, session_id: str) -> Optional[ChatSession]: ...

    @abstractmethod
    async def list_sessions_by_user(self, user_id: str) -> List[ChatSession]: ...

    @abstractmethod
    async def delete_session(self, session_id: str) -> bool: ...

    # Message
    @abstractmethod
    async def add_message(self, message: ChatMessage) -> ChatMessage: ...

    @abstractmethod
    async def list_messages(self, session_id: str) -> List[ChatMessage]: ...
