"""retrieve 节点 — 搜索知识库中相关历史分析"""

import logging

from app.infrastructure.workflow.state.analysis_state import AnalysisState

logger = logging.getLogger(__name__)


def create_retrieve_node(session_factory):
    """
    闭包注入 session_factory，避免节点直接访问 DB。

    Args:
        session_factory: 异步上下文管理器，yield AsyncSession
    """

    async def retrieve_node(state: AnalysisState) -> dict:
        raw_text = state.get("raw_text", "")

        if not raw_text or len(raw_text) < 5:
            logger.info("[retrieve] 输入文本过短，跳过检索")
            return {"search_results": [], "thinking_done_msg": "输入过短，跳过知识库检索"}

        try:
            async with session_factory() as session:
                from app.infrastructure.repositories.mysql_search_repo import MySQLSearchRepository
                search_repo = MySQLSearchRepository(session)

                # 查询词加上当前年份，提升时效性
                from datetime import datetime
                current_year = datetime.now().year
                query = f"{raw_text[:80].strip()} {current_year}"

                articles, total = await search_repo.search(
                    query=query,
                    user_id=state.get("user_id", "default"),
                    page=1,
                    page_size=3,
                )

                results = []
                for article in articles[:3]:
                    results.append({
                        "title": article.title,
                        "summary": article.summary,
                        "event_type": article.event_type,
                        "created_at": article.create_time.isoformat() if article.create_time else "",
                    })

                logger.info("[retrieve] 检索到 %d 篇相关文章（总共 %d 篇）", len(results), total)
                count = len(results)
                done_msg = f"知识库检索完成，找到 {count} 篇相关文章" if count > 0 else "知识库检索完成，未找到相关文章"
                return {"search_results": results, "thinking_done_msg": done_msg}

        except Exception as e:
            logger.error("[retrieve] 知识库检索失败: %s", e, exc_info=True)
            return {"search_results": [], "thinking_done_msg": "知识库检索失败，已跳过"}

    return retrieve_node
