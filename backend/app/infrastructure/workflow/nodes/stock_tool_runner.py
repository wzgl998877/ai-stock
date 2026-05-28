"""股票分析师工具调用辅助。"""

import asyncio
import json
import logging
from typing import Any

from app.infrastructure.workflow.tools.stock_data_toolkit import TOOL_FUNCTION_MAP

logger = logging.getLogger(__name__)

FINAL_REPORT_INSTRUCTION = {
    "role": "user",
    "content": "工具数据已足够。请不要再调用任何工具，不要输出 DSML/tool_calls/XML 标签。请仅基于已有工具结果输出完整中文分析报告。",
}


def is_dsml_text(text: str | None) -> bool:
    return bool(text and "<｜｜DSML｜｜" in text)


async def execute_tool_calls(
    messages: list[dict[str, Any]],
    tool_calls: list[dict[str, Any]],
    agent_name: str,
) -> int:
    executed = 0
    for tc in tool_calls:
        func_info = tc.get("function", {})
        func_name = func_info.get("name", "")
        func_args_str = func_info.get("arguments", "{}")

        try:
            func_args = json.loads(func_args_str)
        except json.JSONDecodeError:
            func_args = {}

        tool_func = TOOL_FUNCTION_MAP.get(func_name)
        if tool_func:
            try:
                tool_result = await asyncio.to_thread(tool_func, **func_args)
            except Exception as e:
                tool_result = f"工具执行失败: {e}"
                logger.error("[%s] 工具 %s 执行失败: %s", agent_name, func_name, e)
        else:
            tool_result = f"未知工具: {func_name}"

        messages.append({
            "role": "tool",
            "tool_call_id": tc.get("id", ""),
            "content": str(tool_result),
        })
        executed += 1
    return executed


async def collect_report_with_tool_continuation(
    ai_service,
    messages: list[dict[str, Any]],
    tools_schema: list[dict[str, Any]],
    agent_name: str,
    content_queue=None,
    max_additional_tool_rounds: int = 2,
    temperature: float = 0.3,
    max_tokens: int = 100000,
) -> tuple[str, int]:
    extra_tool_calls = 0

    for round_index in range(max_additional_tool_rounds + 1):
        full_text = ""
        pending_tool_calls: list[dict[str, Any]] = []

        async for chunk in ai_service.stream_chat_with_tools(
            messages=messages,
            tools=tools_schema,
            tool_choice="auto",
            temperature=temperature,
            max_tokens=max_tokens,
        ):
            if chunk.type == "tool_calls":
                pending_tool_calls.extend(chunk.tool_calls or [])
            elif chunk.type == "content":
                full_text += chunk.text

        if pending_tool_calls and round_index < max_additional_tool_rounds:
            messages.append({
                "role": "assistant",
                "content": None,
                "tool_calls": pending_tool_calls,
            })
            extra_tool_calls += await execute_tool_calls(messages, pending_tool_calls, agent_name)
            continue

        if full_text and not is_dsml_text(full_text):
            if content_queue:
                await content_queue.put(full_text)
            return full_text, extra_tool_calls

        if pending_tool_calls and round_index >= max_additional_tool_rounds:
            logger.warning("[%s] 最终报告阶段仍请求工具，已达到额外工具调用上限", agent_name)

        if round_index < max_additional_tool_rounds:
            messages.append(FINAL_REPORT_INSTRUCTION.copy())
            continue

        if full_text:
            return f"{agent_name}分析生成失败: 模型返回了工具调用格式，未生成有效报告", extra_tool_calls
        return f"{agent_name}分析生成失败: 模型未生成有效报告", extra_tool_calls

    return f"{agent_name}分析生成失败: 模型未生成有效报告", extra_tool_calls
