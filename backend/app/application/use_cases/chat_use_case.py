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

    def __init__(self, chat_repo: ChatRepository, ai_service: AIService, analysis_graph=None):
        self.chat_repo = chat_repo
        self.ai_service = ai_service
        self.analysis_graph = analysis_graph
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
        流程：保存用户消息 → LangGraph 预处理(thinking 实时推送) → 多轮对话 → LLM 流式推理 → 解析 → 持久化
        """
        session = await self.chat_repo.get_session(session_id)
        if not session:
            yield {"type": "error", "data": "会话不存在"}
            return

        effective_event_type = event_type or session.event_type or "other"

        # 1. 保存用户消息
        user_msg = ChatMessage(
            message_id=uuid.uuid4().hex,
            session_id=session_id,
            role="user",
            content=content,
            event_type=event_type,
        )
        await self.chat_repo.add_message(user_msg)

        # 2. LangGraph 预处理 — 内联以便实时 yield thinking 事件
        raw_text = content
        search_results: list[dict] = []
        thinking_steps: list[dict] = []

        if self.analysis_graph:
            from app.infrastructure.workflow.graph.analysis_graph import THINKING_STEP_META, NODE_ORDER

            try:
                # 确定图中实际节点
                try:
                    all_nodes = list(self.analysis_graph.get_graph().nodes.keys())
                    graph_nodes = [n for n in NODE_ORDER if n in all_nodes]
                except Exception:
                    graph_nodes = NODE_ORDER[:2]  # classify + load

                # 发出第一个节点的 running 事件
                if graph_nodes:
                    first_meta = THINKING_STEP_META.get(graph_nodes[0], {})
                    running_evt = {
                        "step": graph_nodes[0],
                        "status": "running",
                        "message": first_meta.get("running", f"正在{graph_nodes[0]}..."),
                    }
                    thinking_steps.append(running_evt)
                    yield {"type": "thinking", "data": running_evt}

                # 使用 astream 获取节点级更新，实时 yield thinking
                accumulated: dict = {}
                async for update in self.analysis_graph.astream(
                    {"source": content, "event_type": effective_event_type},
                    stream_mode="updates",
                ):
                    for node_name, state_update in update.items():
                        accumulated.update(state_update)

                        # done 事件：优先使用节点返回的 thinking_done_msg
                        done_msg = state_update.get("thinking_done_msg")
                        if not done_msg:
                            meta = THINKING_STEP_META.get(node_name, {})
                            done_msg = meta.get("done", f"{node_name}完成")

                        done_evt = {"step": node_name, "status": "done", "message": done_msg}
                        thinking_steps.append(done_evt)
                        yield {"type": "thinking", "data": done_evt}

                        # 下一个节点的 running 事件
                        if node_name in graph_nodes:
                            idx = graph_nodes.index(node_name)
                            if idx + 1 < len(graph_nodes):
                                next_node = graph_nodes[idx + 1]
                                next_meta = THINKING_STEP_META.get(next_node, {})
                                running_evt = {
                                    "step": next_node,
                                    "status": "running",
                                    "message": next_meta.get("running", f"正在{next_node}..."),
                                }
                                thinking_steps.append(running_evt)
                                yield {"type": "thinking", "data": running_evt}

                raw_text = accumulated.get("raw_text", content)
                search_results = accumulated.get("search_results", [])

            except Exception as e:
                logger.warning("LangGraph 预处理失败，降级使用原始输入: %s", e)
                raw_text = content

        # 3. 构建 messages 数组（多轮对话 + 增强上下文）
        history = await self.chat_repo.list_messages(session_id)
        messages = self._build_messages(history, effective_event_type, raw_text, search_results)

        # 4. thinking: 正在分析...
        reasoning_event = {"step": "reasoning", "status": "running", "message": "正在分析..."}
        thinking_steps.append(reasoning_event)
        yield {"type": "thinking", "data": reasoning_event}

        # 5. 流式调用 LLM
        full_content = ""

        try:
            async for chunk in self.ai_service.stream_chat("", "", history_messages=messages):
                full_content += chunk
                yield {"type": "content", "data": chunk}
        except Exception as e:
            logger.error("ChatUseCase AI 调用失败: %s", e, exc_info=True)
            yield {"type": "error", "data": f"AI 分析失败: {str(e)}"}
            return

        # thinking: 分析完成
        reasoning_done = {"step": "reasoning", "status": "done", "message": "分析完成"}
        thinking_steps.append(reasoning_done)
        yield {"type": "thinking", "data": reasoning_done}

        # 6. 解析结果
        parse_result = self.parser.parse(full_content, effective_event_type)

        # 7. 保存 AI 消息
        ai_msg = ChatMessage(
            message_id=uuid.uuid4().hex,
            session_id=session_id,
            role="assistant",
            content=full_content,
            thinking_steps=thinking_steps or None,
            event_type=effective_event_type,
        )
        await self.chat_repo.add_message(ai_msg)

        # 8. 推送结构化数据
        if parse_result.title:
            yield {"type": "title", "data": parse_result.title}
        else:
            yield {"type": "title", "data": content[:15] + ("..." if len(content) > 15 else "")}

        if parse_result.summary:
            yield {"type": "summary", "data": parse_result.summary}

        if parse_result.industry_names:
            yield {"type": "industries", "data": parse_result.industry_names}

        yield {"type": "done", "data": ""}

    def _build_messages(
        self,
        history: list[ChatMessage],
        event_type: str | None,
        raw_text: str | None = None,
        search_results: list[dict] | None = None,
    ) -> list[dict]:
        """将历史消息拼接为 OpenAI messages 数组，支持 LangGraph 增强上下文"""
        effective_type = event_type or "other"
        builder = PROMPT_BUILDERS.get(EventType(effective_type), general.build_prompt)

        messages: list[dict] = []

        # 截断历史（保留最近 N 轮，1 轮 = 1 user + 1 assistant）
        recent = history[-(MAX_HISTORY_ROUNDS * 2):]

        for msg in recent:
            if msg.role == "user":
                messages.append({"role": "user", "content": msg.content})
            elif msg.role == "assistant":
                messages.append({"role": "assistant", "content": msg.content})

        if not messages:
            return messages

        # 使用增强后的内容构建 system prompt
        user_content = raw_text or messages[-1].get("content", "")

        # 拼接知识库检索结果
        if search_results:
            context = self._build_context(user_content, search_results)
            system_prompt = builder(context)
        else:
            system_prompt = builder(user_content)

        messages.insert(0, {"role": "system", "content": system_prompt})

        # 如果 URL 爬取了内容，在最后一条用户消息前插入页面内容
        if raw_text and messages[-1].get("role") == "user" and raw_text != messages[-1]["content"]:
            context_msg = {"role": "system", "content": f"[页面内容]\n{raw_text[:5000]}"}
            messages.insert(-1, context_msg)

        return messages

    @staticmethod
    def _build_context(raw_text: str, search_results: list[dict]) -> str:
        """构建增强上下文，将知识库检索结果注入"""
        parts = ["[历史相关分析参考]"]
        for i, r in enumerate(search_results, 1):
            created = r.get("created_at", "")[:10]
            parts.append(f"{i}. 《{r['title']}》({r.get('event_type', '')}, {created}): {r.get('summary', '')}")
        parts.append("")
        parts.append(f"用户输入: {raw_text}")
        return "\n".join(parts)
