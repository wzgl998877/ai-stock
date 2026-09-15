"""策略监控运维实体（模块三），对标 ``t_strategy_run_log`` / ``t_strategy_monitor_config``。

与 ``chanlun.py``（缠论算法结构对象）区分：本模块放「监控任务编排」相关的
持久化实体（运行日志、逐股监控配置），供 ``ChanlunRepository`` / 监控 UseCase 使用。
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class StrategyRunLog:
    """缠论计算任务运行日志（对标 ``t_strategy_run_log``）。"""

    period: str                                # daily / m30
    trigger_type: str                          # scheduled / manual
    status: str = "running"                    # running / done / failed
    total: Optional[int] = None
    success: Optional[int] = None
    failed: Optional[int] = None
    failed_detail: Optional[list[dict]] = None  # [{stock_code, reason}]
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    algo_version: str = ""
    user_id: Optional[str] = None              # 系统定时任务可空
    id: Optional[int] = None


@dataclass
class ScanPreflight:
    """扫描数据前置诊断（调用方在 ``scan`` 前组装，写入 run_log 供卡片/日志可见）。

    2026-09-14 事故：数据没到位时扫描全量 ``no_new_data`` 跳过，run_log 却是
    ``status='done', success=0, failed=0, failed_detail=NULL``——从监控看完全
    正常，实际数据源全挂。本对象让「数据前置」的结果落到 run_log 上。

    放 Domain 而非 Application：它是 ``daily_sync``（Application）与
    ``chanlun_monitor``（Application use case）之间的契约，放 Domain 避免两个
    Application 模块互相 import。
    """

    ok: bool = True
    status: Optional[str] = None                      # 覆盖 run_log.status（如 "data_stale"）
    notes: list[dict] = field(default_factory=list)   # 追加进 failed_detail


@dataclass
class MonitorConfig:
    """逐股监控配置（对标 ``t_strategy_monitor_config``）。"""

    user_id: str
    stock_code: str
    daily_enabled: bool = True
    m30_enabled: bool = True
    id: Optional[int] = None
    create_time: Optional[datetime] = None
    update_time: Optional[datetime] = None
