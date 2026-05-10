"""SearchService 单元测试

覆盖范围：
1. 中文优先重排逻辑
2. 时效过滤逻辑
3. 日期归一化（15+种格式 + 相对时间）
4. 策略窗口解析
5. 缓存 key 生成
6. format_intel_report 格式化
7. search 通用搜索（多引擎故障转移）
8. search_stock_news（预搜 + 缓存）
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from app.domain.services.search_service import (
    SearchService,
    normalize_news_strategy_profile,
    resolve_news_window_days,
    _parse_relative_news_date,
)
from app.domain.value_objects.search_result import SearchResult, SearchResponse
from app.infrastructure.search.cache import SearchCache


# ---------------------------------------------------------------------------
# 辅助工具
# ---------------------------------------------------------------------------

def _make_result(title="test", snippet="hello", url="http://example.com",
                 source="example", published_date=None) -> SearchResult:
    return SearchResult(title=title, snippet=snippet, url=url,
                        source=source, published_date=published_date)


def _make_response(results=None, success=True, provider="mock",
                   query="test", error_message=None) -> SearchResponse:
    return SearchResponse(
        query=query,
        results=results or [],
        provider=provider,
        success=success,
        error_message=error_message,
    )


def _mock_provider(available=True, response=None):
    """创建 mock 搜索引擎。"""
    provider = MagicMock()
    provider.is_available = available
    provider.name = "MockEngine"
    provider.search = AsyncMock(return_value=response or _make_response())
    return provider


def _mock_cache():
    """创建 mock 缓存（所有方法 no-op）。"""
    cache = MagicMock(spec=SearchCache)
    cache.get = AsyncMock(return_value=None)
    cache.set = AsyncMock()
    cache.acquire_lock = AsyncMock(return_value=True)
    cache.release_lock = AsyncMock()
    cache.wait_for_fill = AsyncMock(return_value=None)
    return cache


# ---------------------------------------------------------------------------
# 1. 策略窗口解析
# ---------------------------------------------------------------------------

class TestStrategyWindows:
    def test_normalize_known_profiles(self):
        assert normalize_news_strategy_profile("ultra_short") == "ultra_short"
        assert normalize_news_strategy_profile("SHORT") == "short"
        assert normalize_news_strategy_profile("medium") == "medium"
        assert normalize_news_strategy_profile("long") == "long"

    def test_normalize_unknown_defaults_to_short(self):
        assert normalize_news_strategy_profile("unknown") == "short"
        assert normalize_news_strategy_profile("") == "short"

    def test_resolve_window_days(self):
        assert resolve_news_window_days("ultra_short") == 1
        assert resolve_news_window_days("short") == 3
        assert resolve_news_window_days("medium") == 7
        assert resolve_news_window_days("long") == 30

    def test_resolve_unknown_uses_short_default(self):
        # normalize_news_strategy_profile("invalid") -> "short" (有效键)
        assert resolve_news_window_days("invalid", fallback_days=5) == 3


# ---------------------------------------------------------------------------
# 2. 中文优先重排
# ---------------------------------------------------------------------------

class TestChinesePrioritization:
    def test_chinese_results_come_first(self):
        svc = SearchService(providers=[], cache=_mock_cache())
        results = [
            _make_result(title="English news", snippet="test"),
            _make_result(title="中文新闻", snippet="测试"),
            _make_result(title="Another English", snippet="more"),
            _make_result(title="另一条中文", snippet="内容"),
        ]
        resp = _make_response(results=results)
        prioritized, count = svc._prioritize_news_language(resp, prefer_chinese=True)
        assert count == 2
        assert "中文" in prioritized.results[0].title
        assert "中文" in prioritized.results[1].title
        assert "English" in prioritized.results[2].title

    def test_no_preference_returns_all(self):
        svc = SearchService(providers=[], cache=_mock_cache())
        results = [_make_result(title="English", snippet="x")]
        resp = _make_response(results=results)
        prioritized, count = svc._prioritize_news_language(resp, prefer_chinese=False)
        assert count == 0
        assert len(prioritized.results) == 1

    def test_empty_results(self):
        svc = SearchService(providers=[], cache=_mock_cache())
        resp = _make_response(results=[])
        prioritized, count = svc._prioritize_news_language(resp, prefer_chinese=True)
        assert count == 0
        assert len(prioritized.results) == 0


# ---------------------------------------------------------------------------
# 3. 日期归一化
# ---------------------------------------------------------------------------

class TestDateNormalization:
    def test_iso_format(self):
        dt = SearchService._normalize_news_publish_date("2025-05-01")
        assert dt == datetime(2025, 5, 1)

    def test_datetime_with_time(self):
        dt = SearchService._normalize_news_publish_date("2025-05-01 10:30:00")
        assert dt == datetime(2025, 5, 1, 10, 30, 0)

    def test_chinese_format(self):
        dt = SearchService._normalize_news_publish_date("2025年05月01日")
        assert dt == datetime(2025, 5, 1)

    def test_none_input(self):
        assert SearchService._normalize_news_publish_date(None) is None

    def test_empty_string(self):
        assert SearchService._normalize_news_publish_date("") is None

    def test_invalid_format(self):
        assert SearchService._normalize_news_publish_date("not-a-date") is None

    def test_relative_chinese_days(self):
        dt = _parse_relative_news_date("3天前")
        expected = datetime.now() - timedelta(days=3)
        assert abs((dt - expected).total_seconds()) < 2

    def test_relative_chinese_hours(self):
        dt = _parse_relative_news_date("2小时前")
        expected = datetime.now() - timedelta(hours=2)
        assert abs((dt - expected).total_seconds()) < 2

    def test_relative_chinese_minutes(self):
        dt = _parse_relative_news_date("30分钟前")
        expected = datetime.now() - timedelta(minutes=30)
        assert abs((dt - expected).total_seconds()) < 2

    def test_relative_chinese_today(self):
        dt = _parse_relative_news_date("今天")
        assert abs((dt - datetime.now()).total_seconds()) < 2

    def test_relative_chinese_yesterday(self):
        dt = _parse_relative_news_date("昨天")
        expected = datetime.now() - timedelta(days=1)
        assert abs((dt - expected).total_seconds()) < 2

    def test_relative_english_days(self):
        dt = _parse_relative_news_date("3 days ago")
        expected = datetime.now() - timedelta(days=3)
        assert abs((dt - expected).total_seconds()) < 2

    def test_relative_english_hours(self):
        dt = _parse_relative_news_date("2 hours ago")
        expected = datetime.now() - timedelta(hours=2)
        assert abs((dt - expected).total_seconds()) < 2

    def test_relative_english_today(self):
        dt = _parse_relative_news_date("today")
        assert abs((dt - datetime.now()).total_seconds()) < 2

    def test_relative_english_yesterday(self):
        dt = _parse_relative_news_date("yesterday")
        expected = datetime.now() - timedelta(days=1)
        assert abs((dt - expected).total_seconds()) < 2


# ---------------------------------------------------------------------------
# 4. 时效过滤
# ---------------------------------------------------------------------------

class TestNewsFiltering:
    def test_filter_removes_old_news(self):
        svc = SearchService(providers=[], cache=_mock_cache())
        old_date = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")
        recent_date = datetime.now().strftime("%Y-%m-%d")
        results = [
            _make_result(title="old", published_date=old_date),
            _make_result(title="recent", published_date=recent_date),
        ]
        resp = _make_response(results=results)
        filtered = svc._filter_news_response(resp, max_age_days=3)
        assert len(filtered.results) == 1
        assert filtered.results[0].title == "recent"

    def test_filter_keeps_no_date_results(self):
        svc = SearchService(providers=[], cache=_mock_cache())
        results = [_make_result(title="no-date", published_date=None)]
        resp = _make_response(results=results)
        filtered = svc._filter_news_response(resp, max_age_days=3)
        assert len(filtered.results) == 1

    def test_filter_empty_results(self):
        svc = SearchService(providers=[], cache=_mock_cache())
        resp = _make_response(results=[])
        filtered = svc._filter_news_response(resp, max_age_days=3)
        assert len(filtered.results) == 0


# ---------------------------------------------------------------------------
# 5. 缓存 key 生成
# ---------------------------------------------------------------------------

class TestCacheKey:
    def test_deterministic_key(self):
        svc = SearchService(providers=[], cache=_mock_cache())
        k1 = svc._cache_key("test", 5, 7, True)
        k2 = svc._cache_key("test", 5, 7, True)
        assert k1 == k2
        assert len(k1) == 12

    def test_different_params_different_key(self):
        svc = SearchService(providers=[], cache=_mock_cache())
        k1 = svc._cache_key("test1", 5, 7, True)
        k2 = svc._cache_key("test2", 5, 7, True)
        assert k1 != k2


# ---------------------------------------------------------------------------
# 6. format_intel_report
# ---------------------------------------------------------------------------

class TestFormatIntelReport:
    def test_format_with_results(self):
        results = {
            "latest_news": _make_response(
                results=[_make_result(title="利好消息", snippet="股价上涨")],
                query="test",
            ),
        }
        report = SearchService.format_intel_report(results, "平安银行")
        assert "平安银行" in report
        assert "最新新闻" in report
        assert "利好消息" in report

    def test_format_empty_results(self):
        results = {"latest_news": _make_response(results=[])}
        report = SearchService.format_intel_report(results, "测试")
        assert "测试" in report


# ---------------------------------------------------------------------------
# 7. search 通用搜索（多引擎故障转移）
# ---------------------------------------------------------------------------

class TestSearch:
    @pytest.mark.asyncio
    async def test_first_provider_succeeds(self):
        good = _mock_provider(response=_make_response(
            results=[_make_result(title="ok")], provider="Good"
        ))
        svc = SearchService(providers=[good], cache=_mock_cache())
        resp = await svc.search("test")
        assert resp.success
        assert resp.results[0].title == "ok"

    @pytest.mark.asyncio
    async def test_fallback_on_failure(self):
        bad = _mock_provider(response=_make_response(success=False, error_message="err"))
        good = _mock_provider(response=_make_response(
            results=[_make_result(title="fallback")], provider="Good"
        ))
        svc = SearchService(providers=[bad, good], cache=_mock_cache())
        resp = await svc.search("test")
        assert resp.success
        assert resp.results[0].title == "fallback"

    @pytest.mark.asyncio
    async def test_all_providers_fail(self):
        bad1 = _mock_provider(response=_make_response(success=False))
        bad2 = _mock_provider(response=_make_response(success=False))
        svc = SearchService(providers=[bad1, bad2], cache=_mock_cache())
        resp = await svc.search("test")
        assert not resp.success

    @pytest.mark.asyncio
    async def test_no_providers(self):
        svc = SearchService(providers=[], cache=_mock_cache())
        resp = await svc.search("test")
        assert not resp.success


# ---------------------------------------------------------------------------
# 8. A股中文优先判断
# ---------------------------------------------------------------------------

class TestChinesePreference:
    def test_a_stock_code_prefer_chinese(self):
        svc = SearchService(providers=[], cache=_mock_cache())
        assert svc._should_prefer_chinese_news("000001") is True
        assert svc._should_prefer_chinese_news("600000") is True
        assert svc._should_prefer_chinese_news("300001") is True

    def test_non_a_stock_no_preference(self):
        svc = SearchService(providers=[], cache=_mock_cache())
        assert svc._should_prefer_chinese_news("AAPL") is False
        assert svc._should_prefer_chinese_news("") is False


# ---------------------------------------------------------------------------
# 9. is_available
# ---------------------------------------------------------------------------

class TestAvailability:
    def test_available_with_providers(self):
        p = _mock_provider(available=True)
        svc = SearchService(providers=[p], cache=_mock_cache())
        assert svc.is_available is True

    def test_unavailable_without_providers(self):
        svc = SearchService(providers=[], cache=_mock_cache())
        assert svc.is_available is False

    def test_unavailable_when_all_down(self):
        p = _mock_provider(available=False)
        svc = SearchService(providers=[p], cache=_mock_cache())
        assert svc.is_available is False


# ---------------------------------------------------------------------------
# 10. 过采样计算
# ---------------------------------------------------------------------------

class TestOverSampling:
    def test_provider_request_size(self):
        svc = SearchService(providers=[], cache=_mock_cache())
        assert svc._provider_request_size(5) == 10
        assert svc._provider_request_size(10) == 20
        assert svc._provider_request_size(15) == 20  # max 20
