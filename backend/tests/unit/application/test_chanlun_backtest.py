"""ChanlunBacktestUseCase 单元测试（T042）。

聚焦纯逻辑：窗口收益计算（``_build_details`` 的 5/10/20/60 窗口 + ``window_complete``
越界处理）与聚合统计（``_aggregate`` 的胜率/平均/中位/盈亏比 + note 标注）。
不重测引擎信号识别（已在 ``test_chanlun_service.py`` 覆盖），也不做 DB IO。
"""

from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest

from app.application.use_cases.chanlun_backtest import ChanlunBacktestUseCase, _q6
from app.application.use_cases.chanlun_calc import ChanlunCalcUseCase
from app.domain.entities.chanlun import ChanlunSignal, KlineBar
from tests.unit.application.test_chanlun_calc import FakeChanlunRepo, FakeStockDataRepo

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# 构造工具
# ---------------------------------------------------------------------------

def _bars(n: int, base: datetime | None = None) -> list[KlineBar]:
    """n 根单调上涨 K 线：close = 10 + i*0.1，便于手算窗口收益。"""
    base = base or datetime(2025, 1, 5)
    bars = []
    for i in range(n):
        c = Decimal(10) + Decimal(i) * Decimal("0.1")
        bars.append(
            KlineBar(
                time=base + timedelta(days=i),
                open=c, high=c + Decimal("0.1"), low=c - Decimal("0.1"),
                close=c, volume=Decimal(1000), macd_bar=Decimal(0), index=i,
            )
        )
    return bars


def _signal(at_idx: int, bars: list[KlineBar], signal_type: str = "buy1") -> ChanlunSignal:
    return ChanlunSignal(
        stock_code="600000", period="daily", signal_type=signal_type,
        structure_level="segment", signal_time=bars[at_idx].time,
        confirmed_at=bars[at_idx].time, trigger_price=bars[at_idx].close,
        algo_version="1.0.0", status="confirmed",
    )


def _make_uc() -> ChanlunBacktestUseCase:
    calc = ChanlunCalcUseCase(FakeStockDataRepo(), FakeChanlunRepo(), algo_version="1.0.0")
    return ChanlunBacktestUseCase(chanlun_calc=calc, backtest_repo=FakeChanlunRepo())  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# _build_details：窗口收益 + window_complete
# ---------------------------------------------------------------------------

async def test_window_returns_and_complete_flag():
    bars = _bars(70)  # 索引 0..69
    uc = _make_uc()
    start, end = date(2024, 12, 1), date(2026, 12, 31)

    # 信号在 idx=5，足够远的未来 → 全窗口完整
    sig_far = _signal(5, bars)
    # 信号在 idx=63：ret_5 存在（68<70），ret_10/20/60 越界 → window_complete=False
    sig_near = _signal(63, bars)
    details = uc._build_details(1, "600000", "daily", [sig_far, sig_near], bars, start, end)

    assert len(details) == 2
    far = next(d for d in details if d.signal_time == bars[5].time)
    near = next(d for d in details if d.signal_time == bars[63].time)

    # 远端信号：ret_5 = (close[10]-close[5])/close[5] = (11.0-10.5)/10.5
    expected_ret5 = _q6((bars[10].close - bars[5].close) / bars[5].close)
    assert far.ret_5 == expected_ret5
    assert far.ret_60 is not None  # 5+60=65 < 70
    assert far.window_complete is True

    # 近端信号：ret_5 存在，ret_60 越界 → window_complete=False
    assert near.ret_5 is not None  # 63+5=68 < 70
    assert near.ret_10 is None     # 63+10=73 ≥ 70
    assert near.ret_60 is None
    assert near.window_complete is False


async def test_window_boundary_exact():
    """idx + N == len(bars) 视为越界（需严格 < ）。"""
    bars = _bars(70)
    uc = _make_uc()
    sig = _signal(65, bars)  # 65+5=70 == len → ret_5 越界
    details = uc._build_details(1, "600000", "daily", [sig], bars, date(2024, 1, 1), date(2026, 12, 31))
    assert details[0].ret_5 is None
    assert details[0].window_complete is False


async def test_range_filter_excludes_out_of_range_signals():
    bars = _bars(70)
    uc = _make_uc()
    # 区间只含 idx 30..40 对应日期
    start = bars[30].time.date()
    end = bars[40].time.date()
    sigs = [_signal(10, bars), _signal(35, bars), _signal(60, bars)]
    details = uc._build_details(1, "600000", "daily", sigs, bars, start, end)
    assert len(details) == 1
    assert details[0].signal_time == bars[35].time


# ---------------------------------------------------------------------------
# _aggregate：胜率/平均/中位/盈亏比/note
# ---------------------------------------------------------------------------

def _detail(period: str, stype: str, ret5=None, ret10=None, ret20=None, ret60=None, complete=True):
    from app.domain.entities.backtest import BacktestSignalDetail

    return BacktestSignalDetail(
        report_id=1, stock_code="600000", period=period, signal_type=stype,
        structure_level="segment", signal_time=datetime(2025, 6, 1),
        trigger_price=Decimal(10), ret_5=ret5, ret_10=ret10, ret_20=ret20,
        ret_60=ret60, window_complete=complete,
    )


async def test_aggregate_win_rate_and_note_sample_insufficient():
    uc = _make_uc()
    # 4 条 ret_20：3 正 1 负 → 胜率 0.75；样本 < 10 → sample_insufficient
    details = [
        _detail("daily", "buy1", ret20=Decimal("0.10")),
        _detail("daily", "buy1", ret20=Decimal("0.05")),
        _detail("daily", "buy1", ret20=Decimal("0.20")),
        _detail("daily", "buy1", ret20=Decimal("-0.08")),
    ]
    summaries = uc._aggregate(1, details)
    w20 = next(s for s in summaries if s.window == 20)
    assert w20.sample_count == 4
    assert w20.win_rate == _q6(Decimal("0.75"))
    assert w20.note == "sample_insufficient"
    # avg = (0.10+0.05+0.20-0.08)/4 = 0.0675
    assert w20.avg_return == _q6(Decimal("0.0675"))
    # median of [0.10,0.05,0.20,-0.08] sorted = [-0.08,0.05,0.10,0.20] → (0.05+0.10)/2 = 0.075
    assert w20.median_return == _q6(Decimal("0.075"))


async def test_aggregate_window_incomplete_note():
    uc = _make_uc()
    # 12 条 buy1：ret_60 仅 10 条非空（2 条近期信号越界）→ window=60 样本 < 总数 → window_incomplete
    details = [_detail("daily", "buy1", ret60=Decimal("0.05")) for _ in range(10)]
    details += [_detail("daily", "buy1", ret60=None, complete=False) for _ in range(2)]
    summaries = uc._aggregate(1, details)
    w60 = next(s for s in summaries if s.window == 60)
    assert w60.sample_count == 10  # ≥10 → 非 sample_insufficient
    assert w60.note == "window_incomplete"


async def test_aggregate_profit_loss_ratio():
    uc = _make_uc()
    # 足量样本（12 条）使 note 不为 sample_insufficient；ret_5：盈亏各半
    wins = [Decimal("0.10")] * 6
    losses = [Decimal("-0.05")] * 6
    details = [_detail("daily", "sell1", ret5=w) for w in wins] + [
        _detail("daily", "sell1", ret5=l) for l in losses
    ]
    summaries = uc._aggregate(1, details)
    w5 = next(s for s in summaries if s.window == 5)
    # avg_win=0.10, avg_loss=0.05 → plr=2.0
    assert w5.profit_loss_ratio == _q6(Decimal("2.0"))
    assert w5.note is None  # 12 样本全部有效，无 incomplete


async def test_aggregate_empty_window_yields_zero_sample():
    uc = _make_uc()
    details = [_detail("daily", "buy1", ret60=None, complete=False)]
    summaries = uc._aggregate(1, details)
    w60 = next(s for s in summaries if s.window == 60)
    assert w60.sample_count == 0
    assert w60.note == "window_incomplete"
    assert w60.win_rate is None
