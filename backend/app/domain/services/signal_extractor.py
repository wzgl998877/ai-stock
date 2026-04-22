"""SignalExtractor — 从 Risk Judge 输出中提取结构化交易信号

适配自 TradingAgents-CN 的 SignalProcessor，多层降级链：
JSON → 正则 → 智能推算 → 默认持有
"""

import json
import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)


# Action 容错映射
ACTION_ALIASES: dict[str, str] = {
    "买入": "买入", "buy": "买入", "强烈买入": "买入", "建议买入": "买入",
    "持有": "持有", "hold": "持有", "观望": "持有", "继续持有": "持有", "维持": "持有",
    "卖出": "卖出", "sell": "卖出", "强烈卖出": "卖出", "建议卖出": "卖出", "减持": "卖出",
}

DEFAULT_ACTION = "持有"


class SignalExtractor:
    """从文本中提取结构化交易信号"""

    def extract(self, text: str) -> dict:
        """
        从文本中提取交易信号，返回结构化字典。

        降级链：JSON提取 → 正则提取 → 智能推算 → 默认持有
        """
        result = self._try_json_extract(text)
        if result:
            return result

        result = self._try_regex_extract(text)
        if result:
            return result

        result = self._try_smart_estimate(text)
        if result:
            return result

        # 最终降级：默认持有
        logger.warning("信号提取全部降级，返回默认持有")
        return {
            "action": DEFAULT_ACTION,
            "target_price": 0.0,
            "confidence": 0.3,
            "risk_score": 0.7,
            "reasoning": "无法提取明确信号，默认持有建议",
        }

    def _try_json_extract(self, text: str) -> Optional[dict]:
        """尝试从文本中提取JSON格式的决策"""
        # 尝试提取 ```json ... ``` 代码块
        json_match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group(1))
                return self._normalize_decision(data)
            except json.JSONDecodeError:
                pass

        # 尝试提取任意 JSON 对象
        brace_match = re.search(r"\{[^{}]*\"action\"[^{}]*\}", text, re.DOTALL)
        if brace_match:
            try:
                data = json.loads(brace_match.group(0))
                return self._normalize_decision(data)
            except json.JSONDecodeError:
                pass

        return None

    def _try_regex_extract(self, text: str) -> Optional[dict]:
        """尝试用正则提取决策"""
        # 提取 action
        action = DEFAULT_ACTION
        for pattern in [r"(?:操作方向|建议|action)[：:]\s*(买入|持有|卖出|buy|hold|sell)",
                        r"(?:建议|决策)[：:]\s*(买入|持有|卖出)"]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                action = ACTION_ALIASES.get(match.group(1).lower(), ACTION_ALIASES.get(match.group(1), DEFAULT_ACTION))
                break

        # 提取 target_price（14种中文价格模式）
        target_price = 0.0
        price_patterns = [
            r"目标价[为是：:\s]*(\d+\.?\d*)",
            r"目标价格[为是：:\s]*(\d+\.?\d*)",
            r"合理价格[为是：:\s]*(\d+\.?\d*)",
            r"建议买入价[为是：:\s]*(\d+\.?\d*)",
            r"目标位[为是：:\s]*(\d+\.?\d*)",
            r"看?到?(\d+\.?\d*)\s*元",
            r"目标(\d+\.?\d*)",
            r"上行空间.*?(\d+\.?\d*)",
            r"(\d+\.?\d*)\s*元.*?目标",
        ]
        for pattern in price_patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    target_price = float(match.group(1))
                    if target_price > 0:
                        break
                except ValueError:
                    continue

        # 提取 confidence
        confidence = 0.5
        conf_match = re.search(r"(?:置信度|信心|confidence)[：:\s]*(\d+)(?:%|％)?", text, re.IGNORECASE)
        if conf_match:
            val = int(conf_match.group(1))
            confidence = val / 100.0 if val > 1 else val

        # 提取 risk_score
        risk_score = 0.5
        risk_match = re.search(r"(?:风险评分|风险等级|risk.?score)[：:\s]*(\d+)(?:%|％)?", text, re.IGNORECASE)
        if risk_match:
            val = int(risk_match.group(1))
            risk_score = val / 100.0 if val > 1 else val

        # 提取 reasoning
        reasoning = ""
        reason_match = re.search(r"(?:决策理由|理由|reasoning)[：:\s]*(.+?)(?:\n|$)", text, re.DOTALL)
        if reason_match:
            reasoning = reason_match.group(1).strip()[:200]

        if action != DEFAULT_ACTION or target_price > 0:
            return {
                "action": action,
                "target_price": target_price,
                "confidence": round(confidence, 2),
                "risk_score": round(risk_score, 2),
                "reasoning": reasoning or f"基于正则提取：{action}",
            }

        return None

    def _try_smart_estimate(self, text: str) -> Optional[dict]:
        """智能推算：根据文本情感倾向推算决策"""
        # 统计关键词频率
        bull_words = ["上涨", "看多", "利好", "增长", "突破", "反弹", "低估", "买入"]
        bear_words = ["下跌", "看空", "利空", "下滑", "破位", "高估", "风险", "卖出"]

        bull_count = sum(1 for w in bull_words if w in text)
        bear_count = sum(1 for w in bear_words if w in text)

        if bull_count == 0 and bear_count == 0:
            return None

        if bull_count > bear_count:
            action = "买入"
            confidence = min(0.6, 0.3 + bull_count * 0.05)
            risk_score = max(0.3, 0.7 - bull_count * 0.05)
        elif bear_count > bull_count:
            action = "卖出"
            confidence = min(0.6, 0.3 + bear_count * 0.05)
            risk_score = min(0.8, 0.5 + bear_count * 0.05)
        else:
            action = "持有"
            confidence = 0.4
            risk_score = 0.5

        return {
            "action": action,
            "target_price": 0.0,
            "confidence": round(confidence, 2),
            "risk_score": round(risk_score, 2),
            "reasoning": f"基于文本情感推算：看多词{bull_count}个，看空词{bear_count}个",
        }

    @staticmethod
    def _normalize_decision(data: dict) -> dict:
        """标准化提取的决策数据"""
        action_raw = str(data.get("action", "")).strip()
        action = ACTION_ALIASES.get(action_raw, ACTION_ALIASES.get(action_raw.lower(), DEFAULT_ACTION))

        target_price = 0.0
        try:
            target_price = float(data.get("target_price", 0))
        except (ValueError, TypeError):
            pass

        confidence = 0.5
        try:
            conf = float(data.get("confidence", 50))
            confidence = conf / 100.0 if conf > 1 else conf
        except (ValueError, TypeError):
            pass

        risk_score = 0.5
        try:
            risk = float(data.get("risk_score", 50))
            risk_score = risk / 100.0 if risk > 1 else risk
        except (ValueError, TypeError):
            pass

        reasoning = str(data.get("reasoning", ""))[:200]

        return {
            "action": action,
            "target_price": round(target_price, 2),
            "confidence": round(confidence, 2),
            "risk_score": round(risk_score, 2),
            "reasoning": reasoning,
        }
