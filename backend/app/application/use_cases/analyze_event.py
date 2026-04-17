"""AnalyzeEventUseCase — AI 事件分析核心用例"""

import json
import logging
import asyncio
from typing import AsyncGenerator

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
    def __init__(self, ai_service: AIService, max_retries: int = 2, retry_delay: float = 5.0):
        self.ai_service = ai_service
        self.parser = AnalysisParser()
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    async def execute(
        self, event_type: str, question: str,
    ) -> AsyncGenerator[dict, None]:
        """
        流式分析事件，yield SSE 事件字典。
        事件格式: {"type": "content"|"title"|"summary"|"industries"|"error"|"done", "data": ...}
        """
        # 获取 prompt
        builder = PROMPT_BUILDERS.get(EventType(event_type))
        if not builder:
            logger.error("不支持的事件类型: %s", event_type)
            yield {"type": "error", "data": f"不支持的事件类型: {event_type}"}
            return

        system_prompt = builder(question)
        logger.info("分析开始: event_type=%s, question前50字=%s", event_type, question[:50])

        # 流式调用 AI，含重试
        full_content = ""
        last_error = None

        for attempt in range(1, self.max_retries + 2):  # 1 次初始 + max_retries 次重试
            try:
                async for chunk in self.ai_service.stream_chat(system_prompt, question):
                    full_content += chunk
                    yield {"type": "content", "data": chunk}
                break  # 成功则退出重试循环

            except Exception as e:
                last_error = str(e)
                logger.warning("AI 调用失败 (attempt %d/%d): %s", attempt, self.max_retries + 1, last_error)
                if attempt <= self.max_retries:
                    yield {"type": "content", "data": f"\n\n⏳ 重试中...（{attempt}/{self.max_retries}）\n\n"}
                    await asyncio.sleep(self.retry_delay)
                else:
                    yield {"type": "error", "data": f"AI 分析失败: {last_error}"}
                    return

        # 解析结果
        logger.info("AI 内容生成完成, 总长度=%d, 开始解析", len(full_content))
        parse_result = self.parser.parse(full_content, event_type)
        logger.info("解析结果: title=%s, industries=%s", parse_result.title, parse_result.industry_names)

        # 推送 title
        if parse_result.title:
            yield {"type": "title", "data": parse_result.title}
        else:
            # 降级：截取前15字作为标题
            fallback_title = question[:15] + ("..." if len(question) > 15 else "")
            yield {"type": "title", "data": fallback_title}

        # 推送 summary
        if parse_result.summary:
            yield {"type": "summary", "data": parse_result.summary}

        # 推送 industries
        if parse_result.industry_names:
            yield {"type": "industries", "data": parse_result.industry_names}

        # 完成
        yield {"type": "done", "data": ""}
