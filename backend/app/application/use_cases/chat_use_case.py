"""ChatUseCase — 对话式分析用例，支持多轮对话和思维链"""

import logging
import uuid
from typing import AsyncGenerator

from app.domain.entities.chat_session import ChatSession
from app.domain.entities.chat_message import ChatMessage
from app.domain.repositories.chat_repo import ChatRepository
from app.domain.services.analysis_parser import AnalysisParser
from app.domain.value_objects.event_type import EventType
from app.infrastructure.ai.ai_service import AIService
from app.infrastructure.ai.prompts import geopolicy, policy, earnings, chain, general

logger = logging.getLogger(__name__)

PROMPT_BUILDERS = {
    EventType.GEO_POLITICAL: geopolicy.build_prompt,
    EventType.POLICY: policy.build_prompt,
    EventType.EARNINGS: earnings.build_prompt,
    EventType.SUPPLY_CHAIN: chain.build_prompt,
    EventType.OTHER: general.build_prompt,
}

MAX_HISTORY_ROUNDS = 10  # 最多保留最近 10 轮对话


class ChatUseCase:

    def __init__(self, chat_repo: ChatRepository, ai_service: AIService):
        self.chat_repo = chat_repo
        self.ai_service = ai_service
        self.parser = AnalysisParser()

    async def create_session(self, user_id: str, title: str | None = None, event_type: str | None = None) -> ChatSession:
        session = ChatSession(
            session_id=uuid.uuid4().hex,
            user_id=user_id,
            title=title,
            event_type=event_type,
        )
        return await self.chat_repo.create_session(session)

    async def list_sessions(self, user_id: str) -> list[ChatSession]:
        return await self.chat_repo.list_sessions_by_user(user_id)

    async def get_session(self, session_id: str) -> ChatSession | None:
        return await self.chat_repo.get_session(session_id)

    async def delete_session(self, session_id: str) -> bool:
        return await self.chat_repo.delete_session(session_id)

    async def stream_chat(
        self, session_id: str, content: str, event_type: str | None = None
    ) -> AsyncGenerator[dict, None]:
        """
        在指定会话中发送消息，SSE 流式返回。
        """
        session = await self.chat_repo.get_session(session_id)
        if not session:
            yield {"type": "error", "data": "会话不存在"}
            return

        # 1. 保存用户消息
        user_msg = ChatMessage(
            message_id=uuid.uuid4().hex,
            session_id=session_id,
            role="user",
            content=content,
            event_type=event_type,
        )
        await self.chat_repo.add_message(user_msg)

        # 2. 构建 messages 数组（多轮对话）
        history = await self.chat_repo.list_messages(session_id)
        messages = self._build_messages(history, event_type)

        # 3. 流式调用 LLM
        full_content = ""
        thinking_steps = []

        try:
            async for chunk in self.ai_service.stream_chat("", "", history_messages=messages):
                full_content += chunk
                yield {"type": "content", "data": chunk}
        except Exception as e:
            logger.error("ChatUseCase AI 调用失败: %s", e, exc_info=True)
            yield {"type": "error", "data": f"AI 分析失败: {str(e)}"}
            return

        # 4. 解析结果
        effective_event_type = event_type or session.event_type or "other"
        parse_result = self.parser.parse(full_content, effective_event_type)

        # 5. 保存 AI 消息
        ai_msg = ChatMessage(
            message_id=uuid.uuid4().hex,
            session_id=session_id,
            role="assistant",
            content=full_content,
            thinking_steps=thinking_steps or None,
            event_type=effective_event_type,
        )
        await self.chat_repo.add_message(ai_msg)

        # 6. 推送结构化数据
        if parse_result.title:
            yield {"type": "title", "data": parse_result.title}
        else:
            yield {"type": "title", "data": content[:15] + ("..." if len(content) > 15 else "")}

        if parse_result.summary:
            yield {"type": "summary", "data": parse_result.summary}

        if parse_result.industry_names:
            yield {"type": "industries", "data": parse_result.industry_names}

        yield {"type": "done", "data": ""}

    def _build_messages(self, history: list[ChatMessage], event_type: str | None) -> list[dict]:
        """将历史消息拼接为 OpenAI messages 数组，截断超过 MAX_HISTORY_ROUNDS 的早期对话"""
        # 选择 prompt
        effective_type = event_type or "other"
        builder = PROMPT_BUILDERS.get(EventType(effective_type), general.build_prompt)

        # 构建消息列表
        messages: list[dict] = []

        # 截断历史（保留最近 N 轮，1 轮 = 1 user + 1 assistant）
        recent = history[-(MAX_HISTORY_ROUNDS * 2):]

        for msg in recent:
            if msg.role == "user":
                messages.append({"role": "user", "content": msg.content})
            elif msg.role == "assistant":
                messages.append({"role": "assistant", "content": msg.content})

        # 如果有 system prompt，插入到最前面
        if messages:
            last_user = messages[-1].get("content", "")
            system_prompt = builder(last_user)
            messages.insert(0, {"role": "system", "content": system_prompt})

        return messages
