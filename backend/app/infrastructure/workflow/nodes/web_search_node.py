"""web_search 节点 — 调用统一搜索服务或 Tavily 搜索互联网信息"""

import logging

from app.infrastructure.workflow.state.analysis_state import AnalysisState

logger = logging.getLogger(__name__)


def create_web_search_node(search_service=None):
    """
    创建 web_search 节点。

    Args:
        search_service: 统一搜索服务实例（可选），可用时优先使用。
                        为 None 时回退到旧版 Tavily 搜索。
    """

    async def web_search_node(state: AnalysisState) -> dict:
        search_query = state.get("search_query", "")

        if not search_query:
            logger.warning("[web_search] search_query 为空，跳过")
            return {"web_search_results": [], "thinking_done_msg": "搜索已跳过"}

        # 优先使用统一搜索服务
        if search_service and search_service.is_available:
            try:
                response = await search_service.search(
                    query=search_query,
                    max_results=5,
                    days=7,
                )
                if response.success and response.results:
                    results = _search_response_to_dict_list(response)
                    count = len(results)
                    done_msg = f"搜索完成，找到 {count} 条结果"
                    logger.info("[web_search] 统一搜索: query=%s, results=%d, provider=%s",
                                search_query[:50], count, response.provider)
                    return {"web_search_results": results, "thinking_done_msg": done_msg}
                else:
                    logger.warning("[web_search] 统一搜索无结果，回退旧版: %s",
                                   response.error_message or "空结果")
            except Exception as e:
                logger.warning("[web_search] 统一搜索异常，回退旧版: %s", e)

        # 回退旧版 Tavily 搜索
        try:
            from app.infrastructure.workflow.tools.web_search import web_search

            results = await web_search(search_query)
            count = len(results)

            if count > 0:
                done_msg = f"搜索完成，找到 {count} 条结果"
            else:
                done_msg = "搜索完成，未找到相关结果"

            logger.info("[web_search] 旧版搜索: query=%s, results=%d", search_query[:50], count)
            return {"web_search_results": results, "thinking_done_msg": done_msg}

        except Exception as e:
            logger.error("[web_search] 搜索失败: %s", e, exc_info=True)
            return {
                "web_search_results": [],
                "thinking_done_msg": "搜索失败，已跳过",
            }

    return web_search_node


def _search_response_to_dict_list(response) -> list[dict]:
    """将 SearchResponse 转换为下游 summarize_context_node 兼容的 dict 列表。

    下游期望格式: {title, content, url}
    """
    results = []
    for r in response.results:
        results.append({
            "title": r.title,
            "content": r.snippet,
            "url": r.url,
        })
    return results
