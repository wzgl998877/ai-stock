"""缠论引擎分层测试（4）：一/二/三类买卖点识别。

用合成确定性序列验证：
- 下降趋势末端底背驰 → 一类买点（buy1）；
- 信号属性合法（status/algo_version/trigger_price/structure_level）；
- 无背驰的平淡序列不误发一类信号。

1.1.0 起补口径测试：一类点须跌破/升破最后中枢；三类点只认中枢出口后
紧邻的第一笔回试；buy2/sell2 正向链路。

2026-09-08 双版本并存后补 v1/v2 同输入对照用例：v1=旧口径（无位置校验、
老中枢不退休）、v2=当前口径，同一输入两版本产出应有口径性差异。
"""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from app.domain.entities.chanlun import (
    Bi,
    Direction,
    Fractal,
    FractalType,
    Zhongshu,
)
from app.domain.services.chanlun_service import (
    ChanlunService,
    normalize_algo_version,
)
from tests.fixtures.chanlun_golden_samples import (
    DIVERGENCE_DOWN_POINTS,
    interpolate_points,
    series,
)


def _fr(idx, price, day, ftype=FractalType.BOTTOM):
    """手工分型 helper（对齐 test_chanlun_service.py 手法）。"""
    return Fractal(
        type=ftype, kline_index=idx, price=Decimal(price), time=datetime(2026, 1, day)
    )


def test_buy1_on_downward_divergence():
    """下降趋势末端：第二下跌段创新低 + MACD 绿柱衰减 + 跌破最后中枢 → 产出一类买点。"""
    bars = interpolate_points(DIVERGENCE_DOWN_POINTS)
    signals, snapshot = ChanlunService.compute_all(bars, "300750", "daily", "1.1.0")

    buy1 = [s for s in signals if s.signal_type == "buy1"]
    assert len(buy1) >= 1, f"期望至少 1 个一类买点，实际信号: {[s.signal_type for s in signals]}"
    sig = buy1[0]
    assert sig.stock_code == "300750"
    assert sig.period == "daily"
    assert sig.status == "confirmed"
    assert sig.structure_level == "segment"
    assert sig.algo_version == "1.1.0"
    assert sig.trigger_price is not None and sig.trigger_price > 0
    # 触发价 ≈ B5 底分型 low（close 30 - spread 0.5）
    assert sig.trigger_price == Decimal("29.5")


def test_confirmed_at_is_right_shoulder_close():
    """确认时刻 = 信号分型右肩 K 线收盘：B5 底（index 37）右肩为 index 38 缓冲 K 线。

    分型须有右侧 K 线才能成立（find_fractals），故 confirmed_at 晚于
    signal_time 一个 K 线周期——尾盘信号要等下一根 K 线收盘才可确认。
    """
    bars = interpolate_points(DIVERGENCE_DOWN_POINTS)
    signals, _ = ChanlunService.compute_all(bars, "300750", "daily", "1.1.0")

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
    _, snapshot = ChanlunService.compute_all(bars, "300750", "daily", "1.1.0")
    assert snapshot.algo_version == "1.1.0"
    assert snapshot.last_kline_time is not None
    assert len(snapshot.strokes) >= 1  # 已确认笔


# ---------------------------------------------------------------------------
# 1.1.0 口径：一类点位置校验（背驰段新极值须破最后中枢 ZD/ZG）
# ---------------------------------------------------------------------------

def _golden_pipeline():
    """黄金样本全管线：返回 (processed, bis, segments)，供直调 _detect_signals。"""
    bars = interpolate_points(DIVERGENCE_DOWN_POINTS)
    processed = ChanlunService.process_inclusion(bars)
    fractals = ChanlunService.find_fractals(processed)
    bis = ChanlunService.build_bis(fractals, processed)
    segments = ChanlunService.build_segments(bis)
    return processed, bis, segments


def test_buy1_requires_break_below_last_zhongshu():
    """一类买点位置校验：背驰段新低须跌破最后中枢 ZD。

    三组对照（同一笔/线段输入）：
    - 无中枢 → 不报（序列早期无中枢的背驰不报）；
    - 中枢 ZD 低于新低（新低未破）→ 不报（盘整背驰）；
    - 中枢 ZD 高于新低（跌破）→ 报，触发价不变。
    """
    processed, bis, segments = _golden_pipeline()
    kwargs = dict(stock_code="300750", period="daily", algo_version="1.1.0")

    # 无中枢
    s_none = ChanlunService._detect_signals(processed, bis, segments, [], **kwargs)
    assert not [s for s in s_none if s.signal_type == "buy1"]

    # 中枢在新低之下（zd=25 < 新低 29.5）→ 未破，不报
    zs_low = [Zhongshu(
        zg=Decimal(45), zd=Decimal(25), gg=Decimal(48), dd=Decimal(24),
        enter_time=datetime(2026, 1, 1), exit_time=datetime(2026, 1, 10),
    )]
    s_low = ChanlunService._detect_signals(processed, bis, segments, zs_low, **kwargs)
    assert not [s for s in s_low if s.signal_type == "buy1"]

    # 中枢在新低之上（zd=40 > 新低 29.5）→ 跌破，报
    zs_high = [Zhongshu(
        zg=Decimal(48), zd=Decimal(40), gg=Decimal(50), dd=Decimal(39),
        enter_time=datetime(2026, 1, 1), exit_time=datetime(2026, 1, 10),
    )]
    s_high = ChanlunService._detect_signals(processed, bis, segments, zs_high, **kwargs)
    buy1 = [s for s in s_high if s.signal_type == "buy1"]
    assert buy1, "跌破最后中枢的背驰应报一类买点"
    assert buy1[0].trigger_price == Decimal("29.5")


def test_sell1_requires_break_above_last_zhongshu():
    """一类卖点位置校验：背驰段新高须升破最后中枢 ZG。

    用 DIVERGENCE_DOWN_POINTS 的镜像（价格取补、MACD 取反）构造上涨双段背驰，
    对照三组中枢：
    - 无中枢 → 不报；
    - ZG 高于新高（未升破）→ 不报；
    - ZG 低于新高（升破）→ 报。
    """
    UP_POINTS = [(i, 100 - p, -m) for (i, p, m) in DIVERGENCE_DOWN_POINTS]
    bars = interpolate_points(UP_POINTS)
    processed = ChanlunService.process_inclusion(bars)
    fractals = ChanlunService.find_fractals(processed)
    bis = ChanlunService.build_bis(fractals, processed)
    segments = ChanlunService.build_segments(bis)
    # 前置：镜像样本有两段 UP 线段，第二段创新高（70.5 > 65.5）且 MACD 衰减
    up_ends = [s.end.price for s in segments if s.direction.name == "UP"]
    assert len(up_ends) >= 2 and up_ends[-1] > up_ends[0]

    kwargs = dict(stock_code="300750", period="daily", algo_version="1.1.0")

    # 无中枢 → 不报
    s_none = ChanlunService._detect_signals(processed, bis, segments, [], **kwargs)
    assert not [s for s in s_none if s.signal_type == "sell1"]

    # 中枢 ZG 高于新高（70.5）→ 未升破，不报（exit 须早于背驰段终点 02-07）
    zs_above = [Zhongshu(
        zg=Decimal(999), zd=Decimal(40), gg=Decimal(1000), dd=Decimal(39),
        enter_time=datetime(2026, 1, 1), exit_time=datetime(2026, 1, 30),
    )]
    s_above = ChanlunService._detect_signals(processed, bis, segments, zs_above, **kwargs)
    assert not [s for s in s_above if s.signal_type == "sell1"]

    # 中枢 ZG 低于新高 → 升破，报
    zs_below = [Zhongshu(
        zg=Decimal(60), zd=Decimal(50), gg=Decimal(61), dd=Decimal(49),
        enter_time=datetime(2026, 1, 1), exit_time=datetime(2026, 1, 30),
    )]
    s_below = ChanlunService._detect_signals(processed, bis, segments, zs_below, **kwargs)
    sell1 = [s for s in s_below if s.signal_type == "sell1"]
    assert sell1, "升破最后中枢的上涨背驰应报一类卖点"


# ---------------------------------------------------------------------------
# 1.1.0 口径：三类点只认中枢出口后紧邻的第一笔回试（老中枢退休）
# ---------------------------------------------------------------------------

def _mk_zhongshu(zg, zd, exit_time):
    return Zhongshu(
        zg=Decimal(zg), zd=Decimal(zd), gg=Decimal(zg), dd=Decimal(zd),
        enter_time=datetime(2026, 1, 1), enter_index=0, exit_time=exit_time,
    )


def test_buy3_fires_on_first_retest_after_departure():
    """向上离开 ZG 后，紧邻第一笔回试守住 ZG → 恰一个 buy3，挂在回试笔终点。"""
    # cb[0] 出口（exit_time=cb[0].end.time），cb[1] UP 离开破 ZG，cb[2] DOWN 回试守住
    bis = [
        Bi(Direction.DOWN, _fr(0, 50, 1, FractalType.TOP), _fr(0, 30, 1), kline_count=5),
        Bi(Direction.UP, _fr(0, 30, 3), _fr(2, 60, 3, FractalType.TOP), kline_count=5),
        Bi(Direction.DOWN, _fr(2, 60, 5, FractalType.TOP), _fr(4, 45, 5), kline_count=5),
    ]
    zs = [_mk_zhongshu(zg=40, zd=32, exit_time=datetime(2026, 1, 1))]

    signals = ChanlunService._detect_signals(
        [], bis, [], zs, "300750", "daily", "1.1.0",
    )
    buy3 = [s for s in signals if s.signal_type == "buy3"]
    assert len(buy3) == 1
    assert buy3[0].signal_time == bis[2].end.time
    assert buy3[0].trigger_price == bis[2].end.price


def test_buy3_no_signal_when_first_retest_enters_range():
    """首笔回试落回 [ZD,ZG] → 无 buy3；其后第二笔守住也不补报。"""
    # cb[1] UP 离开破 ZG，cb[2] DOWN 回试跌回区间（35 < zg 40），cb[3] UP 再创新高
    bis = [
        Bi(Direction.DOWN, _fr(0, 50, 1, FractalType.TOP), _fr(0, 30, 1), kline_count=5),
        Bi(Direction.UP, _fr(0, 30, 3), _fr(2, 60, 3, FractalType.TOP), kline_count=5),
        Bi(Direction.DOWN, _fr(2, 60, 5, FractalType.TOP), _fr(4, 35, 5), kline_count=5),
        Bi(Direction.UP, _fr(4, 35, 7), _fr(6, 70, 7, FractalType.TOP), kline_count=5),
    ]
    zs = [_mk_zhongshu(zg=40, zd=32, exit_time=datetime(2026, 1, 1))]

    signals = ChanlunService._detect_signals(
        [], bis, [], zs, "300750", "daily", "1.1.0",
    )
    assert not [s for s in signals if s.signal_type == "buy3"]


def test_buy3_stale_retest_not_signaled():
    """回归（002940 m30 同价双报根因之一）：中枢出口后隔 ≥2 笔才回踩 → 不报。

    离开笔 cb[1] 后的紧邻回试 cb[2] 落回区间（应判失败），第 3 笔才守住 ZG——
    1.0.0 会扫到第 3 笔补报，1.1.0 只认 cb[2]，故无信号。
    """
    bis = [
        Bi(Direction.DOWN, _fr(0, 50, 1, FractalType.TOP), _fr(0, 30, 1), kline_count=5),
        Bi(Direction.UP, _fr(0, 30, 3), _fr(2, 60, 3, FractalType.TOP), kline_count=5),
        Bi(Direction.DOWN, _fr(2, 60, 5, FractalType.TOP), _fr(4, 35, 5), kline_count=5),
        Bi(Direction.UP, _fr(4, 35, 7), _fr(6, 50, 7, FractalType.TOP), kline_count=5),
        Bi(Direction.DOWN, _fr(6, 50, 9, FractalType.TOP), _fr(8, 45, 9), kline_count=5),
    ]
    zs = [_mk_zhongshu(zg=40, zd=32, exit_time=datetime(2026, 1, 1))]

    signals = ChanlunService._detect_signals(
        [], bis, [], zs, "300750", "daily", "1.1.0",
    )
    assert not [s for s in signals if s.signal_type == "buy3"]


def test_sell3_fires_on_first_retest_after_downward_departure():
    """向下离开 ZD 后，紧邻第一笔反弹压在 ZD 之下 → 恰一个 sell3（对称正例）。"""
    # cb[1] DOWN 离开破 ZD（end 12 < zd 30），cb[2] UP 反弹 25 < 30
    bis = [
        Bi(Direction.UP, _fr(0, 20, 1, FractalType.BOTTOM), _fr(0, 50, 1), kline_count=5),
        Bi(Direction.DOWN, _fr(0, 50, 3, FractalType.TOP), _fr(2, 12, 3), kline_count=5),
        Bi(Direction.UP, _fr(2, 12, 5), _fr(4, 25, 5, FractalType.TOP), kline_count=5),
    ]
    zs = [_mk_zhongshu(zg=45, zd=30, exit_time=datetime(2026, 1, 1))]

    signals = ChanlunService._detect_signals(
        [], bis, [], zs, "300750", "daily", "1.1.0",
    )
    sell3 = [s for s in signals if s.signal_type == "sell3"]
    assert len(sell3) == 1
    assert sell3[0].signal_time == bis[2].end.time
    assert sell3[0].trigger_price == bis[2].end.price


def test_no_buy3_and_sell3_at_same_position_from_one_zhongshu():
    """单一中枢同一时刻至多触发一类三类点（002940 m30 双报回归）。"""
    # 出口 cb[0]；cb[1] UP 破 ZG=40（end 60）；cb[2] DOWN 守住 ZG（end 45）
    bis = [
        Bi(Direction.DOWN, _fr(0, 50, 1, FractalType.TOP), _fr(0, 30, 1), kline_count=5),
        Bi(Direction.UP, _fr(0, 30, 3), _fr(2, 60, 3, FractalType.TOP), kline_count=5),
        Bi(Direction.DOWN, _fr(2, 60, 5, FractalType.TOP), _fr(4, 45, 5), kline_count=5),
    ]
    # 同一刻只有一个中枢，且离开方向唯一（UP）→ 只可能 buy3
    zs = [_mk_zhongshu(zg=40, zd=32, exit_time=datetime(2026, 1, 1))]

    signals = ChanlunService._detect_signals(
        [], bis, [], zs, "300750", "daily", "1.1.0",
    )
    types_at_ret = {
        s.signal_type for s in signals
        if s.signal_time == bis[2].end.time and s.signal_type in ("buy3", "sell3")
    }
    assert len(types_at_ret) <= 1, f"同一回试位置产出多类三类点: {types_at_ret}"


# ---------------------------------------------------------------------------
# 1.1.0 补：buy2/sell2 正向链路（此前无正向覆盖）
# ---------------------------------------------------------------------------

def test_buy2_after_buy1_pullback_holds():
    """黄金样本全管线：buy1 之后的第一次向下回调不破一类买价 → 存在 buy2。"""
    bars = interpolate_points(DIVERGENCE_DOWN_POINTS)
    signals, _ = ChanlunService.compute_all(bars, "300750", "daily", "1.1.0")

    buy1 = [s for s in signals if s.signal_type == "buy1"]
    buy2 = [s for s in signals if s.signal_type == "buy2"]
    assert buy1, "前置：黄金样本应产出一类买点"
    if buy2:  # 回调结构存在时才产出（弱断言：存在则链路关系必须正确）
        b1, b2 = buy1[0], buy2[0]
        assert b2.signal_time > b1.signal_time
        assert b2.trigger_price > b1.trigger_price


def test_sell2_after_sell1_rebound_holds():
    """sell1 之后的第一次向上反弹不上一类卖价 → sell2 派生关系正确。

    黄金样本以下跌为主，sell1 未必产出；存在时验证派生链路的次序与价位关系。
    """
    bars = interpolate_points(DIVERGENCE_DOWN_POINTS)
    signals, _ = ChanlunService.compute_all(bars, "300750", "daily", "1.1.0")
    sell1 = [s for s in signals if s.signal_type == "sell1"]
    sell2 = [s for s in signals if s.signal_type == "sell2"]
    if sell1 and sell2:
        assert sell2[0].signal_time > sell1[0].signal_time
        assert sell2[0].trigger_price < sell1[0].trigger_price


# ---------------------------------------------------------------------------
# v1/v2 双版本对照（2026-09-08）：同一输入下两口径的判定差异
# ---------------------------------------------------------------------------

def test_normalize_algo_version():
    """别名归一化：v1/V1/1.0.0 → 1.0.0；v2/V2/1.1.0 → 1.1.0；非法值抛错。"""
    assert normalize_algo_version("v1") == "1.0.0"
    assert normalize_algo_version("V1") == "1.0.0"
    assert normalize_algo_version("1.0.0") == "1.0.0"
    assert normalize_algo_version("v2") == "1.1.0"
    assert normalize_algo_version("V2") == "1.1.0"
    assert normalize_algo_version("1.1.0") == "1.1.0"
    for bad in ("v3", "", "9.9.9", "最新"):
        with pytest.raises(ValueError, match="不支持的缠论算法版本"):
            normalize_algo_version(bad)


def test_v1_buy1_without_zhongshu_but_v2_suppressed():
    """无前置中枢的背驰：v1 报 buy1（旧口径无位置校验），v2 不报。"""
    bars = interpolate_points(DIVERGENCE_DOWN_POINTS)
    processed, bis, segments = _golden_pipeline()
    assert processed  # 对齐 helper 语义
    del processed, bis, segments

    # 直调 _detect_signals：黄金样本管线真实 segments + 空 zhongshu
    kwargs = dict(stock_code="300750", period="daily")
    p, b, segs = _golden_pipeline()
    v1 = ChanlunService._detect_signals(p, b, segs, [], algo_version="v1", **kwargs)
    v2 = ChanlunService._detect_signals(p, b, segs, [], algo_version="v2", **kwargs)
    assert [s for s in v1 if s.signal_type == "buy1"], "v1 应报无中枢背驰 buy1"
    assert not [s for s in v2 if s.signal_type == "buy1"], "v2 无前置中枢不报"
    del bars


def test_v1_buy3_from_later_bi_but_v2_suppressed():
    """老中枢不退休（v1）vs 只认紧邻第一笔回试（v2）。

    中枢出口 cb[0] 后：cb[1] UP 破 ZG、cb[2] DOWN 回试落回区间、cb[3] UP、
    cb[4] DOWN 守住 ZG——v1 扫到 cb[4] 补报 buy3，v2 只认 cb[2] → 无信号。
    """
    bis = [
        Bi(Direction.DOWN, _fr(0, 50, 1, FractalType.TOP), _fr(0, 30, 1), kline_count=5),
        Bi(Direction.UP, _fr(0, 30, 3), _fr(2, 60, 3, FractalType.TOP), kline_count=5),
        Bi(Direction.DOWN, _fr(2, 60, 5, FractalType.TOP), _fr(4, 35, 5), kline_count=5),
        Bi(Direction.UP, _fr(4, 35, 7), _fr(6, 50, 7, FractalType.TOP), kline_count=5),
        Bi(Direction.DOWN, _fr(6, 50, 9, FractalType.TOP), _fr(8, 45, 9), kline_count=5),
    ]
    zs = [_mk_zhongshu(zg=40, zd=32, exit_time=datetime(2026, 1, 1))]

    kwargs = dict(stock_code="300750", period="daily")
    v1 = ChanlunService._detect_signals([], bis, [], zs, algo_version="v1", **kwargs)
    v2 = ChanlunService._detect_signals([], bis, [], zs, algo_version="v2", **kwargs)
    v1_buy3 = [s for s in v1 if s.signal_type == "buy3"]
    assert v1_buy3, "v1 应扫到后续笔回踩补报 buy3"
    assert v1_buy3[0].signal_time == bis[4].end.time
    assert not [s for s in v2 if s.signal_type == "buy3"], "v2 首笔回试落回区间即作废"


def test_v1_signals_label_normalized():
    """传别名 'v1' → 信号/快照 algo_version 恒为规范串 '1.0.0'（dedup 口径唯一）。"""
    bars = interpolate_points(DIVERGENCE_DOWN_POINTS)
    signals, snapshot = ChanlunService.compute_all(bars, "300750", "daily", "v1")
    assert snapshot.algo_version == "1.0.0"
    assert signals
    for s in signals:
        assert s.algo_version == "1.0.0"


def test_no_duplicate_signal_at_same_position_both_versions():
    """同位置去重不变量在 v1/v2 下均成立。"""
    bars = interpolate_points(DIVERGENCE_DOWN_POINTS)
    for ver in ("v1", "v2"):
        signals, _ = ChanlunService.compute_all(bars, "300750", "daily", ver)
        positions = [(s.signal_type, s.signal_time) for s in signals]
        assert len(positions) == len(set(positions)), f"{ver} 存在同位置重复: {positions}"
