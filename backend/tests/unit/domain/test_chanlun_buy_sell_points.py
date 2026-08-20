"""缠论引擎分层测试（4）：一/二/三类买卖点识别。

用合成确定性序列验证：
- 下降趋势末端底背驰 → 一类买点（buy1）；
- 信号属性合法（status/algo_version/trigger_price/structure_level）；
- 无背驰的平淡序列不误发一类信号。
"""

from datetime import timedelta
from decimal import Decimal

from app.domain.services.chanlun_service import ChanlunService
from tests.fixtures.chanlun_golden_samples import (
    DIVERGENCE_DOWN_POINTS,
    interpolate_points,
    series,
)


def test_buy1_on_downward_divergence():
    """下降趋势末端：第二下跌段创新低 + MACD 绿柱衰减 → 产出一类买点。"""
    bars = interpolate_points(DIVERGENCE_DOWN_POINTS)
    signals, snapshot = ChanlunService.compute_all(bars, "300750", "daily", "1.0.0")

    buy1 = [s for s in signals if s.signal_type == "buy1"]
    assert len(buy1) >= 1, f"期望至少 1 个一类买点，实际信号: {[s.signal_type for s in signals]}"
    sig = buy1[0]
    assert sig.stock_code == "300750"
    assert sig.period == "daily"
    assert sig.status == "confirmed"
    assert sig.structure_level == "segment"
    assert sig.algo_version == "1.0.0"
    assert sig.trigger_price is not None and sig.trigger_price > 0
    # 触发价 ≈ B5 底分型 low（close 30 - spread 0.5）
    assert sig.trigger_price == Decimal("29.5")


def test_confirmed_at_is_right_shoulder_close():
    """确认时刻 = 信号分型右肩 K 线收盘：B5 底（index 37）右肩为 index 38 缓冲 K 线。

    分型须有右侧 K 线才能成立（find_fractals），故 confirmed_at 晚于
    signal_time 一个 K 线周期——尾盘信号要等下一根 K 线收盘才可确认。
    """
    bars = interpolate_points(DIVERGENCE_DOWN_POINTS)
    signals, _ = ChanlunService.compute_all(bars, "300750", "daily", "1.0.0")

    sig = [s for s in signals if s.signal_type == "buy1"][0]
    assert sig.signal_time == bars[37].time  # B5 底分型
    assert sig.confirmed_at == bars[38].time  # 右肩 K 线收盘时刻
    assert sig.confirmed_at == sig.signal_time + timedelta(days=1)


def test_all_signals_confirmed_at_not_before_signal_time():
    """所有信号 confirmed_at >= signal_time（右肩不早于分型中心）。"""
    bars = interpolate_points(DIVERGENCE_DOWN_POINTS)
    signals, _ = ChanlunService.compute_all(bars, "000001", "daily", "1.0.0")
    assert signals, "合成序列应产出信号"
    for s in signals:
        assert s.confirmed_at is not None
        assert s.confirmed_at >= s.signal_time


def test_signal_types_are_legal():
    """所有产出信号的类型必须在合法集合内。"""
    bars = interpolate_points(DIVERGENCE_DOWN_POINTS)
    signals, _ = ChanlunService.compute_all(bars, "000001", "daily", "1.0.0")
    legal = {"buy1", "buy2", "buy3", "sell1", "sell2", "sell3"}
    for s in signals:
        assert s.signal_type in legal


def test_no_signal_on_short_series():
    """数据不足（<5 根）→ 不产出任何信号。"""
    bars = series([10, 8, 6])
    signals, snapshot = ChanlunService.compute_all(bars, "000001", "daily", "1.0.0")
    assert signals == []
    assert snapshot.strokes == []


def test_snapshot_filled_after_compute():
    """compute_all 后结构快照含笔/线段/中枢与 last_kline_time。"""
    bars = interpolate_points(DIVERGENCE_DOWN_POINTS)
    _, snapshot = ChanlunService.compute_all(bars, "300750", "daily", "1.0.0")
    assert snapshot.algo_version == "1.0.0"
    assert snapshot.last_kline_time is not None
    assert len(snapshot.strokes) >= 1  # 已确认笔
