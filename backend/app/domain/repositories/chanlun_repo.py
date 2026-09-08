"""缠论策略 Repository 接口（模块三）。

聚合四类持久化职责（对照 ``data-model.md``）：
1. 信号 ``t_strategy_signal``：幂等 upsert（``dedup_key``）、查询、失效标记；
2. 结构快照 ``t_strategy_structure``：覆盖式 upsert（``stock_code+period+algo_version`` 唯一）；
3. 运行日志 ``t_strategy_run_log``：监控/重算任务记录；
4. 监控配置 ``t_strategy_monitor_config``：逐股逐周期开关（T050/T051）。
"""

from abc import ABC, abstractmethod
from typing import Optional

from app.domain.entities.chanlun import ChanlunSignal, StructureSnapshot
from app.domain.entities.strategy import MonitorConfig, StrategyRunLog


class ChanlunRepository(ABC):
    """缠论策略数据访问接口。"""

    # --- 信号 ---

    @abstractmethod
    async def upsert_signals_batch(self, signals: list[ChanlunSignal]) -> list[ChanlunSignal]:
        """幂等批量写入信号（依据 ``dedup_key``）；返回**新增的信号实体**（已存在不计）。

        已存在的 ``confirmed`` 信号不被覆盖（收盘确认不重绘）。
        新增实体供监控层做微信推送等下游消费。
        """
        ...

    @abstractmethod
    async def get_signals(
        self,
        stock_code: str,
        period: str,
        status: Optional[str] = None,
        limit: int = 100,
        algo_version: Optional[str] = None,
    ) -> list[ChanlunSignal]:
        """查询单股信号历史（按 ``signal_time`` 倒序）。

        ``algo_version`` 传入时只返回该口径的信号（v1/v2 切换），None=全版本混排。
        """
        ...

    @abstractmethod
    async def get_latest_signals_for_stocks(
        self, stock_codes: list[str], period: str,
        algo_version: Optional[str] = None,
    ) -> list[ChanlunSignal]:
        """批量获取多只股票的最新确认信号（自选股徽标用）。

        ``algo_version`` 传入时徽标取该口径下最新一条；该口径无信号则无徽标。
        """
        ...

    @abstractmethod
    async def invalidate_signals(
        self, stock_code: str, period: str, reason: str
    ) -> int:
        """将该股该周期所有 ``confirmed`` 信号标记为 ``invalidated``；返回受影响行数。"""
        ...

    @abstractmethod
    async def update_push_result(
        self,
        signal_ids: list[int],
        status: str,
        message_id: Optional[str] = None,
    ) -> int:
        """批量回写信号微信推送结果（success / skipped / failed）。

        ``message_id`` 为网关受理返回的消息 ID（成功时记录，其余传 None）；
        同时落 ``push_time``。返回受影响行数。
        """
        ...

    # --- 结构快照 ---

    @abstractmethod
    async def upsert_structure(self, snapshot: StructureSnapshot) -> None:
        """覆盖式写入结构快照（每股每周期每版本一行，o9p0q1r2s3t4 起含 algo_version）。"""
        ...

    @abstractmethod
    async def get_structure(
        self, stock_code: str, period: str, algo_version: Optional[str] = None
    ) -> Optional[StructureSnapshot]:
        """读取结构快照；不存在返回 None。

        ``algo_version`` 传入时只取该口径快照（双版本水位线独立）；None=不限版本
        （取最近一行，兼容旧调用方）。
        """
        ...

    # --- 运行日志 ---

    @abstractmethod
    async def create_run_log(self, log: StrategyRunLog) -> StrategyRunLog:
        """创建运行日志（status=running）。"""
        ...

    @abstractmethod
    async def finish_run_log(
        self,
        log_id: int,
        status: str,
        success: int,
        failed: int,
        failed_detail: Optional[list[dict]] = None,
        duration_ms: Optional[int] = None,
    ) -> None:
        """结束运行日志（写 finished_at / 计数 / duration）。"""
        ...

    @abstractmethod
    async def get_latest_run_log(
        self, period: str, algo_version: Optional[str] = None
    ) -> Optional[StrategyRunLog]:
        """获取某周期最近一次运行日志（运行状态卡片用）。

        ``algo_version`` 传入时只取该口径的运行记录（v1/v2 双跑后状态卡片
        须显示所选版本的最近一次）；None=不限版本。
        """
        ...

    # --- 监控配置（T050/T051，逐股逐周期开关）---

    @abstractmethod
    async def get_monitor_config(
        self, user_id: str, stock_code: str
    ) -> Optional[MonitorConfig]:
        """读取逐股监控配置；不存在返回 None（视为双周期默认启用）。"""
        ...

    @abstractmethod
    async def get_monitor_configs(self, user_id: str) -> list[MonitorConfig]:
        """读取用户全部逐股监控配置（扫描范围过滤、徽标状态用）。"""
        ...

    @abstractmethod
    async def upsert_monitor_config(self, config: MonitorConfig) -> MonitorConfig:
        """覆盖式写入逐股监控配置（``user_id+stock_code`` 唯一）。"""
        ...

    @abstractmethod
    async def delete_monitor_config(self, user_id: str, stock_code: str) -> int:
        """删除逐股监控配置（自选股移除联动）；返回受影响行数。"""
        ...
