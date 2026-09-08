"""缠论策略监控 DTO（模块三）—— Pydantic 请求/响应模型。

对照 ``frontend/src/domain/types.ts``（T003）保持字段一致；价格用 ``Decimal``
（router 序列化层转 float，见 T060）。所有信号响应附免责声明（FR-016）。
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field

# 免责声明（FR-016，所有信号响应必须携带）
DISCLAIMER = "规则参考信号，不构成投资建议"


# ---------------------------------------------------------------------------
# 信号
# ---------------------------------------------------------------------------

class SignalDTO(BaseModel):
    """单条缠论信号（完整字段）。"""
    id: Optional[int] = None
    stock_code: str
    period: str
    signal_type: str
    structure_level: str
    signal_time: datetime
    confirmed_at: Optional[datetime] = None
    trigger_price: Optional[Decimal] = None
    status: str = "confirmed"
    invalidated_reason: Optional[str] = None
    algo_version: str = ""
    # 微信推送结果（success / skipped / failed；None=未尝试）
    push_status: Optional[str] = None
    push_message_id: Optional[str] = None
    push_time: Optional[datetime] = None


class SignalListResponse(BaseModel):
    """单股信号历史响应（GET /stocks/{code}/signals、/signal-history）。"""
    stock_code: str
    period: str
    items: list[SignalDTO] = []
    total: int = 0
    page: int = 1
    page_size: int = 50
    disclaimer: str = DISCLAIMER


# ---------------------------------------------------------------------------
# 自选股徽标
# ---------------------------------------------------------------------------

class SignalSummaryDTO(BaseModel):
    """单周期最新信号摘要（徽标用，字段对齐前端 ``SignalSummary``）。"""
    signal_type: Optional[str] = None      # None=无信号
    signal_time: Optional[datetime] = None
    confirmed_at: Optional[datetime] = None
    trigger_price: Optional[Decimal] = None
    is_fresh: Optional[bool] = None        # 新鲜度（纯展示属性）；False=历史信号（超出新鲜度窗口）


class WatchlistSignalItem(BaseModel):
    """自选股双周期信号徽标项。"""
    stock_code: str
    stock_name: str = ""
    daily: Optional[SignalSummaryDTO] = None
    m30: Optional[SignalSummaryDTO] = None
    daily_status: str = "monitored_nodata"   # monitored / monitored_nodata / disabled / insufficient_data
    m30_status: str = "monitored_nodata"


class WatchlistSignalsResponse(BaseModel):
    items: list[WatchlistSignalItem] = []
    disclaimer: str = DISCLAIMER


# ---------------------------------------------------------------------------
# 结构快照
# ---------------------------------------------------------------------------

class FractalDTO(BaseModel):
    type: str
    kline_index: int
    price: Decimal
    time: datetime


class StrokeDTO(BaseModel):
    direction: str
    start: FractalDTO
    end: FractalDTO
    kline_count: int
    confirmed: bool = True


class SegmentDTO(BaseModel):
    direction: str
    start: FractalDTO
    end: FractalDTO
    bi_count: int
    confirmed: bool = True
    break_type: str = ""


class ZhongshuDTO(BaseModel):
    zg: Decimal
    zd: Decimal
    gg: Decimal
    dd: Decimal
    enter_time: Optional[datetime] = None
    exit_time: Optional[datetime] = None
    enter_index: int = 0
    state: str = "ended"


class SignalMarkDTO(BaseModel):
    """K 线主图买卖点标注（字段对齐前端 ``SignalMark``）。"""
    signal_type: str
    time: datetime                          # 与 K 线 x 轴对齐
    price: Optional[Decimal] = None
    confirmed_at: Optional[datetime] = None
    level: int                              # 1/2/3 类
    period: str = "daily"


class StructureResponse(BaseModel):
    """缠论结构 + 信号标注响应（GET /stocks/{code}/structure）。"""
    stock_code: str
    period: str
    strokes: list[StrokeDTO] = []
    segments: list[SegmentDTO] = []
    zhongshu: list[ZhongshuDTO] = []
    signal_marks: list[SignalMarkDTO] = []
    last_kline_time: Optional[datetime] = None
    algo_version: str = ""
    disclaimer: str = DISCLAIMER


# ---------------------------------------------------------------------------
# 配置与状态
# ---------------------------------------------------------------------------

class MonitorConfigBody(BaseModel):
    """逐股监控配置更新体（PUT /stocks/{code}/config）。"""
    daily_enabled: Optional[bool] = None
    m30_enabled: Optional[bool] = None


class MonitorConfigDTO(BaseModel):
    stock_code: str
    daily_enabled: bool = True
    m30_enabled: bool = True


class RunStatusDTO(BaseModel):
    """单周期计算任务状态（字段对齐前端 ``RunStatusItem`` 与 rest-api 契约）。"""
    period: str
    last_run_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    total: Optional[int] = None
    success: Optional[int] = None
    failed: Optional[int] = None
    failed_detail: Optional[list[dict]] = None
    algo_version: str = ""


class RunStatusResponse(BaseModel):
    daily: Optional[RunStatusDTO] = None
    m30: Optional[RunStatusDTO] = None
    algo_version: str = ""


# ---------------------------------------------------------------------------
# 请求
# ---------------------------------------------------------------------------

class RecalculateRequest(BaseModel):
    """重算请求体（POST /recalculate）。

    ``version``：缠论算法口径（v1=旧口径 / v2=当前口径）；None 用服务端默认版
    （settings.chanlun_algo_version）。双版本并存（2026-09-08）。
    """
    stock_codes: Optional[list[str]] = None     # None=用户全部自选股
    period: str = Field(default="daily", pattern="^(daily|m30|both)$")
    version: Optional[str] = Field(default=None, pattern="^(v1|v2)$")
