"""技术面分析师节点 — 通过工具调用获取行情数据，生成技术面分析报告"""

import asyncio
import json
import logging
import time

from app.infrastructure.workflow.prompts.stock_analysis.market_analyst import SYSTEM_PROMPT, USER_TEMPLATE
from app.infrastructure.ai.ai_service import AIService
from app.infrastructure.workflow.tools.stock_data_toolkit import (
    TOOL_FUNCTION_MAP,
    get_stock_tools_schema,
)
from app.infrastructure.workflow.nodes.stock_tool_runner import collect_report_with_tool_continuation

logger = logging.getLogger(__name__)


def create_market_analyst_node(ai_service, max_tool_calls: int = 3):
    """
    闭包工厂：创建技术面分析师节点。

    Args:
        ai_service: AIService 实例
        max_tool_calls: 最大工具调用次数（防止死循环），默认3次
    """

    async def market_analyst_node(state: dict) -> dict:
        t_start = time.time()
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
                t0 = time.time()
                response = await ai_service.tool_call(
                    messages=messages,
                    tools=tools_schema,
                    tool_choice="auto",
                    max_tokens=1024,
                )
                logger.info("[耗时] market_analyst tool_call(第%d轮): %.3fs", tool_call_count + 1, time.time() - t0)
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
                        t0 = time.time()
                        tool_result = await asyncio.to_thread(tool_func, **func_args)
                        logger.info("[耗时] market_analyst 工具[%s]: %.3fs", func_name, time.time() - t0)
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

        t_stream = time.time()
        content_queue = state.get("_content_queue")
        try:
            full_text, extra_tool_calls = await collect_report_with_tool_continuation(
                ai_service=ai_service,
                messages=messages,
                tools_schema=tools_schema,
                agent_name="market_analyst",
                content_queue=content_queue,
                temperature=0.3,
                max_tokens=100000,
            )
            tool_call_count += extra_tool_calls
        except Exception as e:
            logger.error("[market_analyst] 最终报告生成失败: %s", e)
            full_text = f"技术面分析生成失败: {e}"

        logger.info(
            "[耗时] market_analyst final_report: %.3fs", time.time() - t_stream,
        )
        logger.info(
            "[耗时] market_analyst 总耗时: %.3fs, stock=%s, tool_calls=%d, report_len=%d",
            time.time() - t_start, stock_code, tool_call_count, len(full_text),
        )

        return {
            "market_report": full_text,
            "market_tool_call_count": tool_call_count,
            "current_agent": "market_analyst",
            "current_phase": "analysts",
        }

    return market_analyst_node
