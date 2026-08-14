"""缠论回测 DTO（模块三 US3，T043）—— Pydantic 请求/响应模型。

对照 ``frontend/src/domain/types.ts`` 的 ``BacktestReportListItem / BacktestSummaryCell /
BacktestSignalDetailItem``；比例用 ``Decimal``（router 序列化层转 float，T060），所有
响应附免责声明（FR-016）。
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field

from app.application.dtos.chanlun_dto import DISCLAIMER

BACKTEST_DISCLAIMER = (
    "回测存在生存者偏差（仅含当前在市自选股）与未来函数防护，结果仅供算法有效性参考，"
    "不代表未来收益；" + DISCLAIMER
)


# ---------------------------------------------------------------------------
# 请求
# ---------------------------------------------------------------------------

class BacktestRunRequest(BaseModel):
    """发起回测（POST /api/v1/backtest/run）。"""
    range: str = Field(default="3y", pattern="^(1y|3y|5y)$")
    periods: list[str] = Field(default_factory=lambda: ["daily"])
    stock_codes: Optional[list[str]] = None     # None=用户全部启用自选股


# ---------------------------------------------------------------------------
# 报告列表
# ---------------------------------------------------------------------------

class BacktestReportListItem(BaseModel):
    report_id: int
    range_label: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    stock_count: int = 0
    signal_total: int = 0
    excluded_invalidated: int = 0
    algo_version: str = ""
    status: str = "running"
    create_time: Optional[datetime] = None


class BacktestReportsResponse(BaseModel):
    items: list[BacktestReportListItem]
    total: int
    disclaimer: str = BACKTEST_DISCLAIMER


# ---------------------------------------------------------------------------
# 报告详情（汇总表）
# ---------------------------------------------------------------------------

class BacktestReportMeta(BaseModel):
    range_label: str
    stock_count: int = 0
    signal_total: int = 0
    excluded_invalidated: int = 0
    algo_version: str = ""
    benchmark_return: Optional[Decimal] = None
    finished_at: Optional[datetime] = None


class BacktestSummaryCell(BaseModel):
    """汇总单元格：(period, signal_type, window) 一行。"""
    period: str
    signal_type: str
    window: int
    sample: int
    win_rate: Optional[Decimal] = None        # 卖点按「跌为赢」计
    avg_return: Optional[Decimal] = None      # 卖点为卖方视角（真实收益取反）
    median_return: Optional[Decimal] = None   # 卖点同上取反
    profit_loss_ratio: Optional[Decimal] = None  # 卖点同上取反
    note: Optional[str] = None


class BacktestReportDetailResponse(BaseModel):
    meta: BacktestReportMeta
    summary: list[BacktestSummaryCell]
    disclaimer: str = BACKTEST_DISCLAIMER


# ---------------------------------------------------------------------------
# 报告明细下钻
# ---------------------------------------------------------------------------

class BacktestSignalDetailItem(BaseModel):
    stock_code: str
    signal_type: str
    signal_time: datetime
    trigger_price: Optional[Decimal] = None
    ret_5: Optional[Decimal] = None
    ret_10: Optional[Decimal] = None
    ret_20: Optional[Decimal] = None
    ret_60: Optional[Decimal] = None
    window_complete: bool = True


class BacktestDetailsResponse(BaseModel):
    items: list[BacktestSignalDetailItem]
    total: int
    disclaimer: str = BACKTEST_DISCLAIMER
