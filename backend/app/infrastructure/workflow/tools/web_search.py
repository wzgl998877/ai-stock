"""web_search tool — 封装 Tavily Search API，供 Agent 节点调用"""

import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

MAX_RESULTS = 5
MAX_CONTENT_LENGTH = 3000


async def web_search(query: str, max_results: int = MAX_RESULTS) -> list[dict]:
    """
    调用 Tavily Search API 搜索互联网信息。

    Returns:
        list[dict]: 搜索结果列表，每项包含 title, url, content
    """
    if not settings.tavily_api_key:
        logger.warning("[web_search] TAVILY_API_KEY 未配置，跳过搜索")
        return []

    try:
        from tavily import TavilyClient

        client = TavilyClient(api_key=settings.tavily_api_key)
        response = client.search(
            query,
            max_results=max_results,
            search_depth="basic",
            topic="news",
            time_range="month",
        )

        results = []
        for item in response.get("results", []):
            content = item.get("content", "")
            if len(content) > MAX_CONTENT_LENGTH:
                content = content[:MAX_CONTENT_LENGTH] + "...(已截断)"
            results.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "content": content,
            })

        logger.info("[web_search] 搜索完成: query=%s, results=%d", query[:50], len(results))
        return results

    except ImportError:
        logger.warning("[web_search] tavily-python 未安装，跳过搜索")
        return []
    except Exception as e:
        logger.error("[web_search] 搜索失败: %s", e, exc_info=True)
        return []
