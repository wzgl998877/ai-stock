"""ChanlunBacktestUseCase — 缠论信号历史回测用例（T042，SC-005 一致性）。

职责：
1. 对每只自选股用**同一** ``ChanlunService``（与监控共用，SC-005）在区间内重算信号；
2. 对每条区间内确认信号计算 5/10/20/60 个交易日窗口收益（窗口越界
   ``window_complete=False``、``ret_*`` 全空，spec 边缘情况）；
3. 按 (period, signal_type, window) 聚合胜率/平均/中位/盈亏比 → 预聚合 summary；
4. 写 report / detail / summary。

输入复用 ``ChanlunCalcUseCase._load_bars`` 保证与监控的 K 线装配完全一致（一致性的
前提是同一输入 + 同一引擎）；本用例不做信号落库（``t_strategy_signal``），回测产物
独立写入回测三表。
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
from statistics import median
from typing import Awaitable, Callable, Optional

from app.application.use_cases.chanlun_calc import ChanlunCalcUseCase
from app.core.config import settings
from app.domain.entities.backtest import (
    BacktestReport,
    BacktestSignalDetail,
    BacktestSummary,
)
from app.domain.entities.chanlun import ChanlunSignal, KlineBar
from app.domain.repositories.backtest_repo import BacktestRepository
from app.domain.services.chanlun_service import ChanlunService

logger = logging.getLogger(__name__)

# 回测观察窗口（与 ``BACKTEST_WINDOWS`` 对齐）
WINDOWS: tuple[int, ...] = (5, 10, 20, 60)

# range_label → 回溯天数（近似按 365 天/年）
RANGE_DAYS: dict[str, int] = {"1y": 365, "3y": 1095, "5y": 1825}

_Q6 = Decimal("0.000001")


def _q6(v: Optional[Decimal]) -> Optional[Decimal]:
    """量化到 DECIMAL(8,6)。"""
    return None if v is None else v.quantize(_Q6)


class ChanlunBacktestUseCase:
    """缠论信号历史回测（与监控共用同一 ``ChanlunService``，SC-005）。"""

    def __init__(
        self,
        chanlun_calc: ChanlunCalcUseCase,
        backtest_repo: BacktestRepository,
        chanlun_service: Optional[ChanlunService] = None,
        algo_version: Optional[str] = None,
    ):
        # 复用 calc 的 K 线装配（同一 IndicatorService/ChanlunService 实例）
        self.chanlun_calc = chanlun_calc
        self.backtest_repo = backtest_repo
        self.chanlun_service = chanlun_service or chanlun_calc.chanlun_service
        self.algo_version = algo_version or chanlun_calc.algo_version

    async def run(
        self,
        user_id: str,
        range_label: str,
        periods: list[str],
        stock_codes: list[str],
        progress_cb: Optional[Callable[[dict], Awaitable[None]]] = None,
    ) -> BacktestReport:
        """对给定股票 + 周期在区间内重算信号并产出回测报告。

        Args:
            range_label: ``1y`` / ``3y`` / ``5y``
            periods: ``["daily"]`` / ``["daily","m30"]`` 等
            stock_codes: 参与股票（router 已解析为自选股或显式列表）
            progress_cb: 每只股票完成回调（SSE ``backtest_progress`` 用）
        """
        days = RANGE_DAYS.get(range_label, RANGE_DAYS["3y"])
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        report = BacktestReport(
            user_id=user_id,
            range_label=range_label,
            start_date=start_date,
            end_date=end_date,
            stock_count=len(stock_codes),
            algo_version=self.algo_version,
            status="running",
        )
        report = await self.backtest_repo.create_report(report)
        report_id = report.report_id  # type: ignore[assignment]

        all_details: list[BacktestSignalDetail] = []
        for code in stock_codes:
            found = 0
            try:
                for period in periods:
                    bars = await self.chanlun_calc._load_bars(code, period)
                    if not bars:
                        continue
                    signals, _snapshot = self.chanlun_service.compute_all(
                        bars, stock_code=code, period=period, algo_version=self.algo_version
                    )
                    details = self._build_details(
                        report_id, code, period, signals, bars, start_date, end_date
                    )
                    all_details.extend(details)
                    found += len(details)
            except Exception as e:  # 单股失败不阻断整体回测
                logger.warning("backtest: %s 计算失败: %s", code, e)
            if progress_cb is not None:
                try:
                    await progress_cb({"stock_code": code, "signals_found": found})
                except Exception:
                    logger.debug("backtest: progress_cb 失败", exc_info=True)

        # 写明细 + 聚合 + 收尾
        await self.backtest_repo.add_signal_details(all_details)
        summaries = self._aggregate(report_id, all_details)
        await self.backtest_repo.upsert_summaries(summaries)

        signal_total = len(all_details)
        # 基准（沪深300）涨跌暂无数据源接入，置 None；schema 允许空
        await self.backtest_repo.finish_report(
            report_id=report_id,
            status="done",
            signal_total=signal_total,
            excluded_invalidated=0,
            benchmark_return=None,
        )
        report.status = "done"
        report.signal_total = signal_total
        report.excluded_invalidated = 0
        logger.info(
            "backtest[%s/%s]: stocks=%d signals=%d summaries=%d",
            range_label, ",".join(periods), len(stock_codes), signal_total, len(summaries),
        )
        return report

    # ------------------------------------------------------------------
    # 明细构造（区间过滤 + 窗口收益）
    # ------------------------------------------------------------------

    def _build_details(
        self,
        report_id: int,
        stock_code: str,
        period: str,
        signals: list[ChanlunSignal],
        bars: list[KlineBar],
        start: date,
        end: date,
    ) -> list[BacktestSignalDetail]:
        """对区间内信号计算窗口收益。

        信号时间取自包含处理后的 K 线时间（原始交易日时间的子集），故可在原始 bars
        的 ``time → index`` 映射中定位；窗口越界（``idx + N`` 超出序列）置空。
        """
        time_to_idx = {b.time: i for i, b in enumerate(bars)}
        details: list[BacktestSignalDetail] = []
        for sig in signals:
            if sig.signal_time is None or sig.trigger_price is None:
                continue
            # signal_time 取自 K 线时间（datetime），取日期用于区间过滤
            try:
                sig_date = sig.signal_time.date()
            except AttributeError:
                sig_date = None
            if sig_date is None or sig_date < start or sig_date > end:
                continue
            idx = time_to_idx.get(sig.signal_time)
            if idx is None:
                logger.debug("backtest: 信号 %s 未匹配到 K 线，跳过", sig.signal_time)
                continue

            rets: dict[int, Optional[Decimal]] = {}
            complete = True
            for n in WINDOWS:
                j = idx + n
                if j < len(bars):
                    close = bars[j].close
                    rets[n] = _q6((close - sig.trigger_price) / sig.trigger_price)
                else:
                    rets[n] = None
                    complete = False

            details.append(
                BacktestSignalDetail(
                    report_id=report_id,
                    stock_code=stock_code,
                    period=period,
                    signal_type=sig.signal_type,
                    structure_level=sig.structure_level,
                    signal_time=sig.signal_time,
                    trigger_price=sig.trigger_price,
                    ret_5=rets[5],
                    ret_10=rets[10],
                    ret_20=rets[20],
                    ret_60=rets[60],
                    window_complete=complete,
                )
            )
        return details

    # ------------------------------------------------------------------
    # 聚合统计
    # ------------------------------------------------------------------

    def _aggregate(
        self, report_id: int, details: list[BacktestSignalDetail]
    ) -> list[BacktestSummary]:
        """按 (period, signal_type, window) 聚合胜率/平均/中位/盈亏比。

        - 样本 < 10 → ``note=sample_insufficient``；
        - 该类型信号总数 > 该窗口有效样本 → ``note=window_incomplete``（近期信号未来窗越界）。

        买卖方视角：明细 ``ret_*`` 永远是真实绝对收益（涨为正、跌为负，与 K 线一致）。
        此处对**卖点**统计量按卖方视角取反——胜率「跌为赢」、avg/中位/盈亏比以
        「卖对方向」为正，使汇总表卖点的胜率/avg 与「卖对=赚」的直觉一致；买点不变。
        """
        by_group: dict[tuple[str, str], list[BacktestSignalDetail]] = defaultdict(list)
        for d in details:
            by_group[(d.period, d.signal_type)].append(d)

        summaries: list[BacktestSummary] = []
        for (period, stype), group in by_group.items():
            total = len(group)
            is_sell = stype.startswith("sell")
            for n in WINDOWS:
                attr = f"ret_{n}"
                raw = [getattr(d, attr) for d in group if getattr(d, attr) is not None]
                sc = len(raw)
                if sc == 0:
                    summaries.append(
                        BacktestSummary(
                            report_id=report_id, period=period, signal_type=stype,
                            window=n, sample_count=0, note="window_incomplete",
                        )
                    )
                    continue

                # 卖点取反：卖方视角下「卖对」= 真实下跌
                samples = [(-r if is_sell else r) for r in raw]

                wins = [r for r in samples if r > 0]
                losses = [r for r in samples if r < 0]
                win_rate = _q6(Decimal(len(wins)) / Decimal(sc))
                avg = _q6(sum(samples) / Decimal(sc))
                med = _q6(median(samples))
                if wins and losses:
                    avg_win = sum(wins) / Decimal(len(wins))
                    avg_loss = abs(sum(losses) / Decimal(len(losses)))
                    plr = _q6(avg_win / avg_loss) if avg_loss != 0 else None
                elif wins and not losses:
                    plr = None  # 无亏损样本，盈亏比无意义
                else:
                    plr = Decimal(0)

                if sc < 10:
                    note = "sample_insufficient"
                elif sc < total:
                    note = "window_incomplete"
                else:
                    note = None

                summaries.append(
                    BacktestSummary(
                        report_id=report_id, period=period, signal_type=stype, window=n,
                        sample_count=sc, win_rate=win_rate, avg_return=avg,
                        median_return=med, profit_loss_ratio=plr, note=note,
                    )
                )
        return summaries
