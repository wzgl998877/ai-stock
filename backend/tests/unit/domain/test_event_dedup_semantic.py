"""事件语义去重单元测试 — T026 [US3]

测试三层去重引擎：
1. URL MD5 精确去重（最高优先级）
2. Jaccard 标题相似度去重
3. 语义 embedding 相似度去重（第三层兜底）
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domain.entities.vector_search import VectorSearchResult
from app.domain.services.event_dedup import (
    is_semantic_duplicate,
    url_hash,
)
from app.domain.services.impact_assessment import assess_event

# match_all 的默认 mock 返回值：匹配到一只股票，确保 assess_event 不因股票匹配失败而返回 None
_MOCK_MATCH_RESULT = {
    "stocks": [{"code": "601398", "name": "工商银行", "match_type": "regex"}],
    "industries": [],
}

_MOCK_SENTIMENT_RESULT = {
    "sentiment": "neutral",
    "confidence": 0.5,
    "importance": "low",
}


# ---------------------------------------------------------------------------
# Helpers: 构造 mock embedding_service 和 vector_search_repo
# ---------------------------------------------------------------------------

def _make_embedding_service(ready: bool = True):
    """构造 mock EmbeddingService"""
    svc = MagicMock()
    svc.is_ready.return_value = ready
    svc.embed = AsyncMock(return_value=[0.1] * 1024)
    return svc


def _make_vector_search_repo(results: list[VectorSearchResult] | None = None):
    """构造 mock VectorSearchRepository"""
    repo = MagicMock()
    repo.search = AsyncMock(return_value=results or [])
    return repo


def _make_vector_result(doc_id: str, score: float, title: str = "") -> VectorSearchResult:
    """快速构造一个 VectorSearchResult"""
    return VectorSearchResult(
        doc_id=doc_id,
        score=score,
        metadata={"title": title},
        document=title,
    )


# ===========================================================================
# is_semantic_duplicate 测试
# ===========================================================================


@pytest.mark.asyncio
async def test_semantic_duplicate_same_meaning_high_score():
    """同义标题 embedding 相似度 >= 0.85 → 判定为重复"""
    embedding_service = _make_embedding_service(ready=True)
    result = _make_vector_result("event_1", 0.92, "人民银行下调基准利率0.25%")
    vector_search_repo = _make_vector_search_repo([result])

    is_dup = await is_semantic_duplicate(
        new_title="央行降息25个基点",
        embedding_service=embedding_service,
        vector_search_repo=vector_search_repo,
        threshold=0.85,
    )

    assert is_dup is True
    embedding_service.embed.assert_awaited_once_with("央行降息25个基点")
    vector_search_repo.search.assert_awaited_once()


@pytest.mark.asyncio
async def test_semantic_duplicate_different_events_low_score():
    """不同事件 embedding 相似度 < 0.85 → 不合并"""
    embedding_service = _make_embedding_service(ready=True)
    result = _make_vector_result("event_2", 0.45, "新能源汽车销量创新高")
    vector_search_repo = _make_vector_search_repo([result])

    is_dup = await is_semantic_duplicate(
        new_title="央行降息25个基点",
        embedding_service=embedding_service,
        vector_search_repo=vector_search_repo,
        threshold=0.85,
    )

    assert is_dup is False


@pytest.mark.asyncio
async def test_semantic_duplicate_no_results():
    """impact_events 集合无数据 → 不判定为重复"""
    embedding_service = _make_embedding_service(ready=True)
    vector_search_repo = _make_vector_search_repo([])

    is_dup = await is_semantic_duplicate(
        new_title="央行降息25个基点",
        embedding_service=embedding_service,
        vector_search_repo=vector_search_repo,
        threshold=0.85,
    )

    assert is_dup is False


@pytest.mark.asyncio
async def test_semantic_duplicate_exact_threshold():
    """相似度刚好等于阈值 → 判定为重复"""
    embedding_service = _make_embedding_service(ready=True)
    result = _make_vector_result("event_3", 0.85, "央行降息25个基点")
    vector_search_repo = _make_vector_search_repo([result])

    is_dup = await is_semantic_duplicate(
        new_title="央行降息25个基点",
        embedding_service=embedding_service,
        vector_search_repo=vector_search_repo,
        threshold=0.85,
    )

    assert is_dup is True


@pytest.mark.asyncio
async def test_semantic_duplicate_embedding_failure_returns_false():
    """embedding 服务抛异常 → 跳过语义层，返回 False"""
    embedding_service = _make_embedding_service(ready=True)
    embedding_service.embed = AsyncMock(side_effect=RuntimeError("模型加载失败"))
    vector_search_repo = _make_vector_search_repo()

    is_dup = await is_semantic_duplicate(
        new_title="央行降息25个基点",
        embedding_service=embedding_service,
        vector_search_repo=vector_search_repo,
        threshold=0.85,
    )

    assert is_dup is False


@pytest.mark.asyncio
async def test_semantic_duplicate_search_failure_returns_false():
    """向量检索抛异常 → 跳过语义层，返回 False"""
    embedding_service = _make_embedding_service(ready=True)
    vector_search_repo = _make_vector_search_repo()
    vector_search_repo.search = AsyncMock(side_effect=ConnectionError("ChromaDB 不可用"))

    is_dup = await is_semantic_duplicate(
        new_title="央行降息25个基点",
        embedding_service=embedding_service,
        vector_search_repo=vector_search_repo,
        threshold=0.85,
    )

    assert is_dup is False


# ===========================================================================
# assess_event 三层去重集成测试
# ===========================================================================


@pytest.mark.asyncio
async def test_assess_event_url_hash_takes_priority():
    """URL hash 去重优先于语义去重 — URL 重复时直接返回 None，不调用 embedding"""
    embedding_service = _make_embedding_service(ready=True)
    result = _make_vector_result("event_1", 0.99, "央行降息25个基点")
    vector_search_repo = _make_vector_search_repo([result])

    url = "https://example.com/news/rate-cut"
    url_hashes = {url_hash(url)}

    ret = await assess_event(
        title="央行降息25个基点",
        content="人民银行宣布下调基准利率",
        source_url=url,
        existing_url_hashes=url_hashes,
        existing_titles=[],
        embedding_service=embedding_service,
        vector_search_repo=vector_search_repo,
    )

    assert ret is None
    # URL 层已拦截，不应调用语义层
    embedding_service.embed.assert_not_awaited()


@pytest.mark.asyncio
async def test_assess_event_jaccard_match_skips_semantic():
    """Jaccard 匹配命中后跳过语义计算 — 不调用 embedding"""
    embedding_service = _make_embedding_service(ready=True)
    result = _make_vector_result("event_1", 0.99, "国际油价突破85美元/桶创三年新高")
    vector_search_repo = _make_vector_search_repo([result])

    ret = await assess_event(
        title="国际油价突破90美元/桶创三年新高",
        content="布伦特原油价格突破90美元",
        source_url="https://example.com/different-url",
        existing_url_hashes=set(),
        existing_titles=["国际油价突破85美元/桶创三年新高"],
        embedding_service=embedding_service,
        vector_search_repo=vector_search_repo,
    )

    assert ret is None
    # Jaccard 层已拦截，不应调用语义层
    embedding_service.embed.assert_not_awaited()


@pytest.mark.asyncio
async def test_assess_event_semantic_duplicate_after_two_layers_pass():
    """前两层均未命中，语义层命中 → 返回 None"""
    embedding_service = _make_embedding_service(ready=True)
    result = _make_vector_result("event_5", 0.90, "人民银行下调基准利率0.25%")
    vector_search_repo = _make_vector_search_repo([result])

    ret = await assess_event(
        title="央行降息25个基点",
        content="人民银行宣布下调基准利率",
        source_url="https://example.com/new-url",
        existing_url_hashes=set(),
        existing_titles=["新能源汽车销量创新高"],  # Jaccard 不命中
        embedding_service=embedding_service,
        vector_search_repo=vector_search_repo,
    )

    assert ret is None
    embedding_service.embed.assert_awaited_once()


@pytest.mark.asyncio
@patch("app.domain.services.impact_assessment.match_all", return_value=_MOCK_MATCH_RESULT)
@patch("app.domain.services.impact_assessment.sentiment_analyze", return_value=_MOCK_SENTIMENT_RESULT)
async def test_assess_event_semantic_not_duplicate_returns_result(mock_sentiment, mock_match):
    """前两层均未命中，语义层也未命中 → 返回评估结果"""
    embedding_service = _make_embedding_service(ready=True)
    result = _make_vector_result("event_6", 0.45, "新能源汽车销量创新高")
    vector_search_repo = _make_vector_search_repo([result])

    ret = await assess_event(
        title="央行降息25个基点",
        content="人民银行宣布下调基准利率",
        source_url="https://example.com/rate-cut",
        existing_url_hashes=set(),
        existing_titles=["新能源汽车销量创新高"],  # Jaccard 不命中
        embedding_service=embedding_service,
        vector_search_repo=vector_search_repo,
    )

    assert ret is not None
    assert ret["title"] == "央行降息25个基点"
    embedding_service.embed.assert_awaited_once()


@pytest.mark.asyncio
@patch("app.domain.services.impact_assessment.match_all", return_value=_MOCK_MATCH_RESULT)
@patch("app.domain.services.impact_assessment.sentiment_analyze", return_value=_MOCK_SENTIMENT_RESULT)
async def test_assess_event_embedding_unavailable_skips_semantic(mock_sentiment, mock_match):
    """embedding 服务不可用 → 跳过语义层，依靠前两层"""
    embedding_service = _make_embedding_service(ready=False)
    vector_search_repo = _make_vector_search_repo()

    ret = await assess_event(
        title="央行降息25个基点",
        content="人民银行宣布下调基准利率",
        source_url="https://example.com/rate-cut",
        existing_url_hashes=set(),
        existing_titles=["新能源汽车销量创新高"],  # Jaccard 不命中
        embedding_service=embedding_service,
        vector_search_repo=vector_search_repo,
    )

    # 前两层未命中，语义层跳过 → 返回评估结果
    assert ret is not None
    assert ret["title"] == "央行降息25个基点"
    embedding_service.embed.assert_not_awaited()


@pytest.mark.asyncio
@patch("app.domain.services.impact_assessment.match_all", return_value=_MOCK_MATCH_RESULT)
@patch("app.domain.services.impact_assessment.sentiment_analyze", return_value=_MOCK_SENTIMENT_RESULT)
async def test_assess_event_no_vector_services(mock_sentiment, mock_match):
    """embedding_service 和 vector_search_repo 均为 None → 跳过语义层"""
    ret = await assess_event(
        title="央行降息25个基点",
        content="人民银行宣布下调基准利率",
        source_url="https://example.com/rate-cut",
        existing_url_hashes=set(),
        existing_titles=["新能源汽车销量创新高"],
        embedding_service=None,
        vector_search_repo=None,
    )

    assert ret is not None
    assert ret["title"] == "央行降息25个基点"


@pytest.mark.asyncio
async def test_assess_event_empty_title_returns_none():
    """空标题直接返回 None，不执行任何去重"""
    embedding_service = _make_embedding_service(ready=True)
    vector_search_repo = _make_vector_search_repo()

    ret = await assess_event(
        title="",
        content="",
        source_url="https://example.com/test",
        existing_url_hashes=set(),
        existing_titles=[],
        embedding_service=embedding_service,
        vector_search_repo=vector_search_repo,
    )

    assert ret is None
    embedding_service.embed.assert_not_awaited()
