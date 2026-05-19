"""retrieve 节点 — 搜索知识库中相关历史分析（向量语义检索 + FULLTEXT 回退）"""

import logging

from app.infrastructure.workflow.state.analysis_state import AnalysisState

logger = logging.getLogger(__name__)

# 知识库文章正文最大截取长度（供 summarize_context 节点阅读）
MAX_CONTENT_EXCERPT = 3000


def create_retrieve_node(session_factory, vector_search_repo=None, embedding_service=None):
    """
    闭包注入 session_factory，避免节点直接访问 DB。

    Args:
        session_factory: 异步上下文管理器，yield AsyncSession
        vector_search_repo: 向量检索仓储（可选，启用 RAG 时传入）
        embedding_service: Embedding 服务（可选，启用 RAG 时传入）
    """

    async def retrieve_node(state: AnalysisState) -> dict:
        raw_text = state.get("raw_text", "")

        if not raw_text or len(raw_text) < 5:
            logger.info("[retrieve] 输入文本过短，跳过检索")
            return {"search_results": [], "thinking_done_msg": "输入过短，跳过知识库检索"}

        user_id = state.get("user_id", "default")

        # 1. 尝试向量语义检索
        if vector_search_repo and embedding_service and embedding_service.is_ready():
            try:
                query_text = raw_text[:80].strip()
                query_embedding = await embedding_service.embed(query_text)
                from app.core.config import settings

                vector_results = await vector_search_repo.search(
                    query_embedding=query_embedding,
                    top_k=3,
                    filters={"user_id": user_id},
                    threshold=settings.rag_similarity_threshold,
                    collection="knowledge_articles",
                )

                if vector_results:
                    results = []
                    for r in vector_results:
                        results.append({
                            "title": r.metadata.get("title", ""),
                            "summary": r.document,
                            "content": r.document,
                            "event_type": r.metadata.get("event_type", ""),
                            "created_at": "",
                            "score": r.score,
                        })
                    logger.info("[retrieve] 向量检索到 %d 篇相关文章", len(results))
                    count = len(results)
                    done_msg = f"知识库语义检索完成，找到 {count} 篇相关文章" if count > 0 else "知识库语义检索完成，未找到相关文章"
                    return {"search_results": results, "thinking_done_msg": done_msg}

                logger.info("[retrieve] 向量检索无结果，回退到 FULLTEXT")
            except Exception as e:
                logger.warning("[retrieve] 向量检索异常，回退到 FULLTEXT: %s", e)

        # 2. 回退到 FULLTEXT 检索（原有逻辑）
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
                    user_id=user_id,
                    page=1,
                    page_size=3,
                )

                results = []
                for article in articles[:3]:
                    content_text = article.content or ""
                    if len(content_text) > MAX_CONTENT_EXCERPT:
                        content_text = content_text[:MAX_CONTENT_EXCERPT]
                    results.append({
                        "title": article.title,
                        "summary": article.summary,
                        "content": content_text,
                        "event_type": article.event_type,
                        "created_at": article.create_time.isoformat() if article.create_time else "",
                    })

                logger.info("[retrieve] FULLTEXT 检索到 %d 篇相关文章（总共 %d 篇）", len(results), total)
                count = len(results)
                done_msg = f"知识库检索完成，找到 {count} 篇相关文章" if count > 0 else "知识库检索完成，未找到相关文章"
                return {"search_results": results, "thinking_done_msg": done_msg}

        except Exception as e:
            logger.error("[retrieve] 知识库检索失败: %s", e, exc_info=True)
            return {"search_results": [], "thinking_done_msg": "知识库检索失败，已跳过"}

    return retrieve_node
