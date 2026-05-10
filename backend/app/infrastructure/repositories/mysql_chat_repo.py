"""MySQL Chat Repository — session + message CRUD"""

import uuid
from typing import Optional, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.entities.chat_session import ChatSession
from app.domain.entities.chat_message import ChatMessage
from app.domain.repositories.chat_repo import ChatRepository
from app.infrastructure.db.models import ChatSession as SessionModel, ChatMessage as MessageModel


def _message_to_entity(model: MessageModel) -> ChatMessage:
    return ChatMessage(
        message_id=model.message_id,
        session_id=model.session_id,
        role=model.role,
        content=model.content,
        thinking_steps=model.thinking_steps,
        event_type=model.event_type,
        agent_data=model.agent_data,
        summary=model.summary,
        industries=model.industries,
        create_time=model.create_time,
        update_time=model.update_time,
        deleted=model.deleted,
    )


def _session_to_entity(model: SessionModel) -> ChatSession:
    return ChatSession(
        session_id=model.session_id,
        user_id=model.user_id,
        title=model.title,
        event_type=model.event_type,
        session_type=model.session_type,
        config=model.config,
        messages=[_message_to_entity(m) for m in model.messages],
        create_time=model.create_time,
        update_time=model.update_time,
        deleted=model.deleted,
    )


class MySQLChatRepository(ChatRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_session(self, chat_session: ChatSession) -> ChatSession:
        model = SessionModel(
            session_id=chat_session.session_id or uuid.uuid4().hex,
            user_id=chat_session.user_id,
            title=chat_session.title,
            event_type=chat_session.event_type,
            session_type=chat_session.session_type or "event_analysis",
            config=chat_session.config,
        )
        self.session.add(model)
        await self.session.flush()
        chat_session.session_id = model.session_id
        chat_session.create_time = model.create_time
        return chat_session

    async def get_session(self, session_id: str) -> Optional[ChatSession]:
        stmt = (
            select(SessionModel)
            .where(SessionModel.session_id == session_id, SessionModel.deleted == "0")
            .options(selectinload(SessionModel.messages))
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return _session_to_entity(model) if model else None

    async def list_sessions_by_user(self, user_id: str) -> List[ChatSession]:
        stmt = (
            select(SessionModel)
            .where(SessionModel.user_id == user_id, SessionModel.deleted == "0")
            .order_by(SessionModel.create_time.desc())
        )
        result = await self.session.execute(stmt)
        return [_session_to_entity(m) for m in result.scalars().all()]

    async def delete_session(self, session_id: str) -> bool:
        stmt = select(SessionModel).where(SessionModel.session_id == session_id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            return False
        model.deleted = "1"
        await self.session.flush()
        return True

    async def update_session_title(self, session_id: str, title: str) -> None:
        stmt = select(SessionModel).where(SessionModel.session_id == session_id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        if model:
            model.title = title
            await self.session.flush()

    async def add_message(self, message: ChatMessage) -> ChatMessage:
        model = MessageModel(
            message_id=message.message_id or uuid.uuid4().hex,
            session_id=message.session_id,
            role=message.role,
            content=message.content,
            thinking_steps=message.thinking_steps,
            event_type=message.event_type,
            agent_data=message.agent_data,
            summary=message.summary,
            industries=message.industries,
        )
        self.session.add(model)
        await self.session.flush()
        message.message_id = model.message_id
        message.create_time = model.create_time
        return message

    async def list_messages(self, session_id: str) -> List[ChatMessage]:
        stmt = (
            select(MessageModel)
            .where(MessageModel.session_id == session_id, MessageModel.deleted == "0")
            .order_by(MessageModel.create_time.asc())
        )
        result = await self.session.execute(stmt)
        return [_message_to_entity(m) for m in result.scalars().all()]
