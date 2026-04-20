"""AnalyzeEventUseCase — AI 事件分析核心用例（LangGraph 版）"""

import logging
import asyncio
from typing import AsyncGenerator, Optional

from app.domain.services.analysis_parser import AnalysisParser
from app.domain.value_objects.event_type import EventType
from app.infrastructure.ai.ai_service import AIService
from app.infrastructure.ai.prompts import geopolicy, policy, earnings, chain, general

logger = logging.getLogger(__name__)

# 事件类型 → prompt 模块映射
PROMPT_BUILDERS = {
    EventType.GEO_POLITICAL: geopolicy.build_prompt,
    EventType.POLICY: policy.build_prompt,
    EventType.EARNINGS: earnings.build_prompt,
    EventType.SUPPLY_CHAIN: chain.build_prompt,
    EventType.OTHER: general.build_prompt,
}


class AnalyzeEventUseCase:
    def __init__(
        self,
        ai_service: AIService,
        analysis_graph=None,
        max_retries: int = 2,
        retry_delay: float = 5.0,
    ):
        self.ai_service = ai_service
        self.analysis_graph = analysis_graph  # LangGraph 编译后的工作流（可选）
        self.parser = AnalysisParser()
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    async def execute(
        self, event_type: str, question: str,
    ) -> AsyncGenerator[dict, None]:
        """
        流式分析事件，yield SSE 事件字典。

        流程：
        1. [LangGraph] classify -> load -> retrieve，获取预处理数据
        2. [UseCase] 拼装 context + 选择 Prompt
        3. [UseCase] AIService.stream_chat() 流式推理
        4. [UseCase] AnalysisParser 解析结果
        """
        # ---- Phase 1: LangGraph 预处理 ----
        raw_text = question
        search_results = []

        if self.analysis_graph:
            try:
                initial_state = {
                    "source": question,
                    "event_type": event_type,
                }
                result = await self.analysis_graph.ainvoke(initial_state)
                raw_text = result.get("raw_text", question)
                search_results = result.get("search_results", [])

                if result.get("error"):
                    logger.warning("LangGraph 预处理有错误: %s", result["error"])

            except Exception as e:
                logger.error("LangGraph 执行失败，降级为直接文本分析: %s", e, exc_info=True)
                raw_text = question

        # ---- Phase 2: 构建 Prompt ----
        builder = PROMPT_BUILDERS.get(EventType(event_type))
        if not builder:
            logger.error("不支持的事件类型: %s", event_type)
            yield {"type": "error", "data": f"不支持的事件类型: {event_type}"}
            return

        user_message = self._build_user_message(raw_text, search_results)
        system_prompt = builder(user_message)

        logger.info(
            "分析开始: event_type=%s, raw_text长度=%d, search_results=%d",
            event_type, len(raw_text), len(search_results),
        )

        # ---- Phase 3: 流式推理 ----
        full_content = ""

        for attempt in range(1, self.max_retries + 2):
            try:
                async for chunk in self.ai_service.stream_chat(system_prompt, user_message):
                    full_content += chunk
                    yield {"type": "content", "data": chunk}
                break

            except Exception as e:
                last_error = str(e)
                logger.warning("AI 调用失败 (attempt %d/%d): %s", attempt, self.max_retries + 1, last_error)
                if attempt <= self.max_retries:
                    yield {"type": "content", "data": f"\n\n⏳ 重试中...（{attempt}/{self.max_retries}）\n\n"}
                    await asyncio.sleep(self.retry_delay)
                else:
                    yield {"type": "error", "data": f"AI 分析失败: {last_error}"}
                    return

        # ---- Phase 4: 解析结果 ----
        logger.info("AI 内容生成完成, 总长度=%d, 开始解析", len(full_content))
        parse_result = self.parser.parse(full_content, event_type)
        logger.info("解析结果: title=%s, industries=%s", parse_result.title, parse_result.industry_names)

        if parse_result.title:
            yield {"type": "title", "data": parse_result.title}
        else:
            fallback_title = question[:15] + ("..." if len(question) > 15 else "")
            yield {"type": "title", "data": fallback_title}

        if parse_result.summary:
            yield {"type": "summary", "data": parse_result.summary}

        if parse_result.industry_names:
            yield {"type": "industries", "data": parse_result.industry_names}

        yield {"type": "done", "data": ""}

    def _build_user_message(self, raw_text: str, search_results: list[dict]) -> str:
        """构建增强后的 user_message，将历史检索结果作为附加 context 注入。"""
        if not search_results:
            return raw_text

        context_parts = ["[历史相关分析参考]"]
        for i, r in enumerate(search_results, 1):
            created = r.get("created_at", "")[:10]
            context_parts.append(
                f"{i}. 《{r['title']}》({r['event_type']}, {created}): {r['summary']}"
            )
        context_parts.append("")
        context_parts.append(f"用户输入: {raw_text}")

        return "\n".join(context_parts)
