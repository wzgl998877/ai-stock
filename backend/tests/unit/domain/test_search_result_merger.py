"""search_result_merger 单元测试"""

from app.domain.entities.vector_search import VectorSearchResult
from app.domain.services.search_result_merger import merge_chunk_results


def _make_result(
    doc_id: str,
    score: float,
    title: str = "测试文章",
    chunk_type: str = "content",
    document: str = "文档内容",
) -> VectorSearchResult:
    return VectorSearchResult(
        doc_id=doc_id,
        score=score,
        metadata={"title": title, "chunk_type": chunk_type, "chunk_index": 0},
        document=document,
    )


class TestMergeChunkResults:

    def test_empty_results(self):
        """空列表返回空"""
        assert merge_chunk_results([]) == []

    def test_single_article_single_chunk(self):
        """单条结果原样返回"""
        r = _make_result("article_1_chunk_0", 0.85, title="文章A", chunk_type="summary", document="摘要")
        result = merge_chunk_results([r])
        assert len(result) == 1
        assert result[0]["article_id"] == "article_1"
        assert result[0]["score"] == 0.85
        assert result[0]["title"] == "文章A"

    def test_same_article_multiple_chunks(self):
        """同一文章多个 chunk 合并"""
        results = [
            _make_result("article_1_chunk_0", 0.9, chunk_type="summary", document="标题\n摘要"),
            _make_result("article_1_chunk_1", 0.85, chunk_type="content", document="## 章节1\n内容1"),
            _make_result("article_1_chunk_2", 0.75, chunk_type="content", document="## 章节2\n内容2"),
        ]
        merged = merge_chunk_results(results)
        assert len(merged) == 1
        assert merged[0]["article_id"] == "article_1"
        assert merged[0]["score"] == 0.9  # 最高分
        assert "内容1" in merged[0]["content"]
        assert "内容2" in merged[0]["content"]
        assert merged[0]["summary"] == "标题\n摘要"

    def test_different_articles_sorted_by_score(self):
        """多篇文章按 score 降序"""
        results = [
            _make_result("article_1_chunk_0", 0.7, title="文章A"),
            _make_result("article_2_chunk_0", 0.9, title="文章B"),
            _make_result("article_3_chunk_0", 0.8, title="文章C"),
        ]
        merged = merge_chunk_results(results)
        assert len(merged) == 3
        assert merged[0]["article_id"] == "article_2"  # 0.9
        assert merged[1]["article_id"] == "article_3"  # 0.8
        assert merged[2]["article_id"] == "article_1"  # 0.7

    def test_max_articles_limit(self):
        """超过 max_articles 时截断"""
        results = [
            _make_result("article_1_chunk_0", 0.9),
            _make_result("article_2_chunk_0", 0.8),
            _make_result("article_3_chunk_0", 0.7),
            _make_result("article_4_chunk_0", 0.6),
        ]
        merged = merge_chunk_results(results, max_articles=2)
        assert len(merged) == 2

    def test_content_truncation(self):
        """content 超长时截断"""
        long_text = "很长的内容" * 500  # ~2500 字
        results = [
            _make_result("article_1_chunk_1", 0.9, chunk_type="content", document=long_text),
        ]
        merged = merge_chunk_results(results, max_content_length=500)
        assert len(merged[0]["content"]) <= 500

    def test_legacy_doc_id_compat(self):
        """旧格式 doc_id（无 _chunk_）正确处理"""
        r = _make_result("article_123", 0.85, title="旧文章")
        merged = merge_chunk_results([r])
        assert len(merged) == 1
        assert merged[0]["article_id"] == "article_123"

    def test_summary_extraction(self):
        """summary 从 chunk_type='summary' 的块中提取"""
        results = [
            _make_result("article_1_chunk_0", 0.9, chunk_type="summary", document="标题\n这是摘要"),
            _make_result("article_1_chunk_1", 0.8, chunk_type="content", document="## 正文\n内容"),
        ]
        merged = merge_chunk_results(results)
        assert merged[0]["summary"] == "标题\n这是摘要"
        assert "内容" in merged[0]["content"]
