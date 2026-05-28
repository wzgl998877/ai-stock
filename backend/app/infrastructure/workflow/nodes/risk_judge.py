"""风险裁决节点 — 综合所有风险观点，给出最终风险评估"""

import json
import logging
import re
import time

from app.core.config import settings
from app.infrastructure.workflow.prompts.stock_analysis.risk_judge import SYSTEM_PROMPT, USER_TEMPLATE

logger = logging.getLogger(__name__)


def _parse_risk_judge_json(text: str) -> dict:
    """从 AI 响应中解析风险裁决 JSON，失败时返回空 dict。"""
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
            "risk_score": float(result.get("risk_score", 50)),
            "reasoning": str(result.get("reasoning", "")),
        }
    except (json.JSONDecodeError, ValueError, TypeError) as e:
        logger.warning("[risk_judge] JSON 解析失败: %s", e)
        return {}


def create_risk_judge_node(ai_service):
    """
    闭包工厂：创建风险裁决节点。

    使用深度思考模型综合激进、保守、中立三方观点，生成最终风险裁决。

    Args:
        ai_service: AIService 实例
    """

    async def risk_judge_node(state: dict) -> dict:
        t_start = time.time()
        stock_code = state.get("stock_code", "")

        risk_debate_state = state.get("risk_debate_state", {})
        risky_view = risk_debate_state.get("risky_view", "")
        safe_view = risk_debate_state.get("safe_view", "")
        neutral_view = risk_debate_state.get("neutral_view", "")

        user_content = USER_TEMPLATE.format(
            risky_view=risky_view,
            safe_view=safe_view,
            neutral_view=neutral_view,
        )

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]

        # 使用深度思考模型
        deep_model = settings.llm_deep_model or None

        full_text = ""
        content_queue = state.get("_content_queue")
        try:
            async for chunk in ai_service.stream_chat(
                system_prompt="",
                user_message="",
                history_messages=messages,
                model=deep_model,
                temperature=0.2,
                max_tokens=100000,
            ):
                if chunk.type == "content":
                    full_text += chunk.text
                    if content_queue:
                        await content_queue.put(chunk.text)
        except Exception as e:
            logger.error("[risk_judge] stream_chat 失败: %s", e)
            full_text = f"风险裁决生成失败: {e}"

        # 解析 AI 返回的结构化数据
        parsed = _parse_risk_judge_json(full_text)

        # 将裁决结果追加到 messages 供 signal_extractor 文本解析兜底
        new_messages = list(state.get("messages", []))
        new_messages.append({
            "role": "assistant",
            "content": full_text,
            "agent": "risk_judge",
        })

        result = {
            "messages": new_messages,
            "current_agent": "risk_judge",
        }

        # 将结构化字段写入 state，供 signal_extractor 直接使用
        if parsed:
            for key in ("action", "target_price", "stop_loss_price", "expected_return", "confidence", "risk_score", "reasoning"):
                val = parsed.get(key)
                if val:
                    result[f"risk_judge_{key}"] = val
            logger.info(
                "[耗时] risk_judge 总耗时: %.3fs, stock=%s, report_len=%d, action=%s, target=%.2f",
                time.time() - t_start, stock_code, len(full_text),
                parsed.get("action", ""), parsed.get("target_price", 0),
            )
        else:
            logger.info(
                "[耗时] risk_judge 总耗时: %.3fs, stock=%s, report_len=%d (JSON解析失败)",
                time.time() - t_start, stock_code, len(full_text),
            )

        return result

    return risk_judge_node
