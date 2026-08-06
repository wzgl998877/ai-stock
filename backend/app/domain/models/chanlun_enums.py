"""缠论领域枚举（模块三）。

对标 ``app/domain/models/stock_data.py`` 的 ``str, Enum`` 风格。
所有枚举值与持久化层（``t_strategy_signal`` 等）及前端 ``domain/types.ts`` 保持一致。
"""

from enum import Enum


class SignalType(str, Enum):
    """缠论买卖点类型：一/二/三类买、一/二/三类卖。"""

    BUY1 = "buy1"
    BUY2 = "buy2"
    BUY3 = "buy3"
    SELL1 = "sell1"
    SELL2 = "sell2"
    SELL3 = "sell3"


class StrategyPeriod(str, Enum):
    """策略周期：日线 / 30 分钟。"""

    DAILY = "daily"
    M30 = "m30"


class SignalStatus(str, Enum):
    """信号状态机：已确认 →（数据源修正）→ 已失效（终态）。"""

    CONFIRMED = "confirmed"
    INVALIDATED = "invalidated"


class StructureLevel(str, Enum):
    """结构级别：笔（stroke）/ 线段（segment）。"""

    STROKE = "stroke"
    SEGMENT = "segment"


class WindowDays(int, Enum):
    """回测观察窗口（交易日）。日线按交易日；m30 按等根数换算。"""

    W5 = 5
    W10 = 10
    W20 = 20
    W60 = 60


# 便捷集合
ALL_SIGNAL_TYPES: tuple[SignalType, ...] = tuple(SignalType)
BUY_SIGNAL_TYPES: tuple[SignalType, ...] = (SignalType.BUY1, SignalType.BUY2, SignalType.BUY3)
SELL_SIGNAL_TYPES: tuple[SignalType, ...] = (SignalType.SELL1, SignalType.SELL2, SignalType.SELL3)
ALL_WINDOWS: tuple[WindowDays, ...] = tuple(WindowDays)
