"""事件去重服务 — URL MD5 精确去重 + Jaccard 标题去重 + 语义 embedding 去重"""

import hashlib
import logging

logger = logging.getLogger(__name__)


def url_hash(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()


def jaccard_similarity(a: str, b: str) -> float:
    """计算两个字符串的 Jaccard 相似度（基于字符集合）"""
    set_a = set(a)
    set_b = set(b)
    if not set_a and not set_b:
        return 1.0
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union)


def is_duplicate_title(title: str, existing_titles: list, threshold: float = 0.6) -> bool:
    """检查标题是否与已有标题重复"""
    for existing in existing_titles:
        if jaccard_similarity(title, existing) >= threshold:
            return True
    return False


def is_duplicate_url(url: str, existing_hashes: set) -> bool:
    """检查 URL 是否已存在"""
    return url_hash(url) in existing_hashes


async def is_semantic_duplicate(
    new_title: str,
    embedding_service,
    vector_search_repo,
    threshold: float = 0.85,
) -> bool:
    """基于语义 embedding 相似度判断事件是否重复。

    生成 new_title 的 embedding，在 impact_events 集合中搜索 top-1 相似向量，
    score >= threshold 时判定为重复事件。

    Args:
        new_title: 待检测的事件标题
        embedding_service: Embedding 服务实例
        vector_search_repo: 向量检索仓储实例
        threshold: 语义相似度阈值，默认 0.85

    Returns:
        True 表示语义重复，False 表示不重复或检测失败
    """
    try:
        embedding = await embedding_service.embed(new_title)
        results = await vector_search_repo.search(
            query_embedding=embedding,
            top_k=1,
            collection="impact_events",
            threshold=threshold,
        )
        if results and results[0].score >= threshold:
            logger.info(
                "语义去重命中: new_title=%r, matched=%r, score=%.4f",
                new_title[:50],
                results[0].metadata.get("title", "")[:50],
                results[0].score,
            )
            return True
        return False
    except Exception as e:
        logger.warning("语义去重检测异常，跳过语义层: %s", e)
        return False
