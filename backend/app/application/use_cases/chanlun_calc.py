"""ChanlunCalcUseCase — 单股缠论计算用例（对标 ``IndicatorCalcUseCase``）。

职责（胶水层，连接纯函数引擎与持久化）：
1. 读日K（``get_daily``）或 m30K（``get_kline_30m``）；
2. 用 ``IndicatorService.calc_macd`` 现算 MACD BAR 序列并注入 ``KlineBar.macd_bar``
   （背驰判定依赖，见 ``research.md`` D8；日/m30 走同一现算路径，避免 m30 无指标缓存表）；
3. 调 ``ChanlunService.compute_all`` 产出信号 + 结构快照（纯函数，无 IO）；
4. 信号幂等落库（``dedup_key``，已确认信号不覆盖）+ 结构快照覆盖式 upsert。

⚠️ 未收盘 K 线剔除由**监控调度时机**保证（收盘后触发，见 ``chanlun_monitor``）；
   本用例只读取「当前库中最新」序列并计算，不在引擎外重复做收盘判定。
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from app.core.config import settings
from app.domain.entities.chanlun import ChanlunSignal, KlineBar, StructureSnapshot
from app.domain.repositories.chanlun_repo import ChanlunRepository
from app.domain.repositories.stock_data_repo import StockDataRepository
from app.domain.services.chanlun_service import ChanlunService
from app.domain.services.indicator_service import IndicatorService

logger = logging.getLogger(__name__)


class ChanlunCalcUseCase:
    """单股缠论计算 + 落库用例。"""

    def __init__(
        self,
        stock_data_repo: StockDataRepository,
        chanlun_repo: ChanlunRepository,
        indicator_service: Optional[IndicatorService] = None,
        chanlun_service: Optional[ChanlunService] = None,
        algo_version: Optional[str] = None,
    ):
        self.stock_data_repo = stock_data_repo
        self.chanlun_repo = chanlun_repo
        self.indicator_service = indicator_service or IndicatorService()
        self.chanlun_service = chanlun_service or ChanlunService()
        self.algo_version = algo_version or settings.chanlun_algo_version

    async def compute_and_persist(
        self, stock_code: str, period: str
    ) -> tuple[list[ChanlunSignal], StructureSnapshot, int]:
        """计算单股单周期并落库。

        Returns:
            ``(signals, snapshot, added)`` —— 信号列表、结构快照、新增信号条数
            （已存在信号不计；幂等由 ``dedup_key`` 保证）。
        """
        empty_snapshot = StructureSnapshot(
            stock_code=stock_code, period=period, algo_version=self.algo_version
        )
        bars = await self._load_bars(stock_code, period)
        if not bars:
            logger.info("chanlun_calc: 无 K 线数据 %s @ %s", stock_code, period)
            return [], empty_snapshot, 0

        signals, snapshot = self.chanlun_service.compute_all(
            bars, stock_code=stock_code, period=period, algo_version=self.algo_version
        )

        # 监控产出的信号为全局信号（基于行情，所有用户共享），user_id 置空
        for s in signals:
            s.user_id = None
            if s.dedup_key is None:
                s.dedup_key = s.make_dedup_key()

        added = 0
        if signals:
            added = await self.chanlun_repo.upsert_signals_batch(signals)
        await self.chanlun_repo.upsert_structure(snapshot)
        logger.info(
            "chanlun_calc: %s @ %s 产出 %d 信号，新增 %d",
            stock_code, period, len(signals), added,
        )
        return signals, snapshot, added

    # ------------------------------------------------------------------
    # K 线装配
    # ------------------------------------------------------------------

    async def _load_bars(self, stock_code: str, period: str) -> list[KlineBar]:
        if period == "m30":
            return await self._load_m30_bars(stock_code)
        return await self._load_daily_bars(stock_code)

    async def _load_daily_bars(self, stock_code: str) -> list[KlineBar]:
        quotes = await self.stock_data_repo.get_daily(stock_code, period="daily")
        rows = [
            (q.trade_date, q.open_price, q.high_price, q.low_price, q.close_price, q.volume)
            for q in quotes
        ]
        return self._assemble_bars(rows)

    async def _load_m30_bars(self, stock_code: str) -> list[KlineBar]:
        quotes = await self.stock_data_repo.get_kline_30m(stock_code)
        rows = [
            (q.trade_time, q.open_price, q.high_price, q.low_price, q.close_price, q.volume)
            for q in quotes
        ]
        return self._assemble_bars(rows)

    def _assemble_bars(self, rows: list[tuple]) -> list[KlineBar]:
        """将 (time, o, h, l, c, v) 元组序列装配为含 MACD 的 ``KlineBar`` 序列。

        OHLC 任一为空的脏数据行直接丢弃；MACD BAR 在过滤后的 close 序列上现算，
        与 K 线按下标一一对齐。
        """
        clean: list[tuple] = []
        for t, o, h, l, c, v in rows:
            if c is None or o is None or h is None or l is None:
                continue
            clean.append(
                (
                    self._to_datetime(t),
                    Decimal(str(o)),
                    Decimal(str(h)),
                    Decimal(str(l)),
                    Decimal(str(c)),
                    Decimal(str(v)) if v is not None else Decimal(0),
                )
            )
        if not clean:
            return []

        closes = [r[4] for r in clean]
        _, _, macd_bars = self.indicator_service.calc_macd(closes)

        bars: list[KlineBar] = []
        for i, (tt, o, h, l, c, v) in enumerate(clean):
            mb = macd_bars[i] if i < len(macd_bars) else None
            bars.append(
                KlineBar(time=tt, open=o, high=h, low=l, close=c, volume=v, macd_bar=mb, index=i)
            )
        return bars

    @staticmethod
    def _to_datetime(t) -> datetime:
        """日线 ``trade_date`` 是 ``date``，需转当日午夜 ``datetime``；m30 已是 ``datetime``。"""
        if isinstance(t, datetime):
            return t
        if isinstance(t, date):
            return datetime(t.year, t.month, t.day)
        # 容错：字符串时间戳
        if isinstance(t, str):
            return datetime.fromisoformat(t)
        return t
