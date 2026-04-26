"""交易员节点 — 根据投资计划生成具体交易建议"""

import logging
import time

from app.infrastructure.workflow.prompts.stock_analysis.trader import SYSTEM_PROMPT, USER_TEMPLATE

logger = logging.getLogger(__name__)


def create_trader_node(ai_service):
    """
    闭包工厂：创建交易员节点。

    Args:
        ai_service: AIService 实例
    """

    async def trader_node(state: dict) -> dict:
        t_start = time.time()
        stock_code = state.get("stock_code", "")
        stock_name = state.get("stock_name", "")

        investment_plan = state.get("investment_plan", "")

        user_content = USER_TEMPLATE.format(
            investment_plan=investment_plan,
            stock_name=stock_name,
            stock_code=stock_code,
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
                temperature=0.3,
                max_tokens=4096,
            ):
                if chunk.type == "content":
                    full_text += chunk.text
                    if content_queue:
                        await content_queue.put(chunk.text)
        except Exception as e:
            logger.error("[trader] stream_chat 失败: %s", e)
            full_text = f"交易建议生成失败: {e}"

        logger.info(
            "[耗时] trader 总耗时: %.3fs, stock=%s, plan_len=%d",
            time.time() - t_start, stock_code, len(full_text),
        )

        return {
            "trader_investment_plan": full_text,
            "current_agent": "trader",
            "current_phase": "trader",
        }

    return trader_node
