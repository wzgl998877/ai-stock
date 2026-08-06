"""缠论黄金样本（合成确定性 K 线序列）。

⚠️ 本目录为**合成确定性样本**，用于纯函数引擎的回归测试（无 IO、可复现）。
真正的「人工标注 ≥10 只股票」样本是上线门禁（SC-003），需由懂缠论的伙伴
对照 ``docs/v2/strategy-monitor-prd-v2.md``「缠论算法口径」补齐后替换——
合成样本仅保证引擎**确定性与不变量**，不作为口径一致性的最终验收。
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

from app.domain.entities.chanlun import KlineBar


def bar(i: int, day: int, c, macd=None, spread: float = 0.5) -> KlineBar:
    """对称 K 线：open=close=c，high=c+spread，low=c-spread。

    close 单调变化时相邻 K 不互相包含，便于构造可预测的分型/笔。
    """
    cc = Decimal(str(c))
    s = Decimal(str(spread))
    return KlineBar(
        time=datetime(2026, 1, 1) + timedelta(days=day - 1),
        open=cc,
        high=cc + s,
        low=cc - s,
        close=cc,
        volume=Decimal(100),
        macd_bar=Decimal(str(macd)) if macd is not None else None,
        index=i,
    )


def raw_bar(i: int, day: int, o, h, l, c, macd=None) -> KlineBar:
    """显式 OHLC K 线（构造包含关系等特殊场景）。"""
    return KlineBar(
        time=datetime(2026, 1, 1) + timedelta(days=day - 1),
        open=Decimal(str(o)),
        high=Decimal(str(h)),
        low=Decimal(str(l)),
        close=Decimal(str(c)),
        volume=Decimal(100),
        macd_bar=Decimal(str(macd)) if macd is not None else None,
        index=i,
    )


def series(closes, macds: Optional[list] = None, spread: float = 0.5) -> list[KlineBar]:
    """由 close 列表构造 K 线序列（每根 1 天）。"""
    out: list[KlineBar] = []
    for i, c in enumerate(closes):
        m = macds[i] if macds else None
        out.append(bar(i, i + 1, c, macd=m, spread=spread))
    return out


# 预置波形：先降后升（V 形），低点在中间
V_SHAPE_CLOSES = [10, 8, 6, 4, 2, 4, 6, 8, 10]
# 预置波形：两个完整波（底→顶→底→顶→底），分型方向严格交替
TWO_WAVE_CLOSES = [10, 8, 6, 4, 2, 4, 6, 8, 10, 8, 6, 4, 2, 4, 6, 8, 10]


def interpolate_points(points, spread: float = 0.5) -> list[KlineBar]:
    """由转折点列表构造完整 K 线序列（线性插值 close 与 macd）。

    Args:
        points: ``[(kline_index, close, macd), ...]``，按 index 升序，转折点为局部极值。
    """
    last_idx = points[-1][0]
    closes: list = [None] * (last_idx + 1)  # type: ignore[list-item]
    macds: list = [None] * (last_idx + 1)  # type: ignore[list-item]
    for idx, c, m in points:
        closes[idx] = c
        macds[idx] = m
    for i in range(len(points) - 1):
        i1, c1, m1 = points[i]
        i2, c2, m2 = points[i + 1]
        if i2 == i1:
            continue
        for k in range(i1, i2 + 1):
            t = (k - i1) / (i2 - i1)
            closes[k] = c1 + (c2 - c1) * t
            macds[k] = m1 + (m2 - m1) * t
    return [bar(i, i + 1, closes[i], macd=macds[i], spread=spread) for i in range(last_idx + 1)]


# 下降趋势 + 背驰反转序列：T1→B2 为前一下跌段（绿柱大），
# T3→B5 为当前下跌段（创新低 30<35，绿柱小 → 底背驰），预期触发一类买点。
DIVERGENCE_DOWN_POINTS = [
    (0, 48, 0.5),    # 缓冲
    (1, 50, 0.5),    # T1 顶
    (5, 40, -3.0),   # B1 底（绿柱大）
    (9, 48, 0.5),    # T2 顶
    (13, 35, -3.0),  # B2 底（绿柱大）—— 前一下跌段末端
    (17, 55, 0.5),   # T3 顶（突破前高，破坏前下跌段）
    (21, 48, -0.4),
    (25, 53, 0.5),
    (29, 32, -0.4),  # B4 底（绿柱小）
    (33, 38, 0.3),
    (37, 30, -0.4),  # B5 底（创新低 30<35，绿柱小 → 底背驰）—— 一类买点
    (38, 32, 0.3),   # 缓冲
]
