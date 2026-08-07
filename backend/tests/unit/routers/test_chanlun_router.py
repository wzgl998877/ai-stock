"""chanlun 路由纯函数单测（T029）。

端点的 DB/Redis 集成由 T061 上线门禁覆盖；此处覆盖最易错的序列化层：
Decimal→float、datetime→ISO、SSE 报文格式、DTO 装配。
"""

from datetime import datetime
from decimal import Decimal

from app.application.dtos.chanlun_dto import DISCLAIMER
from app.domain.entities.chanlun import (
    Bi,
    ChanlunSignal,
    Direction,
    Fractal,
    FractalType,
    Segment,
    Zhongshu,
)
from app.routers.chanlun import (
    fractal_to_dto,
    jsonable,
    segment_to_dto,
    signal_to_dto,
    signal_to_mark_dto,
    stroke_to_dto,
    summary_from_signal,
    sse,
    zhongshu_to_dto,
)


def test_jsonable_converts_decimal_and_datetime():
    assert jsonable(Decimal("3.5")) == 3.5
    dt = datetime(2026, 8, 5, 10, 30)
    assert jsonable(dt) == "2026-08-05T10:30:00"
    assert jsonable({"a": Decimal("1"), "b": [datetime(2026, 1, 1)]}) == {
        "a": 1.0, "b": ["2026-01-01T00:00:00"],
    }


def test_sse_format_and_jsonable():
    msg = sse("progress", {"price": Decimal("12.3"), "ts": datetime(2026, 8, 5)})
    assert msg.startswith("event: progress\ndata: ")
    assert msg.endswith("\n\n")
    # Decimal 已转 float（无引号包裹的 12.3）
    assert '"price": 12.3' in msg
    assert '"ts": "2026-08-05T00:00:00"' in msg


def test_summary_from_signal_none():
    assert summary_from_signal(None, "daily") is None


def test_summary_from_signal_maps_fields():
    sig = ChanlunSignal(
        stock_code="600000", period="daily", signal_type="buy1",
        structure_level="segment", signal_time=datetime(2026, 8, 5, 15, 0),
        confirmed_at=datetime(2026, 8, 5, 15, 0),
        trigger_price=Decimal("10.5"), status="confirmed", algo_version="1.0.0",
    )
    s = summary_from_signal(sig, "daily")
    assert s is not None
    assert s.signal_type == "buy1"
    assert s.trigger_price == Decimal("10.5")
    assert s.confirmed_at == datetime(2026, 8, 5, 15, 0)
    assert s.is_fresh is True  # 昨天产生的日K信号在 7 天窗口内


def test_is_fresh_window_by_period():
    """新鲜度窗口：daily 7 自然日、m30 2 自然日；边界含当日，无时间视为不新鲜。"""
    from datetime import timedelta

    from app.routers.chanlun import _is_fresh

    now = datetime.now()
    # daily：窗口内 / 超窗（避开整日边界，防计时抖动）
    assert _is_fresh("daily", now - timedelta(days=6, hours=12)) is True
    assert _is_fresh("daily", now - timedelta(days=8)) is False
    # m30：窗口内 / 超窗
    assert _is_fresh("m30", now - timedelta(days=1)) is True
    assert _is_fresh("m30", now - timedelta(days=3)) is False
    # signal_time 缺失 → 视为不新鲜（无时间可比，不应置亮）
    assert _is_fresh("daily", None) is False


def test_summary_is_fresh_false_for_old_signal():
    """超出窗口的信号 is_fresh=False（前端置灰为历史信号）。"""
    from datetime import timedelta

    sig = ChanlunSignal(
        stock_code="600000", period="m30", signal_type="sell1",
        structure_level="segment", signal_time=datetime.now() - timedelta(days=5),
        algo_version="1.0.0",
    )
    s = summary_from_signal(sig, "m30")
    assert s is not None and s.is_fresh is False


def test_signal_to_dto_maps_all_fields():
    sig = ChanlunSignal(
        stock_code="000001", period="m30", signal_type="sell2",
        structure_level="segment", signal_time=datetime(2026, 8, 5, 10, 0),
        confirmed_at=datetime(2026, 8, 5, 10, 0), trigger_price=Decimal("11.2"),
        status="invalidated", invalidated_reason="被后续笔破坏", algo_version="1.0.0", id=7,
    )
    dto = signal_to_dto(sig)
    assert dto.id == 7
    assert dto.stock_code == "000001"
    assert dto.period == "m30"
    assert dto.signal_type == "sell2"
    assert dto.status == "invalidated"
    assert dto.invalidated_reason == "被后续笔破坏"


def test_watchlist_response_carries_disclaimer():
    """DTO 默认 disclaimer 不被 jsonable 破坏。"""
    from app.application.dtos.chanlun_dto import WatchlistSignalsResponse
    resp = WatchlistSignalsResponse(items=[])
    dumped = jsonable(resp.model_dump())
    assert dumped["disclaimer"] == DISCLAIMER


def test_entity_to_dto_conversions():
    """T037：缠论结构实体 → DTO 转换正确（含 fractal/stroke/segment/zhongshu/signal_mark）。"""
    f1 = Fractal(FractalType.BOTTOM, 0, Decimal("10.0"), datetime(2026, 1, 1))
    f2 = Fractal(FractalType.TOP, 5, Decimal("12.0"), datetime(2026, 1, 5))
    bi = Bi(Direction.UP, f1, f2, 6, confirmed=True)
    seg = Segment(Direction.UP, f1, f2, 3, confirmed=True, break_type="first")
    zs = Zhongshu(
        zg=Decimal("11"), zd=Decimal("10.5"), gg=Decimal("12"), dd=Decimal("10"),
        enter_time=datetime(2026, 1, 2), exit_time=datetime(2026, 1, 4),
        enter_index=0, state="ended",
    )

    fdto = fractal_to_dto(f1)
    assert fdto.type == "bottom" and fdto.price == Decimal("10.0")

    bdto = stroke_to_dto(bi)
    assert bdto.direction == "up" and bdto.kline_count == 6 and bdto.confirmed is True

    sdto = segment_to_dto(seg)
    assert sdto.direction == "up" and sdto.break_type == "first" and sdto.bi_count == 3

    zdto = zhongshu_to_dto(zs)
    assert zdto.zg == Decimal("11") and zdto.state == "ended" and zdto.zd == Decimal("10.5")

    sig = ChanlunSignal(
        stock_code="600000", period="daily", signal_type="buy2",
        structure_level="segment", signal_time=datetime(2026, 1, 3),
        trigger_price=Decimal("10.5"), algo_version="1.0.0",
    )
    mdto = signal_to_mark_dto(sig, "daily")
    assert mdto.signal_type == "buy2" and mdto.level == 2
    assert mdto.time == datetime(2026, 1, 3)
