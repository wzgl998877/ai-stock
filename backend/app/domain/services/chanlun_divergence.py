"""缠论背驰判定（纯函数，模块三）。

按 research.md D8：输入直接接收 MACD BAR 序列（由 UseCase 从 ``t_stock_indicator``
读取后注入 ``KlineBar.macd_bar``），**不在引擎内重算 MACD**，保证单一数据源。

背驰双条件（与 ``strategy-monitor-prd-v2.md`` 一致）：
1. 价格幅度：当前同向段创出新极值，但幅度小于前一同向段；
2. MACD 面积：当前段同号 BAR 累积面积小于前一段。

趋势背驰 vs 盘整背驰：本模块提供 ``detect_divergence``（趋势背驰，比较两段同向运动）。
盘整背驰在中枢震荡中由 ``ChanlunService`` 直接比较中枢内两段，复用同一面积函数。
"""

from decimal import Decimal
from typing import Optional

from app.domain.entities.chanlun import KlineBar, Direction


def macd_area(bars: list[KlineBar], lo: int, hi: int) -> tuple[Decimal, Decimal]:
    """计算 ``[lo, hi]`` 区间 MACD BAR 的红柱面积与绿柱面积。

    红柱（BAR>0）累加为 ``red``，绿柱（BAR<0）取绝对值累加为 ``green``。
    越界下标忽略；``macd_bar`` 为 None 视为 0。
    """
    red = Decimal(0)
    green = Decimal(0)
    for k in range(lo, hi + 1):
        if k < 0 or k >= len(bars):
            continue
        bar = bars[k].macd_bar
        if bar is None or bar == 0:
            continue
        if bar > 0:
            red += bar
        else:
            green += -bar
    return red, green


def _extreme(bars: list[KlineBar], lo: int, hi: int, kind: str) -> Optional[Decimal]:
    """区间内最高价（high）或最低价（low）。"""
    vals = []
    for k in range(lo, hi + 1):
        if 0 <= k < len(bars):
            vals.append(bars[k].high if kind == "high" else bars[k].low)
    if not vals:
        return None
    return max(vals) if kind == "high" else min(vals)


def detect_divergence(
    bars: list[KlineBar],
    prev_lo: int, prev_hi: int,
    curr_lo: int, curr_hi: int,
    direction: Direction,
) -> bool:
    """趋势背驰判定（双条件）。

    Args:
        bars: 包含处理后的 K 线序列（与 Fractal.kline_index 同一下标空间）。
        prev_lo/prev_hi: 前一同向段的起止下标。
        curr_lo/curr_hi: 当前同向段的起止下标。
        direction: 比较方向。

    双条件（与 ``strategy-monitor-prd-v2.md`` 一致）：
    1. 价格幅度——当前段创出新极值（上涨创新高 / 下跌创新低）；
    2. MACD 面积——当前段同号 BAR 累积面积小于前段（动能衰减）。

    任一段无 MACD 数据（面积为 0）则不认定背驰（保守，避免误发信号）。
    """
    if direction == Direction.UP:
        curr_high = _extreme(bars, curr_lo, curr_hi, "high")
        prev_high = _extreme(bars, prev_lo, prev_hi, "high")
        if curr_high is None or prev_high is None:
            return False
        if curr_high <= prev_high:
            return False  # 条件1：未创新高
        prev_red, _ = macd_area(bars, prev_lo, prev_hi)
        curr_red, _ = macd_area(bars, curr_lo, curr_hi)
        if curr_red <= 0 or prev_red <= 0:
            return False  # 缺 MACD 数据
        if curr_red >= prev_red:
            return False  # 条件2：MACD 面积未衰减
        return True
    else:
        curr_low = _extreme(bars, curr_lo, curr_hi, "low")
        prev_low = _extreme(bars, prev_lo, prev_hi, "low")
        if curr_low is None or prev_low is None:
            return False
        if curr_low >= prev_low:
            return False  # 条件1：未创新低
        _, prev_green = macd_area(bars, prev_lo, prev_hi)
        _, curr_green = macd_area(bars, curr_lo, curr_hi)
        if curr_green <= 0 or prev_green <= 0:
            return False
        if curr_green >= prev_green:
            return False  # 条件2：MACD 面积未衰减
        return True
