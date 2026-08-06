"""缠论引擎分层测试（2）：线段（特征序列法）/ 中枢 [ZD,ZG]。"""

from decimal import Decimal

from app.domain.entities.chanlun import Direction
from app.domain.services.chanlun_service import ChanlunService
from tests.fixtures.chanlun_golden_samples import series


# 长震荡序列：顶@5/底@10/顶@15/底@20/顶@24，产出 4 笔 + 1 中枢 + 1 下跌线段
OSCILLATION_CLOSES = [
    8, 9, 10, 11, 12, 13,       # → 顶 @5
    11, 9, 7, 5, 3,             # → 底 @10
    5, 7, 9, 11, 13,            # → 顶 @15
    11, 9, 7, 5, 3,             # → 底 @20
    5, 7, 9, 11, 13,            # → 顶 @24
    12,                         # 缓冲（避免端点极值）
]


def _structure(closes):
    bars = series(closes)
    processed = ChanlunService.process_inclusion(bars)
    fractals = ChanlunService.find_fractals(processed)
    bis = ChanlunService.build_bis(fractals, processed)
    segments = ChanlunService.build_segments(bis)
    zhongshu = ChanlunService.find_zhongshu(bis)
    return bis, segments, zhongshu


def test_segment_requires_at_least_three_bis():
    """笔数 <3 时不产生线段。"""
    bars = series([10, 8, 6, 4, 2, 4, 6, 8, 10])  # 仅 1 笔
    processed = ChanlunService.process_inclusion(bars)
    fractals = ChanlunService.find_fractals(processed)
    bis = ChanlunService.build_bis(fractals, processed)
    segments = ChanlunService.build_segments(bis)
    assert segments == []


def test_oscillation_produces_one_downward_segment():
    bis, segments, zhongshu = _structure(OSCILLATION_CLOSES)
    assert len([b for b in bis if b.confirmed]) == 4
    assert len(segments) >= 1
    assert segments[0].direction == Direction.DOWN
    assert segments[0].bi_count >= 3


def test_zhongshu_invariants_hold():
    """中枢不变量：DD ≤ ZD ≤ ZG ≤ GG。"""
    _, _, zhongshu = _structure(OSCILLATION_CLOSES)
    assert len(zhongshu) == 1
    zs = zhongshu[0]
    assert zs.dd <= zs.zd
    assert zs.zd <= zs.zg
    assert zs.zg <= zs.gg
    assert zs.enter_time is not None
    assert zs.exit_time is not None


def test_zhongshu_non_overlapping_bis_no_formation():
    """单调序列无重叠笔 → 不形成中枢。"""
    bars = series([2, 4, 6, 8, 10, 12, 14, 16, 18])  # 单调上升，无分型
    processed = ChanlunService.process_inclusion(bars)
    fractals = ChanlunService.find_fractals(processed)
    bis = ChanlunService.build_bis(fractals, processed)
    zhongshu = ChanlunService.find_zhongshu(bis)
    assert zhongshu == []
