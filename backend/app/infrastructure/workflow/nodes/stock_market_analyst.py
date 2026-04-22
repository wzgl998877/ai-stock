"""技术面分析师节点 — 通过工具调用获取行情数据，生成技术面分析报告"""

import json
import logging

from app.infrastructure.workflow.prompts.stock_analysis.market_analyst import SYSTEM_PROMPT, USER_TEMPLATE
from app.infrastructure.workflow.tools.stock_data_toolkit import (
    TOOL_FUNCTION_MAP,
    get_stock_tools_schema,
)

logger = logging.getLogger(__name__)


def create_market_analyst_node(ai_service, max_tool_calls: int = 3):
    """
    闭包工厂：创建技术面分析师节点。

    Args:
        ai_service: AIService 实例
        max_tool_calls: 最大工具调用次数（防止死循环），默认3次
    """

    async def market_analyst_node(state: dict) -> dict:
        stock_code = state.get("stock_code", "")
        stock_name = state.get("stock_name", "")

        user_content = USER_TEMPLATE.format(stock_name=stock_name, stock_code=stock_code)
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]

        tools_schema = get_stock_tools_schema()
        tool_call_count = 0

        # 循环调用工具，最多 max_tool_calls 次
        for _ in range(max_tool_calls):
            try:
                response = await ai_service.tool_call(
                    messages=messages,
                    tools=tools_schema,
                    tool_choice="auto",
                    max_tokens=1024,
                )
            except Exception as e:
                logger.error("[market_analyst] tool_call 调用失败: %s", e)
                break

            tool_calls = response.get("tool_calls", [])
            if not tool_calls:
                # 没有工具调用，说明模型直接给出了回答
                break

            # 追加 assistant 消息（含 tool_calls）到 messages
            messages.append(response)

            # 执行每个工具调用
            for tc in tool_calls:
                func_info = tc.get("function", {})
                func_name = func_info.get("name", "")
                func_args_str = func_info.get("arguments", "{}")

                try:
                    func_args = json.loads(func_args_str)
                except json.JSONDecodeError:
                    func_args = {}

                # 执行工具函数
                tool_func = TOOL_FUNCTION_MAP.get(func_name)
                if tool_func:
                    try:
                        tool_result = tool_func(**func_args)
                    except Exception as e:
                        tool_result = f"工具执行失败: {e}"
                        logger.error("[market_analyst] 工具 %s 执行失败: %s", func_name, e)
                else:
                    tool_result = f"未知工具: {func_name}"

                # 追加工具结果到 messages
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.get("id", ""),
                    "content": str(tool_result),
                })
                tool_call_count += 1

        # 最终用 stream_chat 获取完整分析报告
        full_text = ""
        try:
            async for chunk in ai_service.stream_chat(
                system_prompt="",
                user_message="",
                history_messages=messages,
                temperature=0.3,
                max_tokens=4096,
            ):
                if chunk.type == "content":
                    full_text += chunk.text
        except Exception as e:
            logger.error("[market_analyst] stream_chat 失败: %s", e)
            full_text = f"技术面分析生成失败: {e}"

        logger.info(
            "[market_analyst] 完成: stock=%s, tool_calls=%d, report_len=%d",
            stock_code, tool_call_count, len(full_text),
        )

        return {
            "market_report": full_text,
            "market_tool_call_count": tool_call_count,
            "current_agent": "market_analyst",
            "current_phase": "analysts",
        }

    return market_analyst_node
