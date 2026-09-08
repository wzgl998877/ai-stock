"""ChanlunMonitorUseCase — 缠论监控扫描用例（T027）。

职责：
1. 取用户自选股并集（``get_all_items_by_user``，T051 起改读 ``t_strategy_monitor_config``）；
2. 数据新鲜度检查：结构快照的 ``last_kline_time`` 与当前库中最新 K 线时间相同则记
   ``no_new_data`` 跳过该股（避免重复计算）；
3. ``asyncio.Semaphore`` 限并发（≤ ``settings.chanlun_concurrency``）；**每股在独立
   ``AsyncSession`` 上计算+落库**（``AsyncSession`` 非并发安全，gather 并发下不可共享）；
4. 全程写 ``run_log``（``running`` → ``done``，含 success/failed 计数与失败明细）。

返回的 ``StrategyRunLog`` 中，``total = success + failed + skipped``（skipped 为新鲜度
命中而跳过的股票，不进 success/failed 计数，仅记日志）。
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Awaitable, Callable, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.use_cases.chanlun_calc import ChanlunCalcUseCase, NoKlineDataError
from app.core.config import settings
from app.domain.entities.chanlun import ChanlunSignal
from app.domain.entities.strategy import StrategyRunLog
from app.domain.repositories.chanlun_repo import ChanlunRepository
from app.domain.repositories.stock_data_repo import StockDataRepository
from app.domain.repositories.watchlist_repo import WatchlistRepository
from app.domain.services.chanlun_service import normalize_algo_version

logger = logging.getLogger(__name__)


class ChanlunMonitorUseCase:
    """缠论监控扫描（用户自选股维度）。"""

    def __init__(
        self,
        watchlist_repo: WatchlistRepository,
        chanlun_repo: ChanlunRepository,
        algo_version: str,
        session_factory,
        build_calc: Callable[[AsyncSession], ChanlunCalcUseCase],
        concurrency: Optional[int] = None,
        signal_pusher: Optional[Callable[[list[ChanlunSignal]], Awaitable[None]]] = None,
    ):
        self.watchlist_repo = watchlist_repo
        self.chanlun_repo = chanlun_repo
        # 双版本并存：构造器版本归一化（settings 可配 v1/v2/规范串）
        self.algo_version = normalize_algo_version(algo_version)
        self._session_factory = session_factory
        self._build_calc = build_calc
        self.concurrency = concurrency or settings.chanlun_concurrency
        self._progress_cb: Optional[Callable[[dict], Awaitable[None]]] = None
        # 新增信号推送器（微信等）；None = 不推送。推送失败不影响扫描结果。
        self.signal_pusher = signal_pusher

    async def scan(
        self,
        period: str,
        user_id: str,
        trigger_type: str = "scheduled",
        stock_codes: Optional[list[str]] = None,
        progress_cb: Optional[Callable[[dict], Awaitable[None]]] = None,
        algo_version: Optional[str] = None,
    ) -> StrategyRunLog:
        """扫描指定用户的自选股并重算 ``period`` 周期。

        Args:
            period: ``daily`` / ``m30``
            user_id: 触发用户（manual 来自鉴权；scheduled 由调度器注入）
            trigger_type: ``scheduled`` / ``manual``
            stock_codes: 显式指定股票列表（manual 重算可传子集）；None 则取用户全部自选股
            progress_cb: 每股完成后的进度回调（manual SSE 用，推送 ``{stock_code, period, status, reason}``）
            algo_version: 本次扫描生效的算法口径（v1/v2/1.0.0/1.1.0 均可，入口归一化）；
                None 则用构造器版本（定时扫描=settings 默认版）。双版本并存：
                run_log 记生效版本、_is_stale 按版本取快照、信号落 v1/v2 各自的
                dedup_key 分身。
        """
        if algo_version is not None:
            algo_version = normalize_algo_version(algo_version)
        effective_version = algo_version or self.algo_version
        self._progress_cb = progress_cb
        started_at = datetime.now()
        if stock_codes is None:
            items = await self.watchlist_repo.get_all_items_by_user(user_id)
            stock_codes = [it.stock_code for it in items if it.stock_code]
        codes = sorted(set(stock_codes))
        # T051：按逐股监控配置过滤——仅扫描该周期启用的股票；system 调度无配置→全扫
        codes = await self._filter_by_config(codes, period, user_id)

        log = StrategyRunLog(
            period=period,
            trigger_type=trigger_type,
            status="running",
            total=len(codes),
            started_at=started_at,
            algo_version=effective_version,
            user_id=user_id,
        )
        log = await self.chanlun_repo.create_run_log(log)

        sem = asyncio.Semaphore(max(1, self.concurrency))
        results = await asyncio.gather(
            *[self._scan_one(c, period, sem, effective_version) for c in codes]
        )

        success = sum(1 for r in results if r[0] == "success")
        failed = sum(1 for r in results if r[0] == "failed")
        skipped = sum(1 for r in results if r[0] == "skipped")
        failed_detail = [
            {"stock_code": c, "reason": reason}
            for kind, c, reason, *_ in results
            if kind == "failed"
        ]

        finished_at = datetime.now()
        duration_ms = int((finished_at - started_at).total_seconds() * 1000)
        await self.chanlun_repo.finish_run_log(
            log_id=log.id,
            status="done",
            success=success,
            failed=failed,
            failed_detail=failed_detail or None,
            duration_ms=duration_ms,
        )

        # 本批新增信号聚合推送（run_log 收尾后执行，不持任何事务；
        # 双重失败安全：pusher 内部全捕获 + 此处再兜底一层）
        if self.signal_pusher is not None:
            all_new = [s for r in results for s in r[3]]
            if all_new:
                try:
                    await self.signal_pusher(all_new)
                except Exception:
                    logger.warning("缠论信号推送失败（不影响扫描结果）", exc_info=True)

        logger.info(
            "chanlun_monitor[%s/%s]: total=%d success=%d failed=%d skipped=%d (%dms)",
            period, trigger_type, len(codes), success, failed, skipped, duration_ms,
        )
        return StrategyRunLog(
            id=log.id,
            period=period,
            trigger_type=trigger_type,
            status="done",
            total=len(codes),
            success=success,
            failed=failed,
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=duration_ms,
            algo_version=effective_version,
            user_id=user_id,
        )

    async def _scan_one(
        self, code: str, period: str, sem: asyncio.Semaphore,
        algo_version: Optional[str] = None,
    ) -> tuple[str, str, Optional[str], list[ChanlunSignal]]:
        async with sem:
            # 每股独立 session：AsyncSession 非并发安全，gather 并发下不可共享。
            new_signals: list[ChanlunSignal] = []
            async with self._session_factory() as session:
                calc = self._build_calc(session)
                try:
                    if await self._is_stale(
                        calc.chanlun_repo, calc.stock_data_repo, code, period,
                        algo_version,
                    ):
                        logger.info("chanlun_monitor: %s @ %s 无新数据，跳过", code, period)
                        kind, reason = "skipped", "no_new_data"
                    else:
                        _, _, new_signals = await calc.compute_and_persist(
                            code, period, algo_version=algo_version
                        )
                        await session.commit()
                        kind, reason = "success", None
                except NoKlineDataError:
                    await session.rollback()
                    logger.info("chanlun_monitor: %s @ %s 无 K 线数据，跳过", code, period)
                    kind, reason = "skipped", "no_kline_data"
                except Exception as e:  # 单股失败不阻断整体扫描
                    await session.rollback()
                    logger.warning("chanlun_monitor: %s @ %s 计算失败: %s", code, period, e)
                    kind, reason = "failed", str(e)
            if self._progress_cb is not None:
                try:
                    await self._progress_cb(
                        {"stock_code": code, "period": period, "status": kind, "reason": reason}
                    )
                except Exception:
                    logger.debug("chanlun_monitor: progress_cb 失败", exc_info=True)
            return (kind, code, reason, new_signals)

    async def _filter_by_config(
        self, codes: list[str], period: str, user_id: str
    ) -> list[str]:
        """按 ``t_strategy_monitor_config`` 过滤：剔除该周期被用户关闭的股票。

        无配置行的股票视为默认启用；``user_id="system"``（定时调度）通常无配置→不过滤。
        """
        if not codes:
            return codes
        try:
            configs = await self.chanlun_repo.get_monitor_configs(user_id)
        except Exception:
            logger.warning("chanlun_monitor: 读取监控配置失败，按全量扫描", exc_info=True)
            return codes
        if not configs:
            return codes
        cfg_map = {c.stock_code: c for c in configs}
        kept: list[str] = []
        for c in codes:
            cfg = cfg_map.get(c)
            if cfg is None:
                kept.append(c)
                continue
            enabled = cfg.daily_enabled if period == "daily" else cfg.m30_enabled
            if enabled:
                kept.append(c)
        if len(kept) != len(codes):
            logger.info(
                "chanlun_monitor[%s]: 配置过滤 %d→%d（关闭该周期的股票已剔除）",
                period, len(codes), len(kept),
            )
        return kept

    async def _is_stale(
        self,
        chanlun_repo: ChanlunRepository,
        stock_data_repo: StockDataRepository,
        code: str,
        period: str,
        algo_version: Optional[str] = None,
    ) -> bool:
        """结构快照的 ``last_kline_time`` 与当前最新 K 线时间相同 → 无新数据。

        首次计算（无快照）返回 ``False``。``algo_version`` 传入时按该口径取快照
        （双版本并存：v1/v2 快照各自独立一行，水位线互不干扰）；None=不限版本
        （取该股该周期最近一行，兼容旧调用方）。
        """
        snapshot = await chanlun_repo.get_structure(code, period, algo_version)
        if snapshot is None or snapshot.last_kline_time is None:
            return False

        latest = await self._latest_kline_time(stock_data_repo, code, period)
        if latest is None:
            return False
        return latest == snapshot.last_kline_time

    async def _latest_kline_time(
        self, stock_data_repo: StockDataRepository, code: str, period: str
    ) -> Optional[datetime]:
        if period == "m30":
            # 只统计已收盘 K 线（排除 forming 行）：与 chanlun_calc._load_m30_bars
            # 的剔除口径一致，否则快照 last_kline_time（不含 forming）永不相等，
            # 盘中每次扫描都会重算
            return await stock_data_repo.get_latest_kline_30m_time(
                code, closed_before=datetime.now()
            )
        # daily：取最新交易日（date → 当日午夜 datetime）
        quotes = await stock_data_repo.get_daily(code, period="daily")
        if not quotes:
            return None
        latest_date = max(q.trade_date for q in quotes if q.trade_date)
        return datetime(latest_date.year, latest_date.month, latest_date.day)
