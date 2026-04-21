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

        # 2. 判断是否为追问（有历史 assistant 回复则跳过 LangGraph 预处理）
        existing_messages = await self.chat_repo.list_messages(session_id)
        is_follow_up = any(m.role == "assistant" for m in existing_messages[:-1]) if len(existing_messages) > 1 else False

        raw_text = content
        search_results: list[dict] = []
        web_search_results: list[dict] = []
        thinking_steps: list[dict] = []

        if self.analysis_graph and not is_follow_up:
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
                # 根据条件边的实际路由决定下一个 running 事件，避免跳过的节点残留 running 状态
                accumulated: dict = {}

                # 实际执行路径：agent_classify 后根据 need_search 决定是否经过 web_search
                EXECUTION_PATHS = [
                    ["agent_classify", "web_search", "load", "retrieve"],  # need_search=True
                    ["agent_classify", "load", "retrieve"],                # need_search=False
                ]

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

                        # 确定下一个实际执行的节点
                        next_node = None
                        if node_name == "agent_classify":
                            # 根据条件边结果决定下一个节点
                            need_search = accumulated.get("need_search", False)
                            next_node = "web_search" if need_search else "load"
                        elif node_name == "web_search":
                            next_node = "load"
                        elif node_name == "load":
                            if "retrieve" in all_nodes:
                                next_node = "retrieve"

                        # 发出下一个节点的 running 事件
                        if next_node and next_node in all_nodes:
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
                web_search_results = accumulated.get("web_search_results", [])

            except Exception as e:
                logger.warning("LangGraph 预处理失败，降级使用原始输入: %s", e)
                raw_text = content

        # 3. 构建 messages 数组（多轮对话 + 增强上下文）
        # 追问时复用已有的 existing_messages，首轮需要重新查询（LangGraph 后数据有更新）
        history = existing_messages if is_follow_up else await self.chat_repo.list_messages(session_id)
        messages = self._build_messages(history, effective_event_type, raw_text, search_results, web_search_results)

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
            # 确保 reasoning 的 done 事件
            reasoning_done = {"step": "reasoning", "status": "failed", "message": "分析失败"}
            thinking_steps.append(reasoning_done)
            yield {"type": "thinking", "data": reasoning_done}
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
        web_search_results: list[dict] | None = None,
    ) -> list[dict]:
        """将历史消息拼接为 OpenAI messages 数组，支持多轮对话上下文"""
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

        # 判断是否为追问（历史中已有 assistant 回复）
        has_prior_response = any(m.role == "assistant" for m in recent[:-1]) if len(recent) > 1 else False

        # 当前用户输入
        user_content = raw_text or messages[-1].get("content", "")

        if has_prior_response:
            # 追问模式：使用对话式 system prompt，保持上下文连贯
            context_parts = []
            if web_search_results:
                context_parts.append("[本轮互联网搜索结果]")
                for i, r in enumerate(web_search_results, 1):
                    context_parts.append(f"{i}. {r.get('title', '')}: {r.get('content', '')[:300]}")
                context_parts.append("")

            if search_results:
                context_parts.append("[历史相关分析参考]")
                for i, r in enumerate(search_results, 1):
                    created = r.get("created_at", "")[:10]
                    context_parts.append(f"{i}. 《{r['title']}》({r.get('event_type', '')}, {created}): {r.get('summary', '')}")
                context_parts.append("")

            system_content = "你是一位专业的A股市场分析师。用户正在基于之前的分析进行追问。请根据之前的对话上下文直接回答用户的问题，保持上下文连贯。不要重新做完整分析，而是针对追问的具体内容给出专业回答。如果追问涉及数据来源或细节，请根据你之前回答的内容来回应。所有股票相关内容仅供学习研究参考，不构成投资建议。"
            if context_parts:
                system_content += "\n\n" + "\n".join(context_parts)

            messages.insert(0, {"role": "system", "content": system_content})
        else:
            # 首轮：使用完整的分析型 system prompt
            context_parts = []
            if web_search_results:
                context_parts.append("[互联网搜索结果]")
                for i, r in enumerate(web_search_results, 1):
                    context_parts.append(f"{i}. {r.get('title', '')}: {r.get('content', '')[:300]}")
                context_parts.append("")

            if search_results:
                context_parts.append("[历史相关分析参考]")
                for i, r in enumerate(search_results, 1):
                    created = r.get("created_at", "")[:10]
                    context_parts.append(f"{i}. 《{r['title']}》({r.get('event_type', '')}, {created}): {r.get('summary', '')}")
                context_parts.append("")

            if context_parts:
                context_parts.append(f"用户输入: {user_content}")
                system_prompt = builder("\n".join(context_parts))
            else:
                system_prompt = builder(user_content)

            messages.insert(0, {"role": "system", "content": system_prompt})

            # 如果 URL 爬取了内容，在最后一条用户消息前插入页面内容
            if raw_text and messages[-1].get("role") == "user" and raw_text != messages[-1]["content"]:
                context_msg = {"role": "system", "content": f"[页面内容]\n{raw_text[:5000]}"}
                messages.insert(-1, context_msg)

        return messages
