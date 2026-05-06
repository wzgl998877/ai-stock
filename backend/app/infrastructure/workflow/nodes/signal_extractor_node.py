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

        # === 优先从 state 中获取 risk_judge 写入的结构化字段 ===
        # risk_judge 和 trader 节点会将解析后的 JSON 写入 state，直接使用
        state_action = state.get("risk_judge_action") or state.get("trader_action") or ""
        state_target_price = state.get("risk_judge_target_price") or state.get("trader_target_price") or 0
        state_stop_loss = state.get("risk_judge_stop_loss_price") or state.get("trader_stop_loss_price") or 0
        state_expected_return = state.get("risk_judge_expected_return") or state.get("trader_expected_return") or 0
        state_confidence = state.get("risk_judge_confidence") or state.get("trader_confidence") or 0
        state_risk_score = state.get("risk_judge_risk_score", 50) or 50
        state_reasoning = state.get("risk_judge_reasoning") or state.get("trader_reasoning") or ""

        # 如果 state 中已有完整结构化数据，直接使用，跳过 AI 调用
        if state_action and state_target_price and state_confidence:
            logger.info(
                "[耗时] signal_extractor 总耗时: %.3fs, stock=%s, action=%s, confidence=%.1f (直接从state取值)",
                time.time() - t_start, stock_code, state_action, state_confidence,
            )
            return {
                "action": state_action,
                "target_price": state_target_price,
                "stop_loss_price": state_stop_loss,
                "expected_return": state_expected_return,
                "confidence": state_confidence,
                "risk_score": state_risk_score,
                "reasoning": state_reasoning,
                "current_phase": "done",
            }

        # === state 中无完整数据，降级为 AI 文本提取 ===
        risk_judgment_text = _get_risk_judgment(state)

        user_content = USER_TEMPLATE.format(risk_judgment_text=risk_judgment_text)

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
            logger.error("[signal_extractor] stream_chat 失败: %s", e)
            # AI 调用失败时，尝试用 state 中的部分数据兜底
            return _merge_signal_with_state(_default_signal_result(f"信号提取失败: {e}"), state)

        # 解析 JSON 响应
        signal = _parse_signal_json(full_text)

        # 用 state 中的结构化数据补全 signal 中缺失的字段
        merged = _merge_signal_with_state(signal, state)

        logger.info(
            "[耗时] signal_extractor 总耗时: %.3fs, stock=%s, action=%s, confidence=%.1f (AI文本提取)",
            time.time() - t_start, stock_code, merged.get("action", "未知"), merged.get("confidence", 0),
        )

        return {
            "action": merged.get("action", "持有"),
            "target_price": merged.get("target_price", 0),
            "stop_loss_price": merged.get("stop_loss_price", 0),
            "expected_return": merged.get("expected_return", 0),
            "confidence": merged.get("confidence", 0),
            "risk_score": merged.get("risk_score", 50),
            "reasoning": merged.get("reasoning", ""),
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
            "stop_loss_price": float(result.get("stop_loss_price", 0)),
            "expected_return": float(result.get("expected_return", 0)),
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
        "stop_loss_price": 0,
        "expected_return": 0,
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

    # 尝试提取 stop_loss_price
    stop_loss_match = re.search(r"stop_loss_price[\"':\s]+(\d+\.?\d*)", text)
    if stop_loss_match:
        result["stop_loss_price"] = float(stop_loss_match.group(1))

    # 尝试提取 expected_return
    er_match = re.search(r"expected_return[\"':\s]+([-]?\d+\.?\d*)", text)
    if er_match:
        result["expected_return"] = float(er_match.group(1))

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
        "stop_loss_price": 0,
        "expected_return": 0,
        "confidence": 0,
        "risk_score": 50,
        "reasoning": error_msg,
        "current_phase": "done",
    }


def _merge_signal_with_state(signal: dict, state: dict) -> dict:
    """将 AI 解析的 signal 与 state 中 trader/risk_judge 写入的结构化数据合并。

    策略：signal 中有效值（非0非空）优先，state 值兜底。
    """
    def _pick(*values):
        for v in values:
            if v and v != 0:
                return v
        return 0

    return {
        "action": signal.get("action") or state.get("risk_judge_action") or state.get("trader_action") or "持有",
        "target_price": _pick(
            signal.get("target_price", 0),
            state.get("risk_judge_target_price", 0),
            state.get("trader_target_price", 0),
        ),
        "stop_loss_price": _pick(
            signal.get("stop_loss_price", 0),
            state.get("risk_judge_stop_loss_price", 0),
            state.get("trader_stop_loss_price", 0),
        ),
        "expected_return": _pick(
            signal.get("expected_return", 0),
            state.get("risk_judge_expected_return", 0),
            state.get("trader_expected_return", 0),
        ),
        "confidence": _pick(
            signal.get("confidence", 0),
            state.get("risk_judge_confidence", 0),
            state.get("trader_confidence", 0),
        ),
        "risk_score": _pick(
            signal.get("risk_score", 0),
            state.get("risk_judge_risk_score", 0),
        ) or 50,
        "reasoning": signal.get("reasoning") or state.get("risk_judge_reasoning") or state.get("trader_reasoning") or "",
    }
