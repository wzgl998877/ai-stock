"""保守风险分析师节点 — 从保守角度评估交易风险"""

import logging

from app.infrastructure.workflow.prompts.stock_analysis.safe_debator import SYSTEM_PROMPT, USER_TEMPLATE

logger = logging.getLogger(__name__)


def create_safe_debator_node(ai_service):
    """
    闭包工厂：创建保守风险分析师节点。

    Args:
        ai_service: AIService 实例
    """

    async def safe_debator_node(state: dict) -> dict:
        stock_code = state.get("stock_code", "")

        trader_plan = state.get("trader_investment_plan", "")

        user_content = USER_TEMPLATE.format(trader_plan=trader_plan)

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]

        full_text = ""
        try:
            async for chunk in ai_service.stream_chat(
                system_prompt="",
                user_message="",
                history_messages=messages,
                temperature=0.5,
                max_tokens=4096,
            ):
                if chunk.type == "content":
                    full_text += chunk.text
        except Exception as e:
            logger.error("[safe_debator] stream_chat 失败: %s", e)
            full_text = f"保守风险分析生成失败: {e}"

        # 更新风险辩论状态
        risk_debate_state = state.get("risk_debate_state", {})
        risk_debate_state["safe_view"] = full_text
        risk_debate_state["round"] = risk_debate_state.get("round", 0) + 1

        logger.info(
            "[safe_debator] 完成: stock=%s, report_len=%d",
            stock_code, len(full_text),
        )

        return {
            "risk_debate_state": risk_debate_state,
            "current_agent": "safe_debator",
        }

    return safe_debator_node
