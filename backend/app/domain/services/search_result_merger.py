"""检索结果合并去重 — 将同一文章的多个 chunk 命中结果合并为一条"""

from app.domain.entities.vector_search import VectorSearchResult


def _extract_article_id(doc_id: str) -> tuple[str, int]:
    """从 doc_id 中提取 article_id 和 chunk_index。

    Args:
        doc_id: 文档 ID，格式为 "article_{id}_chunk_{n}" 或旧格式 "article_{id}"

    Returns:
        (article_id_with_prefix, chunk_index)
        例如 ("article_123", 2) 或 ("article_123", 0)
    """
    if "_chunk_" in doc_id:
        parts = doc_id.rsplit("_chunk_", 1)
        return parts[0], int(parts[1])
    return doc_id, 0


def merge_chunk_results(
    results: list[VectorSearchResult],
    max_articles: int = 3,
    max_content_length: int = 3000,
) -> list[dict]:
    """将多个 chunk 命中结果按 article_id 分组合并。

    Args:
        results: 向量检索返回的原始结果列表。
        max_articles: 最多返回的文章数量。
        max_content_length: 每篇文章拼接 content 的最大字符数。

    Returns:
        合并后的文章列表，每项包含：
        {
            "article_id": str,       # 带 "article_" 前缀
            "title": str,
            "summary": str,
            "content": str,          # 多个 chunk 的 content 拼接
            "score": float,          # 最高分数
            "source": str,           # "vector_search"
        }

    向下兼容：旧格式 doc_id（无 `_chunk_` 后缀，如 `article_123`）
    也能正确处理。
    """
    if not results:
        return []

    # 按 article_id 分组
    groups: dict[str, list[VectorSearchResult]] = {}
    for r in results:
        article_id, _ = _extract_article_id(r.doc_id)
        groups.setdefault(article_id, []).append(r)

    # 每个分组内合并
    merged: list[dict] = []
    for article_id, group_results in groups.items():
        # score 取最高
        best_score = max(r.score for r in group_results)

        # metadata 中的 title
        title = group_results[0].metadata.get("title", "")

        # summary 从 chunk_type="summary" 的块中提取
        summary = ""
        for r in group_results:
            if r.metadata.get("chunk_type") == "summary":
                summary = r.document
                break
        if not summary:
            summary = group_results[0].document

        # content 按 chunk_index 排序后拼接
        sorted_results = sorted(group_results, key=lambda r: _extract_article_id(r.doc_id)[1])
        content_parts = []
        total_len = 0
        for r in sorted_results:
            chunk_type = r.metadata.get("chunk_type", "")
            if chunk_type == "content":
                text = r.document
                if total_len + len(text) > max_content_length:
                    remaining = max_content_length - total_len
                    if remaining > 0:
                        content_parts.append(text[:remaining])
                    break
                content_parts.append(text)
                total_len += len(text)

        content = "\n\n".join(content_parts)

        merged.append({
            "article_id": article_id,
            "title": title,
            "summary": summary,
            "content": content,
            "score": best_score,
            "source": "vector_search",
        })

    # 按 score 降序排列，截取 max_articles 篇
    merged.sort(key=lambda x: x["score"], reverse=True)
    return merged[:max_articles]
