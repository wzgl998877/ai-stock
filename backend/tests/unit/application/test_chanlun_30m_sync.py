"""30m 同步转换逻辑测试（T023 配套）。

mock ``SinaKlineClient.fetch``/``TencentKlineClient.fetch`` 与 Repository，
验证 ``sync_stock_30m`` 的：
- raw dict → ``StockKline30m`` 字段转换（Decimal 精度、datetime 解析）；
- 空/非法行跳过、空数据不触发落库；
- 增量拉取（2026-08-25 新浪封 IP 后新增）：库中有数据 → datalen 缩小、
  已有最新行及更早的跳过；
- 降级链：新浪空返回 → 腾讯兜底。
"""

from datetime import datetime
from decimal import Decimal

import pytest

from app.application.sync import chanlun_30m_sync

pytestmark = pytest.mark.asyncio


class _FakeRepo:
    def __init__(self, latest=None):
        self.upserted: list = []
        self.cleared = False
        self.latest = latest

    async def upsert_kline_30m_batch(self, quotes):
        self.upserted = quotes

    async def get_latest_kline_30m_time(self, code):
        return self.latest


@pytest.fixture
def fake_fetch(monkeypatch):
    captured: dict = {"sina_calls": 0, "tencent_calls": 0}

    async def _sina_fetch(self, code, period="daily", count=None):
        captured["sina_calls"] += 1
        captured["count"] = count
        return captured.get("sina_data", [])

    async def _tencent_fetch(self, code, period="daily", count=None):
        captured["tencent_calls"] += 1
        captured["tencent_count"] = count
        return captured.get("tencent_data", [])

    monkeypatch.setattr(
        chanlun_30m_sync, "SinaKlineClient",
        lambda: type("S", (), {"fetch": _sina_fetch})(),
    )
    monkeypatch.setattr(
        chanlun_30m_sync, "TencentKlineClient",
        lambda: type("T", (), {"fetch": _tencent_fetch})(),
    )
    return captured


async def test_sync_converts_raw_to_entities(fake_fetch):
    fake_fetch["data"] = [
        {"trade_date": "2026-08-05 10:00:00", "open": 10.5, "high": 10.8,
         "low": 10.4, "close": 10.7, "volume": 1000, "amount": 10500.25},
    ]
    fake_fetch["sina_data"] = fake_fetch.pop("data")
    repo = _FakeRepo()
    n = await chanlun_30m_sync.sync_stock_30m("600519", repo)

    assert n == 1
    assert fake_fetch["sina_calls"] == 1
    q = repo.upserted[0]
    assert q.code == "600519"
    assert q.trade_time == datetime(2026, 8, 5, 10, 0, 0)
    assert q.open_price == Decimal("10.5")
    assert q.high_price == Decimal("10.8")
    assert q.amount == Decimal("10500.25")
    assert q.data_source == "sina"


async def test_sync_skips_invalid_rows(fake_fetch):
    fake_fetch["sina_data"] = [
        {"trade_date": "", "open": 1, "high": 2, "low": 0, "close": 1, "volume": 1, "amount": 1},
        {"trade_date": "not-a-date", "open": 1, "high": 2, "low": 0, "close": 1, "volume": 1, "amount": 1},
        {"trade_date": "2026-08-05 10:30:00", "open": 1, "high": 2, "low": 0, "close": 1, "volume": 1, "amount": 1},
    ]
    repo = _FakeRepo()
    n = await chanlun_30m_sync.sync_stock_30m("000001", repo)

    assert n == 1  # 仅 1 条合法
    assert len(repo.upserted) == 1
    assert repo.upserted[0].trade_time == datetime(2026, 8, 5, 10, 30, 0)


async def test_sync_empty_returns_zero(fake_fetch):
    fake_fetch["sina_data"] = []
    repo = _FakeRepo()
    n = await chanlun_30m_sync.sync_stock_30m("600519", repo)

    assert n == 0
    assert repo.upserted == []  # 未触发落库


# ---------------------------------------------------------------------------
# 增量拉取（2026-08-25 新浪 456 封禁后新增）
# ---------------------------------------------------------------------------

async def test_sync_full_backfill_when_no_history(fake_fetch):
    """首次回补：库中无数据 → count=None（SinaKlineClient 用默认 1500 全量）。"""
    fake_fetch["sina_data"] = [
        {"trade_date": "2026-08-05 10:00:00", "open": 1, "high": 2,
         "low": 0, "close": 1, "volume": 1, "amount": 1},
    ]
    repo = _FakeRepo(latest=None)
    await chanlun_30m_sync.sync_stock_30m("600519", repo)

    assert fake_fetch["count"] is None  # 全量回补


async def test_sync_incremental_when_history_exists(fake_fetch):
    """增量：库中已有数据 → count=INCREMENT_COUNT、只落库晚于库内最新行的 K 线。"""
    fake_fetch["sina_data"] = [
        # 库内已有的最新行（重复出现，应跳过不重写）
        {"trade_date": "2026-08-25 11:30:00", "open": 1, "high": 2,
         "low": 0, "close": 1, "volume": 1, "amount": 1},
        # 两根新 K 线
        {"trade_date": "2026-08-25 13:30:00", "open": 1, "high": 2,
         "low": 0, "close": 1, "volume": 1, "amount": 1},
        {"trade_date": "2026-08-25 14:00:00", "open": 1, "high": 2,
         "low": 0, "close": 1, "volume": 1, "amount": 1},
    ]
    repo = _FakeRepo(latest=datetime(2026, 8, 25, 11, 30))
    n = await chanlun_30m_sync.sync_stock_30m("600519", repo)

    assert fake_fetch["count"] == chanlun_30m_sync.INCREMENT_COUNT  # 缩小 datalen
    assert n == 2
    assert [q.trade_time for q in repo.upserted] == [
        datetime(2026, 8, 25, 13, 30), datetime(2026, 8, 25, 14, 0),
    ]


async def test_sync_incremental_no_new_rows_returns_zero(fake_fetch):
    """增量无新行（数据源未更新/全部已存在）→ 0 且不触发落库。"""
    fake_fetch["sina_data"] = [
        {"trade_date": "2026-08-25 11:30:00", "open": 1, "high": 2,
         "low": 0, "close": 1, "volume": 1, "amount": 1},
    ]
    repo = _FakeRepo(latest=datetime(2026, 8, 25, 11, 30))
    n = await chanlun_30m_sync.sync_stock_30m("600519", repo)

    assert n == 0
    assert repo.upserted == []


# ---------------------------------------------------------------------------
# 降级链：新浪 → 腾讯（2026-08-25 新浪封禁后新增）
# ---------------------------------------------------------------------------

async def test_fallback_to_tencent_when_sina_empty(fake_fetch):
    """新浪空返回（含被限流）→ 腾讯兜底，data_source 标记 tencent。"""
    fake_fetch["sina_data"] = []
    fake_fetch["tencent_data"] = [
        {"trade_date": "2026-08-25 14:30:00", "open": 10.0, "high": 10.5,
         "low": 9.9, "close": 10.2, "volume": 100, "amount": None},
    ]
    repo = _FakeRepo(latest=datetime(2026, 8, 25, 14, 0))
    n = await chanlun_30m_sync.sync_stock_30m("600519", repo)

    assert fake_fetch["sina_calls"] == 1 and fake_fetch["tencent_calls"] == 1
    assert n == 1
    assert repo.upserted[0].data_source == "tencent"  # 溯源降级来源
    assert repo.upserted[0].trade_time == datetime(2026, 8, 25, 14, 30)


async def test_no_fallback_when_sina_ok(fake_fetch):
    """新浪正常返回 → 不调用腾讯。"""
    fake_fetch["sina_data"] = [
        {"trade_date": "2026-08-25 14:30:00", "open": 1, "high": 2,
         "low": 0, "close": 1, "volume": 1, "amount": 1},
    ]
    repo = _FakeRepo(latest=datetime(2026, 8, 25, 14, 0))
    await chanlun_30m_sync.sync_stock_30m("600519", repo)

    assert fake_fetch["tencent_calls"] == 0


async def test_both_sources_empty_returns_zero(fake_fetch):
    """两边都空 → 真无数据，0 落库。"""
    fake_fetch["sina_data"] = []
    fake_fetch["tencent_data"] = []
    repo = _FakeRepo()
    n = await chanlun_30m_sync.sync_stock_30m("600519", repo)

    assert n == 0
    assert fake_fetch["sina_calls"] == 1 and fake_fetch["tencent_calls"] == 1
