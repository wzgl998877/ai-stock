"""缠论领域实体（模块三）。

对标 ``app/domain/entities/stock_indicator.py`` 的 dataclass 风格。
分两类：
1. 引擎内部结构对象：``KlineBar`` / ``Fractal`` / ``Bi`` / ``Segment`` / ``Zhongshu``
   —— 纯内存结构，供 ``ChanlunService`` 产出与单测断言。
2. 持久化实体：``ChanlunSignal`` / ``StructureSnapshot`` —— 与 ``t_strategy_signal`` /
   ``t_strategy_structure`` 一一对应，供 Repository 落库。
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional


# ---------------------------------------------------------------------------
# 引擎输入
# ---------------------------------------------------------------------------

@dataclass
class KlineBar:
    """标准化 K 线（缠论引擎输入单元）。

    ``time`` 为 K 线时间戳（日线取 ``date``，m30 取区间结束时刻）；
    ``macd_bar`` 由 UseCase 从 ``t_stock_indicator`` 读取后注入（背驰判定依赖，见 research.md D8）。
    """

    time: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal = Decimal(0)
    macd_bar: Optional[Decimal] = None
    index: int = 0  # 在输入序列中的位置（0-based）


# ---------------------------------------------------------------------------
# 结构对象（引擎产出）
# ---------------------------------------------------------------------------

class Direction(str, Enum):
    UP = "up"
    DOWN = "down"


class FractalType(str, Enum):
    TOP = "top"        # 顶分型
    BOTTOM = "bottom"  # 底分型


@dataclass
class Fractal:
    """顶/底分型：经包含处理后的连续三根 K 中，中间为局部最高/低。"""

    type: FractalType
    kline_index: int        # 分型中间 K 在原始序列的下标
    price: Decimal          # 顶取 high，底取 low
    time: datetime


@dataclass
class Bi:
    """笔：相邻的顶底分型连线，方向交替，且含独立 K 线 ≥5 根。"""

    direction: Direction
    start: Fractal
    end: Fractal
    kline_count: int        # 笔内包含处理后的 K 线数
    confirmed: bool = True


@dataclass
class Segment:
    """线段：由 ≥3 笔组成，方向由其内部特征序列判定（特征序列法）。"""

    direction: Direction
    start: Fractal          # 线段起点（= 第一笔起点分型）
    end: Fractal            # 线段终点
    bi_count: int           # 构成线段的笔数
    confirmed: bool = True
    break_type: str = ""    # 破坏类型：first / second（第一/第二种破坏）


@dataclass
class Zhongshu:
    """中枢：至少连续三笔的重叠区间 [ZD, ZG]。

    - ZG = min(三笔中前两笔的高点)
    - ZD = max(三笔中前两笔的低点)
    - GG = 区间内最高点 / DD = 区间内最低点
    """

    zg: Decimal
    zd: Decimal
    gg: Decimal
    dd: Decimal
    enter_time: datetime
    exit_time: Optional[datetime] = None
    enter_index: int = 0    # 进入中枢的笔下标
    state: str = "ended"    # forming / extended / ended


# ---------------------------------------------------------------------------
# 持久化实体（与 t_strategy_signal / t_strategy_structure 对应）
# ---------------------------------------------------------------------------

@dataclass
class ChanlunSignal:
    """缠论信号历史（核心实体，对标 ``t_strategy_signal``）。"""

    stock_code: str
    period: str                               # daily / m30
    signal_type: str                          # buy1..sell3
    structure_level: str                      # stroke / segment
    signal_time: datetime
    confirmed_at: Optional[datetime] = None
    trigger_price: Optional[Decimal] = None
    algo_version: str = ""
    status: str = "confirmed"
    invalidated_reason: Optional[str] = None
    user_id: Optional[str] = None
    dedup_key: Optional[str] = None
    id: Optional[int] = None
    create_time: Optional[datetime] = None
    update_time: Optional[datetime] = None

    def make_dedup_key(self) -> str:
        """构造幂等键：stock_code|period|signal_type|signal_time|algo_version。"""
        ts = self.signal_time.isoformat(sep=" ") if self.signal_time else ""
        return f"{self.stock_code}|{self.period}|{self.signal_type}|{ts}|{self.algo_version}"


@dataclass
class StructureSnapshot:
    """缠论结构快照（覆盖式更新，对标 ``t_strategy_structure``）。

    ``strokes`` / ``segments`` / ``zhongshu`` 仅存内存对象；落库时由 Repository
    序列化为 JSON（宪章允许 JSON 仅用于结构快照扩展字段）。
    """

    stock_code: str
    period: str
    strokes: list[Bi] = field(default_factory=list)
    segments: list[Segment] = field(default_factory=list)
    zhongshu: list[Zhongshu] = field(default_factory=list)
    last_kline_time: Optional[datetime] = None
    algo_version: str = ""
    update_time: Optional[datetime] = None
