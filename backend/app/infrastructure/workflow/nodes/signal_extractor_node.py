"""信号提取节点 — 从风险裁决中提取结构化交易信号"""

import json
import logging
import re
import time

from app.infrastructure.workflow.prompts.stock_analysis.signal_extractor import SYSTEM_PROMPT, USER_TEMPLATE

logger = logging.getLogger(__name__)


def create_signal_extractor_node(ai_service):
    """
    闭包工厂：创建信号提取节点。

    从 risk_judge 的输出中提取结构化交易信号：
    action, target_price, confidence, risk_score, reasoning

    Args:
        ai_service: AIService 实例
    """

    async def signal_extractor_node(state: dict) -> dict:
        t_start = time.time()
        stock_code = state.get("stock_code", "")

        # 获取 risk_judge 的输出（从 messages 中最后一条）
        risk_judgment_text = _get_risk_judgment(state)

        user_content = USER_TEMPLATE.format(risk_judgment_text=risk_judgment_text)

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
                temperature=0.1,
                max_tokens=1024,
            ):
                if chunk.type == "content":
                    full_text += chunk.text
        except Exception as e:
            logger.error("[signal_extractor] stream_chat 失败: %s", e)
            return _default_signal_result(f"信号提取失败: {e}")

        # 解析 JSON 响应
        signal = _parse_signal_json(full_text)

        logger.info(
            "[耗时] signal_extractor 总耗时: %.3fs, stock=%s, action=%s, confidence=%.1f",
            time.time() - t_start, stock_code, signal.get("action", "未知"), signal.get("confidence", 0),
        )

        return {
            "action": signal.get("action", "持有"),
            "target_price": signal.get("target_price", 0),
            "confidence": signal.get("confidence", 0),
            "risk_score": signal.get("risk_score", 50),
            "reasoning": signal.get("reasoning", ""),
            "current_phase": "done",
        }

    return signal_extractor_node


def _get_risk_judgment(state: dict) -> str:
    """从 state 中获取风险裁决文本"""
    # 优先从 messages 中获取 risk_judge 的输出
    messages = state.get("messages", [])
    for msg in reversed(messages):
        if msg.get("agent") == "risk_judge" or msg.get("role") == "assistant":
            content = msg.get("content", "")
            if content:
                return content

    # 降级：从 risk_debate_state 中获取
    risk_debate_state = state.get("risk_debate_state", {})
    parts = []
    for key in ["risky_view", "safe_view", "neutral_view"]:
        view = risk_debate_state.get(key, "")
        if view:
            parts.append(view)
    if parts:
        return "\n\n".join(parts)

    return "无风险裁决数据"


def _parse_signal_json(text: str) -> dict:
    """从 AI 响应中解析 JSON 信号"""
    # 尝试从 markdown 代码块中提取 JSON
    json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if json_match:
        json_str = json_match.group(1)
    else:
        # 尝试直接解析整个文本为 JSON
        json_str = text.strip()

    try:
        result = json.loads(json_str)
        # 标准化字段
        return {
            "action": str(result.get("action", "持有")),
            "target_price": float(result.get("target_price", 0)),
            "confidence": float(result.get("confidence", 0)),
            "risk_score": float(result.get("risk_score", 50)),
            "reasoning": str(result.get("reasoning", "")),
        }
    except (json.JSONDecodeError, ValueError, TypeError) as e:
        logger.warning("[signal_extractor] JSON 解析失败: %s, 尝试从文本提取", e)
        return _extract_signal_from_text(text)


def _extract_signal_from_text(text: str) -> dict:
    """当 JSON 解析失败时，尝试从文本中提取信号字段"""
    result = {
        "action": "持有",
        "target_price": 0,
        "confidence": 50,
        "risk_score": 50,
        "reasoning": text[:200],
    }

    # 尝试提取 action
    action_match = re.search(r"action[\"':\s]+[\"']?(买入|持有|卖出)[\"']?", text)
    if action_match:
        result["action"] = action_match.group(1)

    # 尝试提取 target_price
    price_match = re.search(r"target_price[\"':\s]+(\d+\.?\d*)", text)
    if price_match:
        result["target_price"] = float(price_match.group(1))

    # 尝试提取 confidence
    conf_match = re.search(r"confidence[\"':\s]+(\d+\.?\d*)", text)
    if conf_match:
        result["confidence"] = float(conf_match.group(1))

    # 尝试提取 risk_score
    risk_match = re.search(r"risk_score[\"':\s]+(\d+\.?\d*)", text)
    if risk_match:
        result["risk_score"] = float(risk_match.group(1))

    return result


def _default_signal_result(error_msg: str) -> dict:
    """返回默认信号结果（用于错误降级）"""
    return {
        "action": "持有",
        "target_price": 0,
        "confidence": 0,
        "risk_score": 50,
        "reasoning": error_msg,
        "current_phase": "done",
    }
