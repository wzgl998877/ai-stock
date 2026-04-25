"""研究管理器节点 — 综合辩论结果，制定投资计划"""

import logging
import time

from app.core.config import settings
from app.infrastructure.workflow.prompts.stock_analysis.research_manager import SYSTEM_PROMPT, USER_TEMPLATE

logger = logging.getLogger(__name__)


def create_research_manager_node(ai_service):
    """
    闭包工厂：创建研究管理器节点。

    使用深度思考模型综合看多和看空辩论结果，生成投资计划。

    Args:
        ai_service: AIService 实例
    """

    async def research_manager_node(state: dict) -> dict:
        t_start = time.time()
        stock_code = state.get("stock_code", "")
        stock_name = state.get("stock_name", "")

        # 获取辩论历史
        debate_state = state.get("investment_debate_state", {})
        debate_history = _build_debate_history(debate_state)

        user_content = USER_TEMPLATE.format(
            debate_history=debate_history,
        )

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]

        # 使用深度思考模型（如果配置了的话）
        deep_model = settings.llm_deep_model or None

        full_text = ""
        try:
            async for chunk in ai_service.stream_chat(
                system_prompt="",
                user_message="",
                history_messages=messages,
                model=deep_model,
                temperature=0.3,
                max_tokens=4096,
            ):
                if chunk.type == "content":
                    full_text += chunk.text
        except Exception as e:
            logger.error("[research_manager] stream_chat 失败: %s", e)
            full_text = f"投资计划生成失败: {e}"

        logger.info(
            "[耗时] research_manager 总耗时: %.3fs, stock=%s, plan_len=%d",
            time.time() - t_start, stock_code, len(full_text),
        )

        return {
            "investment_plan": full_text,
            "current_agent": "research_manager",
        }

    return research_manager_node


def _build_debate_history(debate_state: dict) -> str:
    """将辩论状态格式化为辩论历史文本"""
    parts = []

    bull = debate_state.get("bull_arguments", "")
    if bull:
        parts.append(f"【看多论据】\n{bull}")

    bear = debate_state.get("bear_arguments", "")
    if bear:
        parts.append(f"【看空论据】\n{bear}")

    rounds = debate_state.get("round", 0)
    if rounds > 0:
        parts.insert(0, f"辩论轮次: {rounds}")

    return "\n\n".join(parts) if parts else "暂无辩论记录"
