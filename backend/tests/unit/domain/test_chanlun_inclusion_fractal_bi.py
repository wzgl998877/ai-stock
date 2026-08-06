"""缠论引擎分层测试（1）：K 线包含处理 / 顶底分型 / 笔。

基于合成确定性样本（``tests/fixtures/chanlun_golden_samples``）断言。
"""

from decimal import Decimal

from app.domain.entities.chanlun import FractalType
from app.domain.services.chanlun_service import ChanlunService
from tests.fixtures.chanlun_golden_samples import (
    V_SHAPE_CLOSES,
    TWO_WAVE_CLOSES,
    raw_bar,
    series,
)


# ---------------------------------------------------------------------------
# 1. K 线包含处理
# ---------------------------------------------------------------------------

def test_inclusion_merges_contained_bar_down_direction():
    """last 包含 cur 且 close 走低 → 向下合并：取 min(high)/min(low)。"""
    bars = [
        raw_bar(0, 1, o=6, h=10, l=5, c=8),
        raw_bar(1, 2, o=7, h=8, l=7, c=7.5),
    ]
    out = ChanlunService.process_inclusion(bars)
    assert len(out) == 1
    assert out[0].high == Decimal(8)
    assert out[0].low == Decimal(5)


def test_inclusion_merges_contained_bar_up_direction():
    """last 包含 cur 且 close 走高 → 向上合并：取 max(high)/max(low)。"""
    bars = [
        raw_bar(0, 1, o=7, h=10, l=5, c=6),
        raw_bar(1, 2, o=7, h=8, l=6, c=7),  # last 包含 cur：10>=8 and 5<=6
    ]
    out = ChanlunService.process_inclusion(bars)
    assert len(out) == 1
    assert out[0].high == Decimal(10)
    assert out[0].low == Decimal(6)


def test_inclusion_no_merge_for_non_overlapping():
    """相邻 K 不互相包含 → 全部保留。"""
    bars = series([10, 8, 6, 4, 2])
    out = ChanlunService.process_inclusion(bars)
    assert len(out) == 5


def test_inclusion_does_not_mutate_input():
    """包含处理不修改输入对象（纯函数）。"""
    bars = [raw_bar(0, 1, o=6, h=10, l=5, c=8), raw_bar(1, 2, o=7, h=8, l=7, c=7.5)]
    orig_high = bars[0].high
    ChanlunService.process_inclusion(bars)
    assert bars[0].high == orig_high


# ---------------------------------------------------------------------------
# 2. 顶底分型
# ---------------------------------------------------------------------------

def test_find_fractals_v_shape_bottom():
    """V 形序列产生唯一底分型，位置/价格正确。"""
    bars = series(V_SHAPE_CLOSES)  # [10,8,6,4,2,4,6,8,10]
    processed = ChanlunService.process_inclusion(bars)
    fractals = ChanlunService.find_fractals(processed)
    bottoms = [f for f in fractals if f.type == FractalType.BOTTOM]
    assert len(bottoms) == 1
    assert bottoms[0].kline_index == 4
    assert bottoms[0].price == Decimal("1.5")  # close=2 - spread 0.5


def test_find_fractals_inverted_v_top():
    """倒 V 形序列产生唯一顶分型。"""
    bars = series([2, 4, 6, 8, 10, 8, 6, 4, 2])
    processed = ChanlunService.process_inclusion(bars)
    fractals = ChanlunService.find_fractals(processed)
    tops = [f for f in fractals if f.type == FractalType.TOP]
    assert len(tops) == 1
    assert tops[0].kline_index == 4
    assert tops[0].price == Decimal("10.5")


def test_fractals_strictly_alternate():
    """多波序列的分型方向严格交替（顶/底互不相邻）。"""
    bars = series(TWO_WAVE_CLOSES)
    processed = ChanlunService.process_inclusion(bars)
    fractals = ChanlunService.find_fractals(processed)
    assert len(fractals) >= 3
    for i in range(1, len(fractals)):
        assert fractals[i].type != fractals[i - 1].type


# ---------------------------------------------------------------------------
# 3. 笔
# ---------------------------------------------------------------------------

def test_build_bis_alternate_direction_and_count():
    """多波序列产出方向交替的已确认笔，且每笔 K 线数 ≥5。"""
    bars = series(TWO_WAVE_CLOSES)  # 底@4,顶@8,底@12
    processed = ChanlunService.process_inclusion(bars)
    fractals = ChanlunService.find_fractals(processed)
    bis = ChanlunService.build_bis(fractals, processed)

    confirmed = [b for b in bis if b.confirmed]
    assert len(confirmed) == 2  # up(4→8), down(8→12)
    # 方向交替
    assert confirmed[0].direction.value == "up"
    assert confirmed[1].direction.value == "down"
    # 每笔 ≥5 根
    for b in confirmed:
        assert b.kline_count >= 5


def test_build_bis_short_segment_unconfirmed():
    """分型间 K 线不足 5 根 → 标记为未确认（不参与下游）。"""
    # 底@1,顶@3,底@5：分型间距 2 根 <5
    bars = series([4, 2, 6, 2, 6, 2, 6])
    processed = ChanlunService.process_inclusion(bars)
    fractals = ChanlunService.find_fractals(processed)
    bis = ChanlunService.build_bis(fractals, processed)
    # 距离均 <5 → 全部 unconfirmed
    assert all(not b.confirmed for b in bis)
