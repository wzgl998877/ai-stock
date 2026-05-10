"""agent_classify 节点 — 使用 LLM 自主判断是否需要搜索互联网信息"""

import json
import logging
import re
from datetime import datetime

from app.infrastructure.workflow.state.analysis_state import AnalysisState

logger = logging.getLogger(__name__)

# URL / 文件判断（复用 classify_node 的逻辑）
URL_PATTERN = re.compile(r"^https?://\S+$", re.IGNORECASE)
FILE_EXTENSIONS = {".pdf", ".doc", ".docx", ".txt", ".csv", ".xlsx"}
TYPE_LABELS = {"url": "网页链接", "file": "文件", "text": "文本"}

# LLM function calling 的 web_search tool 定义
WEB_SEARCH_TOOL = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": f"搜索互联网获取最新新闻、数据、事件信息。当用户的问题涉及最新时事、当前市场动态、或需要最新数据时应使用。搜索关键词应包含当前年份（{datetime.now().year}年）。",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索关键词，中文，建议包含当前年份以获取最新信息",
                }
            },
            "required": ["query"],
        },
    },
}

SYSTEM_PROMPT = """你是一个投研分析助手。判断用户的输入是否需要搜索互联网获取最新信息。

需要搜索的情况：
- 涉及最新时事新闻（如：某国最新政策、战争冲突进展）
- 需要最新市场数据或统计
- 具体公司、人物最新动态
- 提到"最新"、"近期"、"目前"、"现在"等时效词

不需要搜索的情况：
- 通用概念分析（如：新能源汽车产业链分析）
- 历史事件分析
- 理论性问题
- 已经有足够上下文的问题

如果需要搜索，调用 web_search 工具，搜索关键词应包含当前年份（{year}年）以确保获取最新信息；否则直接回复"不需要搜索"。""".format(year=datetime.now().year)


def create_agent_classify_node(ai_service):
    """
    闭包注入 AIService，创建 agent_classify 节点。

    Args:
        ai_service: AIService 实例（需要 tool_call 方法）
    """

    async def agent_classify_node(state: AnalysisState) -> dict:
        source = state.get("source", "").strip()

        # 1. 先用规则判断输入类型
        if URL_PATTERN.match(source):
            input_type = "url"
        elif any(source.lower().endswith(ext) for ext in FILE_EXTENSIONS):
            input_type = "file"
        else:
            input_type = "text"

        result = {
            "input_type": input_type,
            "need_search": False,
        }

        # 2. URL 和文件不需要搜索（已经有内容来源）
        if input_type != "text":
            result["thinking_done_msg"] = f"判断输入类型: {TYPE_LABELS.get(input_type, input_type)}"
            logger.info("[agent_classify] input_type=%s, 不需要搜索", input_type)
            return result

        # 3. 文本输入：用 LLM 判断是否需要搜索
        try:
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": source},
            ]

            message = await ai_service.tool_call(
                messages,
                tools=[WEB_SEARCH_TOOL],
                tool_choice="auto",
            )

            # 检查是否有 tool_calls
            tool_calls = message.get("tool_calls", [])
            if tool_calls:
                for tc in tool_calls:
                    fn = tc.get("function", {})
                    if fn.get("name") == "web_search":
                        try:
                            args = json.loads(fn.get("arguments", "{}"))
                            search_query = args.get("query", source[:50])
                        except json.JSONDecodeError:
                            search_query = source[:50]

                        # 加入当前年份，提升搜索结果的时效性
                        current_year = datetime.now().year
                        if str(current_year - 1) not in search_query and str(current_year) not in search_query:
                            search_query = f"{search_query} {current_year}"

                        result["need_search"] = True
                        result["search_query"] = search_query
                        result["thinking_done_msg"] = f"判断输入类型: 文本，需要搜索: {search_query[:30]}"
                        logger.info("[agent_classify] 需要搜索: query=%s", search_query)
                        return result

            # 没有调用工具 → 不需要搜索
            result["thinking_done_msg"] = "判断输入类型: 文本，无需搜索"
            logger.info("[agent_classify] 不需要搜索")

        except Exception as e:
            logger.warning("[agent_classify] LLM 判断失败，降级为不搜索: %s", e)
            result["thinking_done_msg"] = "判断输入类型: 文本"

        return result

    return agent_classify_node
