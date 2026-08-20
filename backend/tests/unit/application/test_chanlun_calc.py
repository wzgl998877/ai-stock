"""ChanlunCalcUseCase 单元测试（T026）。

聚焦「装配 + 落库契约」：验证 UseCase 正确读取 K 线、注入 MACD、调用幂等 upsert 与
结构覆盖；不重测引擎本身的信号识别（已在 ``test_chanlun_service.py`` 覆盖）。
"""

from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest

from app.application.use_cases.chanlun_calc import ChanlunCalcUseCase
from app.domain.entities.chanlun import StructureSnapshot
from app.domain.models.stock_data import StockDailyQuote, StockKline30m

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------

class FakeStockDataRepo:
    def __init__(self, daily=None, m30=None):
        self._daily = daily or []
        self._m30 = m30 or []

    async def get_daily(self, code, start_date=None, end_date=None, period="daily"):
        return self._daily

    async def get_kline_30m(self, code, start_time=None, end_time=None):
        return self._m30


class FakeChanlunRepo:
    def __init__(self, added_mapper=None):
        self.signals_upserted: list[list] = []
        self.structures: list[StructureSnapshot] = []
        self.added_mapper = added_mapper  # 可定制返回的新增信号列表

    async def upsert_signals_batch(self, signals):
        self.signals_upserted.append(signals)
        if self.added_mapper is not None:
            return self.added_mapper(signals)
        return list(signals)

    async def upsert_structure(self, snapshot):
        self.structures.append(snapshot)


# ---------------------------------------------------------------------------
# 合成 K 线构造器：先涨后跌再涨，足以形成分型/笔
# ---------------------------------------------------------------------------

def _synth_daily(n: int = 60) -> list[StockDailyQuote]:
    base = date(2026, 1, 5)
    # 前 1/3 涨、中 1/3 跌、后 1/3 涨，制造明显的顶/底分型
    seg = n // 3
    closes = []
    for i in range(n):
        if i < seg:
            closes.append(Decimal(10) + Decimal(i) * Decimal("0.3"))
        elif i < 2 * seg:
            closes.append(Decimal(10) + Decimal(seg) * Decimal("0.3") - Decimal(i - seg) * Decimal("0.3"))
        else:
            closes.append(Decimal(10) + Decimal(i - 2 * seg) * Decimal("0.3"))
    quotes = []
    for i, c in enumerate(closes):
        quotes.append(
            StockDailyQuote(
                code="600000",
                trade_date=base + timedelta(days=i),
                period="daily",
                open_price=c - Decimal("0.1"),
                high_price=c + Decimal("0.2"),
                low_price=c - Decimal("0.2"),
                close_price=c,
                volume=Decimal(1000),
            )
        )
    return quotes


def _synth_m30(n: int = 60) -> list[StockKline30m]:
    base = datetime(2026, 1, 5, 10, 0)
    seg = n // 3
    closes = []
    for i in range(n):
        if i < seg:
            closes.append(Decimal(10) + Decimal(i) * Decimal("0.3"))
        elif i < 2 * seg:
            closes.append(Decimal(10) + Decimal(seg) * Decimal("0.3") - Decimal(i - seg) * Decimal("0.3"))
        else:
            closes.append(Decimal(10) + Decimal(i - 2 * seg) * Decimal("0.3"))
    quotes = []
    for i, c in enumerate(closes):
        quotes.append(
            StockKline30m(
                code="600000",
                trade_time=base + timedelta(minutes=30 * i),
                open_price=c - Decimal("0.1"),
                high_price=c + Decimal("0.2"),
                low_price=c - Decimal("0.2"),
                close_price=c,
                volume=Decimal(1000),
            )
        )
    return quotes


# ---------------------------------------------------------------------------
# 测试
# ---------------------------------------------------------------------------

async def test_daily_path_persists_structure_and_signals():
    stock_repo = FakeStockDataRepo(daily=_synth_daily())
    chanlun_repo = FakeChanlunRepo()
    uc = ChanlunCalcUseCase(stock_repo, chanlun_repo, algo_version="1.0.0")

    signals, snapshot, new_signals = await uc.compute_and_persist("600000", "daily")

    assert snapshot.stock_code == "600000"
    assert snapshot.period == "daily"
    assert snapshot.algo_version == "1.0.0"
    # 结构快照覆盖落库一次
    assert len(chanlun_repo.structures) == 1
    assert chanlun_repo.structures[0].period == "daily"
    # 若产生信号：dedup_key 自动生成 + 幂等落库被调用
    if signals:
        assert all(s.dedup_key for s in signals)
        assert all(s.user_id is None for s in signals)  # 全局信号
        assert chanlun_repo.signals_upserted
        # Fake 全量新增 → new_signals 与落库入参一致
        assert new_signals == chanlun_repo.signals_upserted[0]


async def test_m30_path_persists_structure():
    stock_repo = FakeStockDataRepo(m30=_synth_m30())
    chanlun_repo = FakeChanlunRepo()
    uc = ChanlunCalcUseCase(stock_repo, chanlun_repo, algo_version="1.0.0")

    signals, snapshot, new_signals = await uc.compute_and_persist("600000", "m30")

    assert snapshot.period == "m30"
    assert len(chanlun_repo.structures) == 1
    assert chanlun_repo.structures[0].period == "m30"
    if signals:
        assert all(s.period == "m30" for s in signals)
        assert isinstance(new_signals, list)


async def test_no_data_raises_for_skip_semantics():
    """无 K 线数据时抛 ``NoKlineDataError``（监控层据此记 skipped，不误报 success）。"""
    from app.application.use_cases.chanlun_calc import NoKlineDataError

    stock_repo = FakeStockDataRepo(daily=[], m30=[])
    chanlun_repo = FakeChanlunRepo()
    uc = ChanlunCalcUseCase(stock_repo, chanlun_repo, algo_version="1.0.0")

    with pytest.raises(NoKlineDataError):
        await uc.compute_and_persist("600000", "daily")

    # 无数据时不应落库（避免空快照覆盖已有快照）
    assert chanlun_repo.structures == []
    assert chanlun_repo.signals_upserted == []


async def test_macd_injected_into_bars():
    """``_assemble_bars`` 在 close 序列足够长时为每根 K 注入 MACD BAR。"""
    stock_repo = FakeStockDataRepo(daily=_synth_daily(60))
    uc = ChanlunCalcUseCase(stock_repo, FakeChanlunRepo(), algo_version="1.0.0")

    bars = await uc._load_bars("600000", "daily")

    assert len(bars) == 60
    # 26 根之后 MACD 有效（calc_macd 的 slow_period），BAR 为 Decimal
    assert bars[30].macd_bar is not None
    assert isinstance(bars[30].macd_bar, Decimal)


async def test_dirty_rows_filtered():
    """OHLC 含 None 的脏数据行被丢弃，不进入引擎。"""
    quotes = _synth_daily(10)
    quotes[3].close_price = None  # 脏数据
    stock_repo = FakeStockDataRepo(daily=quotes)
    uc = ChanlunCalcUseCase(stock_repo, FakeChanlunRepo(), algo_version="1.0.0")

    bars = await uc._load_bars("600000", "daily")

    assert len(bars) == 9  # 丢弃 1 行


async def test_m30_forming_kline_excluded():
    """未收盘 forming K 线（trade_time > now）不进入引擎。

    数据源盘中返回的 30m K 线时间戳为周期结束时点（未来时点），
    参与计算会用临时形态触发信号（定型后可推翻的重绘风险）。
    """
    quotes = _synth_m30()
    last_closed = quotes[-1].trade_time
    quotes.append(
        StockKline30m(
            code="600000",
            trade_time=datetime.now() + timedelta(minutes=24),  # forming 中
            open_price=Decimal("10"),
            high_price=Decimal("10.5"),
            low_price=Decimal("9.8"),
            close_price=Decimal("10.3"),
            volume=Decimal(500),
        )
    )
    stock_repo = FakeStockDataRepo(m30=quotes)
    uc = ChanlunCalcUseCase(stock_repo, FakeChanlunRepo(), algo_version="1.0.0")

    bars = await uc._load_bars("600000", "m30")

    assert all(b.time <= datetime.now() for b in bars)
    assert bars[-1].time == last_closed  # forming 行被剔除，末根为最后已收盘 K 线


async def test_m30_boundary_trade_time_equals_now_kept():
    """边界：trade_time == now 视为已收盘（<= 判定），保留。"""
    quotes = _synth_m30()
    edge = datetime.now()
    quotes.append(
        StockKline30m(
            code="600000",
            trade_time=edge,
            open_price=Decimal("10"),
            high_price=Decimal("10.5"),
            low_price=Decimal("9.8"),
            close_price=Decimal("10.3"),
            volume=Decimal(500),
        )
    )
    stock_repo = FakeStockDataRepo(m30=quotes)
    uc = ChanlunCalcUseCase(stock_repo, FakeChanlunRepo(), algo_version="1.0.0")

    bars = await uc._load_bars("600000", "m30")

    assert bars[-1].time == edge
