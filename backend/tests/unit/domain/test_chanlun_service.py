"""缠论引擎汇总测试（T015）：横切不变量。

验证引擎在「算法版本内嵌、确定性/幂等、未收盘不重绘、同位置信号去重」四个
横切属性上的契约（与 ``chanlun_service.py`` 模块 docstring 声明一致）。
"""

from decimal import Decimal

import pytest

from app.domain.entities.chanlun import ChanlunSignal
from app.domain.services.chanlun_service import ChanlunService
from tests.fixtures.chanlun_golden_samples import (
    DIVERGENCE_DOWN_POINTS,
    TWO_WAVE_CLOSES,
    bar,
    interpolate_points,
    raw_bar,
    series,
)


def test_algo_version_embedded_in_signals_and_snapshot():
    """传入的 algo_version 必须内嵌到每条信号与结构快照（口径可追溯）。

    1.1.0 起版本受支持集约束（v1/v2 双口径并存），自定义串不再合法；
    别名 v1/v2 归一化为规范串后内嵌。
    """
    bars = interpolate_points(DIVERGENCE_DOWN_POINTS)
    signals, snapshot = ChanlunService.compute_all(bars, "300750", "daily", algo_version="v1")

    assert snapshot.algo_version == "1.0.0"
    assert len(signals) >= 1
    for s in signals:
        assert s.algo_version == "1.0.0"

    with pytest.raises(ValueError, match="不支持的缠论算法版本"):
        ChanlunService.compute_all(bars, "300750", "daily", algo_version="2.1.3")


def test_compute_all_is_deterministic_and_idempotent():
    """同一输入两次计算结果恒等（确定性 + 幂等基础）。"""
    bars = interpolate_points(DIVERGENCE_DOWN_POINTS)
    s1, snap1 = ChanlunService.compute_all(bars, "300750", "daily", "1.0.0")
    s2, snap2 = ChanlunService.compute_all(bars, "300750", "daily", "1.0.0")

    norm1 = [(s.signal_type, s.signal_time, s.trigger_price) for s in s1]
    norm2 = [(s.signal_type, s.signal_time, s.trigger_price) for s in s2]
    assert norm1 == norm2
    assert snap1.last_kline_time == snap2.last_kline_time
    assert len(snap1.strokes) == len(snap2.strokes)


def test_confirmed_signal_not_replayed_when_tail_extends():
    """收盘确认不重绘：尾部追加一根未形成新结构的 K 线，已确认信号不变。

    引擎接收的必须是「已剔除未收盘 K 线」的序列（UseCase 职责）。此处验证：
    即便尾部多一根 K 线（模拟新收盘但未改变既有结构），此前已确认的一类买点
    的触发价/时间不被重绘。
    """
    bars = interpolate_points(DIVERGENCE_DOWN_POINTS)
    signals_before, _ = ChanlunService.compute_all(bars, "300750", "daily", "1.0.0")
    buy1_before = [s for s in signals_before if s.signal_type == "buy1"]
    assert buy1_before, "前置：原序列应已产出一类买点"

    # 末尾追加一根延续缓冲方向的 K 线（close=32，不形成新分型、不改变既有笔）
    last = bars[-1]
    bars_ext = bars + [bar(len(bars), len(bars) + 1, 32, macd=0.3)]
    signals_after, _ = ChanlunService.compute_all(bars_ext, "300750", "daily", "1.0.0")
    buy1_after = [s for s in signals_after if s.signal_type == "buy1"]

    assert len(buy1_after) >= len(buy1_before)
    # 原一类买点（按时间）的触发价/时间保持不变
    before_map = {(s.signal_time, s.trigger_price) for s in buy1_before}
    after_map = {(s.signal_time, s.trigger_price) for s in buy1_after}
    assert before_map.issubset(after_map)
    assert last  # 仅用于消除未用变量告警


def test_no_duplicate_signal_at_same_position():
    """同一 (signal_type, signal_time) 位置不得产出重复信号。"""
    bars = interpolate_points(DIVERGENCE_DOWN_POINTS)
    signals, _ = ChanlunService.compute_all(bars, "300750", "daily", "1.0.0")

    positions = [(s.signal_type, s.signal_time) for s in signals]
    assert len(positions) == len(set(positions)), f"存在同位置重复信号: {positions}"


def test_no_duplicate_signal_when_multiple_zhongshu_hit_same_bar():
    """多中枢在同一根 K 线回试触发同类买卖点时，不得产出重复信号。

    复现回测 IntegrityError 根因：``_detect_signals`` 三类买卖点外层遍历所有中枢，
    多个中枢的回试可能落到同一根回调 K 线（同 signal_time），修复前会产出
    重复 (signal_type, signal_time)。直接喂数据给 ``_detect_signals`` 隔离验证。

    1.1.0 起三类点只认中枢出口后的紧邻第一笔回试：``exit_time`` 必须对齐
    ``cb[j].end.time`` 才能反解出口笔下标，两个中枢出口同刻 → 仍同刻触发。
    """
    from datetime import datetime
    from decimal import Decimal

    from app.domain.entities.chanlun import Bi, Direction, Fractal, FractalType, Zhongshu

    def _fr(idx, price, day, ftype=FractalType.BOTTOM):
        return Fractal(
            type=ftype, kline_index=idx, price=Decimal(price), time=datetime(2026, 1, day)
        )

    # cb：down(5) → up(8) → down(10) → up(20)，已确认笔（confirmed 默认 True）
    bis = [
        Bi(Direction.DOWN, _fr(0, 8, 1, FractalType.TOP), _fr(0, 5, 1), kline_count=5),
        Bi(Direction.UP, _fr(0, 5, 3), _fr(2, 8, 3, FractalType.TOP), kline_count=5),
        Bi(Direction.DOWN, _fr(2, 8, 5, FractalType.TOP), _fr(4, 10, 5), kline_count=5),
        Bi(Direction.UP, _fr(4, 10, 7), _fr(6, 20, 7, FractalType.TOP), kline_count=5),
    ]
    # 两个中枢出口均为 cb[1]（exit_time=cb[1].end.time=1月3日）：
    # 离开笔 cb[2]（DOWN，end 10 < zd 25）、回试笔 cb[3]（UP，end 20 < 25）
    # → 两个中枢都在 cb[3] 触发 sell3（同 signal_time）
    zhongshu = [
        Zhongshu(zg=Decimal(30), zd=Decimal(25), gg=Decimal(35), dd=Decimal(20),
                 enter_time=datetime(2026, 1, 1), enter_index=0,
                 exit_time=datetime(2026, 1, 3)),
        Zhongshu(zg=Decimal(30), zd=Decimal(25), gg=Decimal(35), dd=Decimal(20),
                 enter_time=datetime(2026, 1, 1), enter_index=0,
                 exit_time=datetime(2026, 1, 3)),
    ]

    signals = ChanlunService._detect_signals(
        [], bis, [], zhongshu, "000636", "daily", "1.0.0",
    )

    sell3 = [s for s in signals if s.signal_type == "sell3"]
    assert sell3, "前置：多中枢同根 K 线回试应产出 sell3（否则测试无效）"
    positions = [(s.signal_type, s.signal_time) for s in signals]
    assert len(positions) == len(set(positions)), f"存在同位置重复信号: {positions}"


def test_dedup_key_stable_and_distinguishes_position():
    """make_dedup_key 对相同位置稳定、对位置变化敏感（幂等落库依据）。"""
    bars = interpolate_points(DIVERGENCE_DOWN_POINTS)
    signals, _ = ChanlunService.compute_all(bars, "300750", "daily", "1.0.0")
    assert signals, "前置：应有信号"
    anchor_time = signals[0].signal_time

    # 引擎产出的信号反复生成 dedup_key 应稳定
    keys1 = [s.make_dedup_key() for s in signals]
    keys2 = [s.make_dedup_key() for s in signals]
    assert keys1 == keys2
    # 引擎不应在同一次产出中给出重复 key
    assert len(set(keys1)) == len(keys1)

    # 显式构造：相同位置 → 同 key；改 signal_type/algo_version → 不同 key
    base = ChanlunSignal(
        stock_code="300750", period="daily", signal_type="buy1",
        structure_level="segment", signal_time=anchor_time,
        algo_version="1.0.0",
    )
    twin = ChanlunSignal(
        stock_code="300750", period="daily", signal_type="buy1",
        structure_level="segment", signal_time=anchor_time,
        algo_version="1.0.0",
    )
    assert base.make_dedup_key() == twin.make_dedup_key()

    other_type = ChanlunSignal(
        stock_code="300750", period="daily", signal_type="buy2",
        structure_level="segment", signal_time=anchor_time,
        algo_version="1.0.0",
    )
    other_version = ChanlunSignal(
        stock_code="300750", period="daily", signal_type="buy1",
        structure_level="segment", signal_time=anchor_time,
        algo_version="2.0.0",
    )
    assert base.make_dedup_key() != other_type.make_dedup_key()
    assert base.make_dedup_key() != other_version.make_dedup_key()
    # structure_level 不参与 dedup_key（同位置不同 level 视为同一信号幂等键）
    other_level = ChanlunSignal(
        stock_code="300750", period="daily", signal_type="buy1",
        structure_level="stroke", signal_time=anchor_time,
        algo_version="1.0.0",
    )
    assert base.make_dedup_key() == other_level.make_dedup_key()


def test_short_series_returns_empty_without_raising():
    """空/极短序列不应抛异常，返回空信号 + 仅含基本字段的快照。"""
    for seq in ([], series([10, 8]), series([10, 8, 6, 4])):
        signals, snapshot = ChanlunService.compute_all(seq, "000001", "daily", "1.0.0")
        assert signals == []
        assert snapshot.strokes == []
        assert snapshot.segments == []
        assert snapshot.zhongshu == []
        assert snapshot.algo_version == "1.0.0"


def test_snapshot_watermark_is_last_input_bar_even_if_merged_by_inclusion():
    """回归（2026-09-02 生产）：快照水位线必须取原始输入末根时间。

    末根 K 线被包含合并吞掉时（合并保留组首 time），若取合并后序列末根
    time，水位线早于库中最新 K 线 → 监控层 ``_is_stale`` 的相等比较永不
    命中，该股每次扫描都被判"有新数据"空转重算（生产 17/37 只 m30、
    13/37 只日线长年空转，且重算后水位仍停在合并组起点）。
    """
    # 两波完整结构保证 len(bars) >= MIN_BI_KLINES 进入正式计算；
    # 末尾追加一根被前根包含的 K 线（前根 high=10.5/low=9.5 完全罩住它）
    bars = series(TWO_WAVE_CLOSES)
    assert bars[-1].high == Decimal("10.5") and bars[-1].low == Decimal("9.5")
    bars.append(raw_bar(len(bars), len(bars) + 1, 10, 10.3, 9.7, 10))

    _, snapshot = ChanlunService.compute_all(bars, "300750", "daily", "1.0.0")

    # 水位线 = 原始输入末根时间（= bars[-1].time），而非合并组首
    assert snapshot.last_kline_time == bars[-1].time
