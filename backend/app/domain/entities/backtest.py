"""回测领域实体（模块三），对标 ``t_backtest_report`` / ``t_backtest_signal_detail`` / ``t_backtest_summary``。"""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Optional


@dataclass
class BacktestReport:
    """回测报告（对标 ``t_backtest_report``）。"""

    user_id: str
    range_label: str                          # 1y / 3y / 5y
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    stock_count: int = 0
    signal_total: int = 0
    excluded_invalidated: int = 0
    benchmark_return: Optional[Decimal] = None
    algo_version: str = ""
    status: str = "running"                   # running / done / failed
    report_id: Optional[int] = None
    create_time: Optional[datetime] = None


@dataclass
class BacktestSignalDetail:
    """回测信号明细（对标 ``t_backtest_signal_detail``）。

    一条信号确认后，在第 5/10/20/60 个交易日的涨跌；窗口越界则
    ``window_complete=False`` 且 ``ret_*`` 全空（spec 边缘情况）。
    """

    report_id: int
    stock_code: str
    period: str
    signal_type: str
    structure_level: str
    signal_time: datetime
    trigger_price: Optional[Decimal] = None
    ret_5: Optional[Decimal] = None
    ret_10: Optional[Decimal] = None
    ret_20: Optional[Decimal] = None
    ret_60: Optional[Decimal] = None
    window_complete: bool = True
    id: Optional[int] = None


@dataclass
class BacktestSummary:
    """回测聚合统计（对标 ``t_backtest_summary``，预聚合加速查询）。"""

    report_id: int
    period: str
    signal_type: str
    window: int                               # 5/10/20/60
    sample_count: int = 0
    win_rate: Optional[Decimal] = None        # DECIMAL(8,6)；卖点按「跌为赢」计
    avg_return: Optional[Decimal] = None      # 卖点为卖方视角（真实收益取反）
    median_return: Optional[Decimal] = None   # 卖点同上取反
    profit_loss_ratio: Optional[Decimal] = None  # 卖点同上取反
    note: Optional[str] = None                # sample_insufficient / window_incomplete / None
    id: Optional[int] = None
