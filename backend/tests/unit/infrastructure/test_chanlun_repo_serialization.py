"""缠论 Repository 结构序列化往返测试（T019 配套）。

``MySQLChanlunRepository`` 的 IO 部分由集成测试覆盖；本测试聚焦其模块级
序列化纯函数（``_bi_to_dict``/``_segment_to_dict``/``_zhongshu_to_dict`` 及反向），
验证 ``Decimal``/``datetime``/``Enum`` 经 JSON 化往返后等价（落库/读库一致性基础）。
"""

import json
from datetime import datetime
from decimal import Decimal

from app.domain.entities.chanlun import Bi, Direction, Fractal, FractalType
from app.domain.services.chanlun_service import ChanlunService
from app.infrastructure.repositories.mysql_chanlun_repo import (
    _bi_from_dict,
    _bi_to_dict,
    _segment_from_dict,
    _segment_to_dict,
    _zhongshu_from_dict,
    _zhongshu_to_dict,
)
from tests.fixtures.chanlun_golden_samples import (
    DIVERGENCE_DOWN_POINTS,
    interpolate_points,
)


def _snapshot_structures():
    """用引擎产出真实结构（笔/线段/中枢）作为序列化样本。"""
    bars = interpolate_points(DIVERGENCE_DOWN_POINTS)
    _, snapshot = ChanlunService.compute_all(bars, "300750", "daily", "1.0.0")
    assert snapshot.strokes, "前置：引擎应产出已确认笔"
    return snapshot


def test_bi_roundtrip_preserves_all_fields():
    snap = _snapshot_structures()
    for bi in snap.strokes:
        d = _bi_to_dict(bi)
        # 必须可 JSON 序列化（落库为 JSON 列）
        s = json.dumps(d, ensure_ascii=False)
        back = _bi_from_dict(json.loads(s))
        assert back.direction == bi.direction
        assert back.kline_count == bi.kline_count
        assert back.confirmed == bi.confirmed
        assert back.start.type == bi.start.type
        assert back.start.kline_index == bi.start.kline_index
        assert back.start.price == bi.start.price            # Decimal 等价
        assert back.start.time == bi.start.time              # datetime 等价
        assert back.end.price == bi.end.price
        assert back.end.time == bi.end.time


def test_segment_roundtrip_preserves_all_fields():
    snap = _snapshot_structures()
    if not snap.segments:
        return
    for seg in snap.segments:
        d = _segment_to_dict(seg)
        back = _segment_from_dict(json.loads(json.dumps(d, ensure_ascii=False)))
        assert back.direction == seg.direction
        assert back.bi_count == seg.bi_count
        assert back.confirmed == seg.confirmed
        assert back.break_type == seg.break_type
        assert back.start.price == seg.start.price
        assert back.end.price == seg.end.price


def test_zhongshu_roundtrip_preserves_decimal_bounds():
    snap = _snapshot_structures()
    for zs in snap.zhongshu:
        d = _zhongshu_to_dict(zs)
        back = _zhongshu_from_dict(json.loads(json.dumps(d, ensure_ascii=False)))
        assert back.zg == zs.zg
        assert back.zd == zs.zd
        assert back.gg == zs.gg
        assert back.dd == zs.dd
        assert back.enter_time == zs.enter_time
        assert back.exit_time == zs.exit_time
        assert back.enter_index == zs.enter_index
        assert back.state == zs.state


def test_fractal_decimal_not_float():
    """价格须以字符串落库（避免 JSON float 精度丢失），反序列化仍为 Decimal。"""
    snap = _snapshot_structures()
    bi = snap.strokes[0]
    d = _bi_to_dict(bi)
    assert isinstance(d["start"]["price"], str)
    assert isinstance(_fractal_price_dec := _bi_from_dict(d).start.price, Decimal)
    assert _fractal_price_dec == bi.start.price


def test_direction_and_fractaltype_enum_roundtrip():
    """Direction / FractalType 经字典化后能由 value 重建（两种方向 × 两种分型）。"""
    top = Fractal(FractalType.TOP, 3, Decimal("12.5"), datetime(2026, 1, 4))
    bottom = Fractal(FractalType.BOTTOM, 7, Decimal("8.5"), datetime(2026, 1, 8))
    bi_up = Bi(Direction.UP, bottom, top, 5, confirmed=True)
    bi_down = Bi(Direction.DOWN, top, bottom, 5, confirmed=True)
    for bi in (bi_up, bi_down):
        back = _bi_from_dict(_bi_to_dict(bi))
        assert back.direction == bi.direction
        assert back.start.type == bi.start.type
        assert back.end.type == bi.end.type
