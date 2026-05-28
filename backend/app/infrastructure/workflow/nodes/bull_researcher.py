"""看多研究员节点 — 汇总分析师报告，生成看多论据"""

import json
import logging
import time

from app.infrastructure.workflow.prompts.stock_analysis.bull_researcher import SYSTEM_PROMPT, USER_TEMPLATE

logger = logging.getLogger(__name__)


def create_bull_researcher_node(ai_service):
    """
    闭包工厂：创建看多研究员节点。

    Args:
        ai_service: AIService 实例
    """

    async def bull_researcher_node(state: dict) -> dict:
        t_start = time.time()
        stock_code = state.get("stock_code", "")
        stock_name = state.get("stock_name", "")

        # 汇总所有分析师报告
        analyst_reports = _build_analyst_reports(state)
        user_content = USER_TEMPLATE.format(
            analyst_reports=analyst_reports,
            stock_name=stock_name,
        )

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]

        # 调用 AI 获取看多论据
        full_text = ""
        content_queue = state.get("_content_queue")
        try:
            async for chunk in ai_service.stream_chat(
                system_prompt="",
                user_message="",
                history_messages=messages,
                temperature=0.5,
                max_tokens=100000,
            ):
                if chunk.type == "content":
                    full_text += chunk.text
                    if content_queue:
                        await content_queue.put(chunk.text)
        except Exception as e:
            logger.error("[bull_researcher] stream_chat 失败: %s", e)
            full_text = f"看多研究分析生成失败: {e}"

        # 更新辩论状态
        debate_state = state.get("investment_debate_state", {})
        debate_state["bull_arguments"] = full_text
        debate_state["round"] = debate_state.get("round", 0) + 1

        logger.info(
            "[耗时] bull_researcher 总耗时: %.3fs, stock=%s, report_len=%d",
            time.time() - t_start, stock_code, len(full_text),
        )

        return {
            "investment_debate_state": debate_state,
            "current_agent": "bull_researcher",
            "current_phase": "debate",
        }

    return bull_researcher_node


def _build_analyst_reports(state: dict) -> str:
    """将所有分析师报告格式化为文本"""
    parts = []

    market = state.get("market_report", "")
    if market:
        parts.append(f"【技术面分析报告】\n{market}")

    fundamentals = state.get("fundamentals_report", "")
    if fundamentals:
        parts.append(f"【基本面分析报告】\n{fundamentals}")

    news = state.get("news_report", "")
    if news:
        parts.append(f"【新闻分析报告】\n{news}")

    sentiment = state.get("sentiment_report", "")
    if sentiment:
        parts.append(f"【情绪分析报告】\n{sentiment}")

    return "\n\n".join(parts)
