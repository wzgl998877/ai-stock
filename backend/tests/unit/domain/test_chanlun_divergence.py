"""缠论引擎分层测试（3）：背驰判定（价格幅度 + MACD 面积双条件）。

直接测 ``chanlun_divergence.detect_divergence``，输入由 ``bar`` 构造（含 MACD BAR）。
"""

from decimal import Decimal

from app.domain.entities.chanlun import Direction
from app.domain.services.chanlun_divergence import detect_divergence, macd_area
from tests.fixtures.chanlun_golden_samples import bar


def test_macd_area_separates_red_and_green():
    bars = [
        bar(0, 1, 10, macd=2),
        bar(1, 2, 12, macd=-1),
        bar(2, 3, 14, macd=3),
    ]
    red, green = macd_area(bars, 0, 2)
    assert red == Decimal(5)   # 2 + 3
    assert green == Decimal(1)


def test_divergence_up_true_when_macd_shrinks_and_new_high():
    """curr 段创新高，但红柱面积与涨幅均小于 prev → 顶背驰。"""
    bars = [
        # prev 上涨段 index0-3：到 16，红柱大
        bar(0, 1, 10, macd=2), bar(1, 2, 12, macd=2), bar(2, 3, 14, macd=2), bar(3, 4, 16, macd=2),
        bar(4, 5, 14, macd=-0.5),  # 回调
        # curr 上涨段 index5-7：到 18（创新高），红柱小
        bar(5, 6, 15, macd=1), bar(6, 7, 17, macd=0.8), bar(7, 8, 18, macd=0.5),
    ]
    assert detect_divergence(bars, 0, 3, 5, 7, Direction.UP) is True


def test_divergence_up_false_when_no_new_high():
    """curr 未创新高 → 非背驰。"""
    bars = [
        bar(0, 1, 10, macd=2), bar(1, 2, 16, macd=2),  # prev 高 16
        bar(2, 3, 12, macd=-1),
        bar(3, 4, 14, macd=1),  # curr 高 14 < 16
    ]
    assert detect_divergence(bars, 0, 1, 3, 3, Direction.UP) is False


def test_divergence_up_false_when_macd_not_shrinking():
    """curr MACD 面积未缩小 → 非背驰。"""
    bars = [
        bar(0, 1, 10, macd=1), bar(1, 2, 12, macd=1),   # prev 面积 2
        bar(2, 3, 11, macd=-0.2),
        bar(3, 4, 13, macd=2), bar(4, 5, 15, macd=2),   # curr 面积 4 > 2，创新高但未衰减
    ]
    assert detect_divergence(bars, 0, 1, 3, 4, Direction.UP) is False


def test_divergence_down_true_when_macd_shrinks_and_new_low():
    """curr 段创新低，但绿柱面积与跌幅均小于 prev → 底背驰。"""
    bars = [
        # prev 下跌段：到 4，绿柱大
        bar(0, 1, 10, macd=-2), bar(1, 2, 8, macd=-2), bar(2, 3, 6, macd=-2), bar(3, 4, 4, macd=-2),
        bar(4, 5, 6, macd=0.5),   # 反弹
        # curr 下跌段：到 2（创新低），绿柱小
        bar(5, 6, 5, macd=-1), bar(6, 7, 3, macd=-0.8), bar(7, 8, 2, macd=-0.5),
    ]
    assert detect_divergence(bars, 0, 3, 5, 7, Direction.DOWN) is True


def test_divergence_false_without_macd_data():
    """缺 MACD 数据（面积为 0）→ 保守不认定背驰。"""
    bars = [
        bar(0, 1, 10, macd=None), bar(1, 2, 12, macd=None),
        bar(2, 3, 11, macd=None),
        bar(3, 4, 13, macd=None), bar(4, 5, 15, macd=None),
    ]
    assert detect_divergence(bars, 0, 1, 3, 4, Direction.UP) is False
