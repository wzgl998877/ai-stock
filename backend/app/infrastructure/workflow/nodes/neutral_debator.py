"""中立风险分析师节点 — 平衡激进与保守观点，给出中性评估"""

import logging
import time

from app.infrastructure.workflow.prompts.stock_analysis.neutral_debator import SYSTEM_PROMPT, USER_TEMPLATE

logger = logging.getLogger(__name__)


def create_neutral_debator_node(ai_service):
    """
    闭包工厂：创建中立风险分析师节点。

    Args:
        ai_service: AIService 实例
    """

    async def neutral_debator_node(state: dict) -> dict:
        t_start = time.time()
        stock_code = state.get("stock_code", "")

        risk_debate_state = state.get("risk_debate_state", {})
        risky_view = risk_debate_state.get("risky_view", "")
        safe_view = risk_debate_state.get("safe_view", "")

        user_content = USER_TEMPLATE.format(
            risky_view=risky_view,
            safe_view=safe_view,
        )

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]

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
            logger.error("[neutral_debator] stream_chat 失败: %s", e)
            full_text = f"中立风险分析生成失败: {e}"

        # 更新风险辩论状态
        risk_debate_state["neutral_view"] = full_text
        risk_debate_state["round"] = risk_debate_state.get("round", 0) + 1

        logger.info(
            "[耗时] neutral_debator 总耗时: %.3fs, stock=%s, report_len=%d",
            time.time() - t_start, stock_code, len(full_text),
        )

        return {
            "risk_debate_state": risk_debate_state,
            "current_agent": "neutral_debator",
        }

    return neutral_debator_node
