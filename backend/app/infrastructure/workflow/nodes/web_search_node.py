"""web_search 节点 — 调用 Tavily 搜索互联网信息"""

import logging

from app.infrastructure.workflow.state.analysis_state import AnalysisState

logger = logging.getLogger(__name__)


async def web_search_node(state: AnalysisState) -> dict:
    """
    调用 web_search tool 搜索互联网。
    仅在 need_search=True 时执行。
    """
    search_query = state.get("search_query", "")

    if not search_query:
        logger.warning("[web_search] search_query 为空，跳过")
        return {"web_search_results": [], "thinking_done_msg": "搜索已跳过"}

    try:
        from app.infrastructure.workflow.tools.web_search import web_search

        results = await web_search(search_query)
        count = len(results)

        if count > 0:
            done_msg = f"搜索完成，找到 {count} 条结果"
        else:
            done_msg = "搜索完成，未找到相关结果"

        logger.info("[web_search] query=%s, results=%d", search_query[:50], count)
        return {"web_search_results": results, "thinking_done_msg": done_msg}

    except Exception as e:
        logger.error("[web_search] 搜索失败: %s", e, exc_info=True)
        return {
            "web_search_results": [],
            "thinking_done_msg": f"搜索失败，已跳过",
        }
