"""30m 同步转换逻辑测试（T023 配套）。

mock ``SinaKlineClient.fetch`` 与 Repository，验证 ``sync_stock_30m`` 的：
- raw dict → ``StockKline30m`` 字段转换（Decimal 精度、datetime 解析）；
- 空/非法行跳过；
- 空数据不触发落库。
"""

from datetime import datetime
from decimal import Decimal

import pytest

from app.application.sync import chanlun_30m_sync

pytestmark = pytest.mark.asyncio


class _FakeRepo:
    def __init__(self):
        self.upserted: list = []
        self.cleared = False

    async def upsert_kline_30m_batch(self, quotes):
        self.upserted = quotes

    async def get_latest_kline_30m_time(self, code):
        return None


@pytest.fixture
def fake_fetch(monkeypatch):
    captured: dict = {}

    async def _fetch(self, code, period="daily"):
        captured["code"], captured["period"] = code, period
        return captured["data"]

    monkeypatch.setattr(chanlun_30m_sync, "SinaKlineClient", lambda: type("C", (), {"fetch": _fetch})())
    return captured


async def test_sync_converts_raw_to_entities(fake_fetch):
    fake_fetch["data"] = [
        {"trade_date": "2026-08-05 10:00:00", "open": 10.5, "high": 10.8,
         "low": 10.4, "close": 10.7, "volume": 1000, "amount": 10500.25},
    ]
    repo = _FakeRepo()
    n = await chanlun_30m_sync.sync_stock_30m("600519", repo)

    assert n == 1
    assert fake_fetch["period"] == "m30"
    q = repo.upserted[0]
    assert q.code == "600519"
    assert q.trade_time == datetime(2026, 8, 5, 10, 0, 0)
    assert q.open_price == Decimal("10.5")
    assert q.high_price == Decimal("10.8")
    assert q.amount == Decimal("10500.25")
    assert q.data_source == "sina"


async def test_sync_skips_invalid_rows(fake_fetch):
    fake_fetch["data"] = [
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
    fake_fetch["data"] = []
    repo = _FakeRepo()
    n = await chanlun_30m_sync.sync_stock_30m("600519", repo)

    assert n == 0
    assert repo.upserted == []  # 未触发落库
