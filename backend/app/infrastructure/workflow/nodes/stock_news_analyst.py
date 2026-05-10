"""新闻分析师节点 — 通过工具调用获取新闻数据，生成新闻分析报告"""

import json
import logging
import time

from app.infrastructure.workflow.prompts.stock_analysis.news_analyst import SYSTEM_PROMPT, USER_TEMPLATE
from app.infrastructure.workflow.tools.stock_data_toolkit import (
    TOOL_FUNCTION_MAP,
    get_stock_tools_schema,
)

logger = logging.getLogger(__name__)

_PRE_SEARCH_CONTEXT_TEMPLATE = """
以下是已获取到的新闻数据（来自互联网搜索），供你分析参考：
---
{news_context}
---
请结合以上新闻数据进行分析。如果还需要更多信息，可以调用 get_stock_news 工具获取额外数据。
"""


def create_news_analyst_node(ai_service, max_tool_calls: int = 3, search_service=None):
    """
    闭包工厂：创建新闻分析师节点。

    Args:
        ai_service: AIService 实例
        max_tool_calls: 最大工具调用次数（防止死循环），默认3次
        search_service: 统一搜索服务实例（可选），可用时预搜新闻注入上下文
    """

    async def news_analyst_node(state: dict) -> dict:
        t_start = time.time()
        stock_code = state.get("stock_code", "")
        stock_name = state.get("stock_name", "")

        user_content = USER_TEMPLATE.format(stock_name=stock_name, stock_code=stock_code)

        # 预搜新闻（search_service 可用时）
        pre_search_context = ""
        if search_service and search_service.is_available:
            try:
                t0 = time.time()
                response = await search_service.search_stock_news(
                    stock_code=stock_code,
                    stock_name=stock_name,
                    max_results=8,
                )
                logger.info("[耗时] news_analyst 预搜新闻: %.3fs, provider=%s, results=%d",
                            time.time() - t0, response.provider, len(response.results))
                if response.success and response.results:
                    pre_search_context = _PRE_SEARCH_CONTEXT_TEMPLATE.format(
                        news_context=response.to_context(max_results=8)
                    )
            except Exception as e:
                logger.warning("[news_analyst] 预搜新闻失败，将依赖工具调用: %s", e)

        if pre_search_context:
            user_content = user_content + "\n" + pre_search_context

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
                logger.info("[耗时] news_analyst tool_call(第%d轮): %.3fs", tool_call_count + 1, time.time() - t0)
            except Exception as e:
                logger.error("[news_analyst] tool_call 调用失败: %s", e)
                break

            tool_calls = response.get("tool_calls", [])
            if not tool_calls:
                break

            # 追加 assistant 消息
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

                tool_func = TOOL_FUNCTION_MAP.get(func_name)
                if tool_func:
                    try:
                        t0 = time.time()
                        tool_result = tool_func(**func_args)
                        logger.info("[耗时] news_analyst 工具[%s]: %.3fs", func_name, time.time() - t0)
                    except Exception as e:
                        tool_result = f"工具执行失败: {e}"
                        logger.error("[news_analyst] 工具 %s 执行失败: %s", func_name, e)
                else:
                    tool_result = f"未知工具: {func_name}"

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.get("id", ""),
                    "content": str(tool_result),
                })
                tool_call_count += 1

        # 最终获取完整分析报告
        t_stream = time.time()
        full_text = ""
        content_queue = state.get("_content_queue")
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
                    if content_queue:
                        await content_queue.put(chunk.text)
        except Exception as e:
            logger.error("[news_analyst] stream_chat 失败: %s", e)
            full_text = f"新闻分析生成失败: {e}"

        logger.info(
            "[耗时] news_analyst stream_chat: %.3fs", time.time() - t_stream,
        )
        logger.info(
            "[耗时] news_analyst 总耗时: %.3fs, stock=%s, tool_calls=%d, report_len=%d",
            time.time() - t_start, stock_code, tool_call_count, len(full_text),
        )

        return {
            "news_report": full_text,
            "news_tool_call_count": tool_call_count,
            "current_agent": "news_analyst",
            "current_phase": "analysts",
        }

    return news_analyst_node
