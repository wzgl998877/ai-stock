"""快速决策节点 — 仅从技术和基本面报告生成简要决策（quick模式）"""

import json
import logging
import re
import time

from app.infrastructure.workflow.prompts.stock_analysis.signal_extractor import SYSTEM_PROMPT

logger = logging.getLogger(__name__)

QUICK_DECISION_TEMPLATE = """根据以下分析报告，快速给出简要投资决策：

【技术面分析报告】
{market_report}

【基本面分析报告】
{fundamentals_report}

请直接给出决策，用以下JSON格式输出：
```json
{{"action": "买入/持有/卖出", "target_price": 数字, "confidence": 0-100, "risk_score": 0-100, "reasoning": "简短决策理由"}}
```"""


def create_quick_decision_node(ai_service):
    """
    闭包工厂：创建快速决策节点。

    仅从 market_report 和 fundamentals_report 生成简要决策，
    用于 quick 分析模式。

    Args:
        ai_service: AIService 实例
    """

    async def quick_decision_node(state: dict) -> dict:
        t_start = time.time()
        stock_code = state.get("stock_code", "")

        market_report = state.get("market_report", "")
        fundamentals_report = state.get("fundamentals_report", "")

        user_content = QUICK_DECISION_TEMPLATE.format(
            market_report=market_report,
            fundamentals_report=fundamentals_report,
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
                temperature=0.1,
                max_tokens=1024,
            ):
                if chunk.type == "content":
                    full_text += chunk.text
                    if content_queue:
                        await content_queue.put(chunk.text)
        except Exception as e:
            logger.error("[quick_decision] stream_chat 失败: %s", e)
            return _default_quick_result(f"快速决策生成失败: {e}")

        # 解析 JSON
        signal = _parse_signal_json(full_text)

        logger.info(
            "[耗时] quick_decision 总耗时: %.3fs, stock=%s, action=%s, confidence=%.1f",
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

    return quick_decision_node


def _parse_signal_json(text: str) -> dict:
    """从 AI 响应中解析 JSON 信号"""
    json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if json_match:
        json_str = json_match.group(1)
    else:
        json_str = text.strip()

    try:
        result = json.loads(json_str)
        return {
            "action": str(result.get("action", "持有")),
            "target_price": float(result.get("target_price", 0)),
            "confidence": float(result.get("confidence", 0)),
            "risk_score": float(result.get("risk_score", 50)),
            "reasoning": str(result.get("reasoning", "")),
        }
    except (json.JSONDecodeError, ValueError, TypeError) as e:
        logger.warning("[quick_decision] JSON 解析失败: %s", e)
        return _extract_signal_from_text(text)


def _extract_signal_from_text(text: str) -> dict:
    """从文本中提取信号字段"""
    result = {
        "action": "持有",
        "target_price": 0,
        "confidence": 50,
        "risk_score": 50,
        "reasoning": text[:200],
    }

    action_match = re.search(r"action[\"':\s]+[\"']?(买入|持有|卖出)[\"']?", text)
    if action_match:
        result["action"] = action_match.group(1)

    price_match = re.search(r"target_price[\"':\s]+(\d+\.?\d*)", text)
    if price_match:
        result["target_price"] = float(price_match.group(1))

    conf_match = re.search(r"confidence[\"':\s]+(\d+\.?\d*)", text)
    if conf_match:
        result["confidence"] = float(conf_match.group(1))

    risk_match = re.search(r"risk_score[\"':\s]+(\d+\.?\d*)", text)
    if risk_match:
        result["risk_score"] = float(risk_match.group(1))

    return result


def _default_quick_result(error_msg: str) -> dict:
    """返回默认快速决策结果"""
    return {
        "action": "持有",
        "target_price": 0,
        "confidence": 0,
        "risk_score": 50,
        "reasoning": error_msg,
        "current_phase": "done",
    }
