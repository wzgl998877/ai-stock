"""summarize_context 节点 — 用 LLM 对联网搜索 + 知识库检索结果进行提炼总结"""

import logging

from app.infrastructure.workflow.state.analysis_state import AnalysisState

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是一位专业的信息整理助手。你的任务是阅读以下搜索结果和知识库文章，从中提炼出与用户问题相关的关键事实、数据和观点。

要求：
1. 保留所有具体的数字、日期、公司名称、政策名称等关键事实
2. 按主题分类整理，使用清晰的标题和要点格式
3. 标注信息来源（互联网搜索 / 知识库）
4. 去除广告、重复内容和无关信息
5. 如果有矛盾信息，标注各方说法
6. 用中文输出

请直接输出整理后的内容，不要加前言或总结性开头。"""


def create_summarize_context_node(ai_service):
    """
    创建 summarize_context 节点。

    Args:
        ai_service: AIService 实例，用于调用 LLM 做总结
    """

    async def summarize_context_node(state: AnalysisState) -> dict:
        web_results = state.get("web_search_results", [])
        search_results = state.get("search_results", [])
        source = state.get("source", "")

        # 没有任何上下文数据，跳过
        if not web_results and not search_results:
            logger.info("[summarize_context] 无搜索/检索结果，跳过总结")
            return {"summarized_context": "", "thinking_done_msg": "无需整理上下文"}

        # 拼接所有原始材料
        context_parts = []

        if web_results:
            context_parts.append("=== 互联网搜索结果 ===")
            for i, r in enumerate(web_results, 1):
                title = r.get("title", "")
                content = r.get("content", "")
                url = r.get("url", "")
                context_parts.append(f"\n--- 搜索结果 {i}: {title} ---")
                context_parts.append(f"来源: {url}")
                context_parts.append(content)
                context_parts.append("")

        if search_results:
            context_parts.append("\n=== 知识库历史文章 ===")
            for i, r in enumerate(search_results, 1):
                title = r.get("title", "")
                summary = r.get("summary", "")
                content = r.get("content", "")
                event_type = r.get("event_type", "")
                created = r.get("created_at", "")[:10]
                context_parts.append(f"\n--- 文章 {i}: {title} ({event_type}, {created}) ---")
                if summary:
                    context_parts.append(f"摘要: {summary}")
                if content:
                    context_parts.append(f"正文: {content}")
                context_parts.append("")

        raw_context = "\n".join(context_parts)
        logger.info(
            "[summarize_context] 原始材料长度=%d, web=%d条, kb=%d条",
            len(raw_context), len(web_results), len(search_results),
        )

        # 调用 LLM 总结
        user_message = f"用户问题: {source}\n\n请整理以下信息，提炼与用户问题相关的关键内容：\n\n{raw_context}"

        summarized = ""
        try:
            async for chunk in ai_service.stream_chat(
                system_prompt=SYSTEM_PROMPT,
                user_message=user_message,
                temperature=0.3,
                max_tokens=2048,
            ):
                if chunk.type == "content":
                    summarized += chunk.text
        except Exception as e:
            logger.error("[summarize_context] LLM 总结失败: %s", e, exc_info=True)
            # 降级：直接拼接原始材料的摘要部分
            fallback_parts = []
            for r in web_results:
                fallback_parts.append(f"- {r.get('title', '')}: {r.get('content', '')[:500]}")
            for r in search_results:
                fallback_parts.append(f"- {r.get('title', '')}: {r.get('summary', '')[:500]}")
            summarized = "\n".join(fallback_parts)

        logger.info("[summarize_context] 总结完成, 长度=%d", len(summarized))
        return {"summarized_context": summarized, "thinking_done_msg": "信息整理完成"}

    return summarize_context_node
