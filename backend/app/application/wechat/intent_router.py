"""意图路由器（specs/010，research D2）：规则白名单 → LLM Function Calling → 降级链。

三层顺序（spec FR-005/006/008）：

1. **规则层**：注册表 ``patterns`` 精确匹配（含简单参数捕获），零成本零延迟，
   不依赖任何智能服务——"缠论状态/执行记录"等保底查询永远走这层；
2. **LLM 层**：``AIService.tool_call``（含 chat 兜底意图）；超时/异常自动降级；
3. **降级层**：LLM 不可用时若规则层也未命中，回帮助文案并告知当前仅支持精确指令。

Prompt 单一定义点（rules/backend.md §四：模板化管理、禁止散落）。
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Optional

from app.application.wechat.tools import registry  # 包级 import：触发工具注册（contracts §3）
from app.core.config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Prompt 模板（单一定义点）
# ---------------------------------------------------------------------------

ROUTER_SYSTEM_PROMPT = (
    "你是投研系统的微信指令路由器。根据用户消息选择要执行的工具（tool call），"
    "或选择 chat 表示闲聊/无关内容。\n"
    "规则：\n"
    "1. 只在用户明确表达要执行对应功能时才选具体工具，宁可 chat 不要误判；\n"
    "2. 股票代码为 6 位数字；用户提到股票名而未给代码时，若无代码参数则留空让系统回问；\n"
    "3. 结合对话历史理解指代（如「它」「这只股票」指上文提到的代码）；\n"
    "4. 当前系统时间：{now}（A股交易日 {trading_day}）。"
)


@dataclass
class IntentResult:
    """路由结果：tool 命中（tool_name+params）或回复文案（chat/help/降级）。"""

    tool_name: Optional[str] = None
    params: Optional[dict] = None
    reply_text: Optional[str] = None   # tool 未命中时的回复文案
    via: str = ""                      # pattern | llm | fallback


def build_help_text(include_degraded_note: bool = False) -> str:
    """帮助文案：从注册表动态生成（契约 §2 HELP）。"""
    lines = ["我可以执行这些指令："]
    for tool in registry.all():
        brief = tool.description.split("。")[0]
        sample = tool.usage or "自然语言描述"
        lines.append(f"· {sample} —— {brief}")
    lines.append("也可以用自然语言跟我说，比如「帮我把自选股的缠论都跑一遍」。")
    if include_degraded_note:
        lines.append("（提示：智能识别服务暂不可用，当前仅支持上述精确指令）")
    return "\n".join(lines)


def _fold_history(history: list[dict]) -> list[dict]:
    """会话上下文折叠为 LLM messages（user/assistant 交替，最多 5 轮）。"""
    messages = []
    for turn in history[-5:]:
        role = "user" if turn.get("role") == "user" else "assistant"
        text = (turn.get("text") or "").strip()
        if not text:
            continue
        tc = turn.get("tool_call")
        if role == "user" and tc:
            text = f"{text}（已执行：{tc.get('name')}）"
        messages.append({"role": role, "content": text})
    return messages


async def _resolve_by_llm(text: str, history: list[dict]) -> IntentResult:
    """LLM Function Calling 路由；异常/超时由调用方降级。"""
    from datetime import datetime

    from app.infrastructure.ai.ai_service import AIService

    weekday = datetime.now().weekday()
    trading_day = "是" if weekday < 5 else "否（周末，行情数据为上一交易日）"
    messages = [
        {"role": "system", "content": ROUTER_SYSTEM_PROMPT.format(
            now=datetime.now().strftime("%Y-%m-%d %H:%M"), trading_day=trading_day
        )},
        *_fold_history(history),
        {"role": "user", "content": text},
    ]
    message = await asyncio.wait_for(
        AIService().tool_call(
            messages=messages,
            tools=registry.export_llm_tools(),
            tool_choice="auto",
        ),
        timeout=max(1, settings.wechat_cmd_llm_timeout),
    )

    tool_calls = message.get("tool_calls") or []
    if not tool_calls:
        return IntentResult(reply_text=build_help_text(), via="fallback")
    func = tool_calls[0].get("function", {})
    name = func.get("name", "")
    if name == "chat":
        return IntentResult(tool_name="chat", reply_text=build_help_text(), via="llm")

    tool = registry.get(name)
    if tool is None:
        # LLM 幻觉出未注册的工具名 → 回帮助（契约护栏，research D2）
        logger.warning("微信指令路由：LLM 返回未注册工具 %s", name)
        return IntentResult(reply_text=build_help_text(), via="fallback")

    raw_args = func.get("arguments") or "{}"
    try:
        params = json.loads(raw_args) if isinstance(raw_args, str) else dict(raw_args)
    except (json.JSONDecodeError, TypeError):
        params = {}
    params = {k: v for k, v in params.items() if v not in (None, "", [])}
    return IntentResult(tool_name=name, params=params, via="llm")


async def resolve_intent(text: str, history: list[dict] | None = None) -> IntentResult:
    """路由入口：规则 → LLM → 降级。永不抛异常（网关依赖此约定）。"""
    history = history or []

    # 1) 规则层（保底，不依赖 LLM）
    matched = registry.match_pattern(text)
    if matched:
        tool, params = matched
        return IntentResult(tool_name=tool.name, params=params, via="pattern")

    # 2) LLM 层
    try:
        return await _resolve_by_llm(text, history)
    except Exception as e:  # noqa: BLE001 - LLM 不可用降级（FR-008）
        logger.warning("微信指令路由 LLM 不可用，降级规则模式: %s", e)
        return IntentResult(
            reply_text=build_help_text(include_degraded_note=True), via="fallback"
        )
