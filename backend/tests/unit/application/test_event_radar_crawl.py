"""事件采集去重与单条容错单元测试

覆盖 crawl_and_process 的关键修复：
1. 批次开始时批量查 DB 已有 url_hash，跨批次去重
2. 撞唯一索引时 SAVEPOINT 只回滚当前条，不中断整批
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from sqlalchemy.exc import IntegrityError

from app.domain.entities.impact_event import ImpactEvent
from app.domain.services.event_dedup import url_hash as calc_url_hash
from app.infrastructure.crawler.base_provider import CrawledArticle


class _FakeSavepoint:
    """模拟 session.begin_nested() 的 SAVEPOINT：异常原样抛给外层 except"""

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


def _make_article(url: str, title: str) -> CrawledArticle:
    return CrawledArticle(title=title, url=url, content=f"{title}正文", source="cls")


def _assess_result(title: str) -> dict:
    return {
        "title": title,
        "summary": f"{title}摘要",
        "sentiment": "neutral",
        "importance": "medium",
        "confidence": 0.8,
        "affected_stocks": [{"code": "600916", "name": "中国黄金"}],
        "affected_industries": [{"code": "gold", "name": "黄金"}],
        "url_hash": None,
    }


async def _fake_assess(title, content="", source_url="", existing_url_hashes=None,
                       existing_titles=None, **kwargs):
    """复刻 assess_event 第一层 URL 去重语义，其余放行"""
    from app.domain.services.event_dedup import is_duplicate_url
    if existing_url_hashes and source_url and is_duplicate_url(source_url, existing_url_hashes):
        return None
    result = _assess_result(title)
    result["url_hash"] = calc_url_hash(source_url) if source_url else None
    return result


def _build_use_case(articles, existing_hashes, article_create=None):
    """组装带 mock 仓储的 EventRadarUseCase，返回 (uc, mocks)"""
    from app.application.use_cases.event_radar import EventRadarUseCase

    event_seq = iter(range(101, 110))

    async def _create_event(event):
        event.event_id = next(event_seq)
        return event

    event_repo = MagicMock()
    event_repo.create = AsyncMock(side_effect=_create_event)
    event_repo.session = MagicMock()
    event_repo.session.begin_nested = MagicMock(return_value=_FakeSavepoint())

    article_repo = MagicMock()
    article_repo.get_existing_hashes = AsyncMock(return_value=set(existing_hashes))
    if article_create is not None:
        article_repo.create = AsyncMock(side_effect=article_create)
    else:
        article_repo.create = AsyncMock(side_effect=lambda a: a)

    impact_repo = MagicMock()
    mock_result = MagicMock()
    mock_result.fetchall.return_value = []
    impact_repo.session = MagicMock()
    impact_repo.session.execute = AsyncMock(return_value=mock_result)

    provider = MagicMock()
    provider.fetch_latest = AsyncMock(return_value=articles)

    uc = EventRadarUseCase(
        event_repo=event_repo,
        article_repo=article_repo,
        impact_repo=impact_repo,
    )
    return uc, {"event_repo": event_repo, "article_repo": article_repo, "provider": provider}


class TestCrawlAndProcessDedup:
    """跨批次 URL 去重"""

    @pytest.mark.asyncio
    async def test_db_existing_hash_merged_into_dedup(self, monkeypatch):
        """DB 已有 url_hash 的文章跳过，只处理新文章"""
        dup = _make_article("https://www.cls.cn/detail/2455680", "金价上调")
        fresh = _make_article("https://www.cls.cn/detail/2455681", "央行降准")
        uc, mocks = _build_use_case(
            articles=[dup, fresh],
            existing_hashes={calc_url_hash(dup.url)},
        )
        monkeypatch.setattr(
            "app.infrastructure.crawler.cls_provider.ClsProvider",
            lambda: mocks["provider"],
        )
        with patch("app.application.use_cases.event_radar.assess_event", _fake_assess):
            result = await uc.crawl_and_process()

        assert result["crawled"] == 2
        assert result["new_events"] == 1
        assert mocks["event_repo"].create.call_count == 1
        assert mocks["article_repo"].create.call_count == 1
        saved = mocks["article_repo"].create.call_args[0][0]
        assert saved.url == fresh.url

    @pytest.mark.asyncio
    async def test_no_articles_short_circuit(self, monkeypatch):
        """空批次直接返回"""
        uc, mocks = _build_use_case(articles=[], existing_hashes=set())
        monkeypatch.setattr(
            "app.infrastructure.crawler.cls_provider.ClsProvider",
            lambda: mocks["provider"],
        )
        with patch("app.application.use_cases.event_radar.assess_event", _fake_assess):
            result = await uc.crawl_and_process()

        assert result == {"crawled": 0, "new_events": 0}
        mocks["article_repo"].get_existing_hashes.assert_not_awaited()


class TestCrawlAndProcessIntegrityError:
    """撞唯一索引时单条容错"""

    @pytest.mark.asyncio
    async def test_integrity_error_skips_single_article(self, monkeypatch):
        """article 撞唯一索引：跳过该条，后续文章继续入库"""
        first = _make_article("https://www.cls.cn/detail/1000001", "第一条重复文章")
        second = _make_article("https://www.cls.cn/detail/1000002", "第二条新文章")

        call_state = {"n": 0}

        async def _article_create(article):
            call_state["n"] += 1
            if call_state["n"] == 1:
                raise IntegrityError("INSERT INTO t_impact_article ...", {}, Exception("dup"))
            return article

        uc, mocks = _build_use_case(
            articles=[first, second],
            existing_hashes=set(),
            article_create=_article_create,
        )
        monkeypatch.setattr(
            "app.infrastructure.crawler.cls_provider.ClsProvider",
            lambda: mocks["provider"],
        )
        with patch("app.application.use_cases.event_radar.assess_event", _fake_assess):
            result = await uc.crawl_and_process()

        # 第一条被回滚跳过，第二条正常入库，批次未中断
        assert result["new_events"] == 1
        assert mocks["article_repo"].create.call_count == 2
        assert mocks["event_repo"].create.call_count == 2
        saved = mocks["article_repo"].create.call_args[0][0]
        assert saved.url == second.url

    @pytest.mark.asyncio
    async def test_within_batch_duplicate_url_dedup(self, monkeypatch):
        """同一批次内重复 URL：首条入库后其余被批内去重拦截"""
        a1 = _make_article("https://www.cls.cn/detail/1000003", "同一事件标题甲")
        a2 = _make_article("https://www.cls.cn/detail/1000003", "同一事件标题乙")
        uc, mocks = _build_use_case(articles=[a1, a2], existing_hashes=set())
        monkeypatch.setattr(
            "app.infrastructure.crawler.cls_provider.ClsProvider",
            lambda: mocks["provider"],
        )
        with patch("app.application.use_cases.event_radar.assess_event", _fake_assess):
            result = await uc.crawl_and_process()

        assert result["crawled"] == 2
        assert result["new_events"] == 1
