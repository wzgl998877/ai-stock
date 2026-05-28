"""交易员节点 — 根据投资计划生成具体交易建议"""

import json
import logging
import re
import time

from app.infrastructure.workflow.prompts.stock_analysis.trader import SYSTEM_PROMPT, USER_TEMPLATE

logger = logging.getLogger(__name__)


def _parse_trader_json(text: str) -> dict:
    """从 AI 响应中解析交易决策 JSON，失败时返回空 dict。"""
    json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    json_str = json_match.group(1) if json_match else text.strip()
    try:
        result = json.loads(json_str)
        return {
            "action": str(result.get("action", "")),
            "target_price": float(result.get("target_price", 0)),
            "stop_loss_price": float(result.get("stop_loss_price", 0)),
            "expected_return": float(result.get("expected_return", 0)),
            "confidence": float(result.get("confidence", 0)),
            "reasoning": str(result.get("reasoning", "")),
        }
    except (json.JSONDecodeError, ValueError, TypeError) as e:
        logger.warning("[trader] JSON 解析失败: %s", e)
        return {}


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
                max_tokens=100000,
            ):
                if chunk.type == "content":
                    full_text += chunk.text
                    if content_queue:
                        await content_queue.put(chunk.text)
        except Exception as e:
            logger.error("[trader] stream_chat 失败: %s", e)
            full_text = f"交易建议生成失败: {e}"

        # 解析 AI 返回的结构化数据
        parsed = _parse_trader_json(full_text)
        result = {
            "trader_investment_plan": full_text,
            "current_agent": "trader",
            "current_phase": "trader",
        }
        # 将解析到的结构化字段写入 state，供下游节点直接使用
        if parsed:
            for key in ("action", "target_price", "stop_loss_price", "expected_return", "confidence", "reasoning"):
                val = parsed.get(key)
                if val:
                    result[f"trader_{key}"] = val
            logger.info(
                "[耗时] trader 总耗时: %.3fs, stock=%s, plan_len=%d, action=%s, target=%.2f",
                time.time() - t_start, stock_code, len(full_text),
                parsed.get("action", ""), parsed.get("target_price", 0),
            )
        else:
            logger.info(
                "[耗时] trader 总耗时: %.3fs, stock=%s, plan_len=%d (JSON解析失败)",
                time.time() - t_start, stock_code, len(full_text),
            )

        return result

    return trader_node
