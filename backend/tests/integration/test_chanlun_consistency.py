"""监控 vs 回测 一致性集成测试（T044，SC-005）。

SC-005 要求：对同一股票同一区间，监控增量结果与回测全量结果 100% 一致。物理保证是
两者复用同一 ``ChanlunService.compute_all`` + 同一 ``ChanlunCalcUseCase._load_bars``。
本测试用合成 K 线跑通两条完整管线（监控 ``compute_and_persist`` / 回测 ``run``），断言
产出的信号集合（signal_type, signal_time, trigger_price）完全相等。

自包含：仅用 Fake 仓储，不需要运行中的数据库。
"""

from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

import pytest

from app.application.use_cases.chanlun_backtest import ChanlunBacktestUseCase
from app.application.use_cases.chanlun_calc import ChanlunCalcUseCase
from app.domain.entities.backtest import BacktestReport, BacktestSignalDetail, BacktestSummary
from app.domain.entities.chanlun import StructureSnapshot
from app.domain.models.stock_data import StockDailyQuote
from tests.unit.application.test_chanlun_calc import FakeChanlunRepo, FakeStockDataRepo

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------

class FakeBacktestRepo:
    """内存回测仓储：仅记录写入的明细/汇总，供一致性比对。"""

    def __init__(self):
        self._seq = 0
        self.details: list[BacktestSignalDetail] = []
        self.summaries: list[BacktestSummary] = []
        self.report: Optional[BacktestReport] = None

    async def create_report(self, report: BacktestReport) -> BacktestReport:
        self._seq += 1
        report.report_id = self._seq
        self.report = report
        return report

    async def finish_report(self, report_id, status, signal_total, excluded_invalidated, benchmark_return):
        if self.report:
            self.report.status = status
            self.report.signal_total = signal_total

    async def add_signal_details(self, details):
        self.details.extend(details)

    async def upsert_summaries(self, summaries):
        self.summaries.extend(summaries)


# ---------------------------------------------------------------------------
# 合成「近期」日 K（锚定今天，确保落在 1y/3y/5y 区间内）
# ---------------------------------------------------------------------------

def _recent_daily(n: int = 120) -> list[StockDailyQuote]:
    """n 根「涨-跌-涨」日 K，base = 今天 - n 天，使全部 bar 落入任意回测区间。"""
    base = date.today() - timedelta(days=n + 5)
    seg = n // 3
    closes = []
    for i in range(n):
        if i < seg:
            closes.append(Decimal(10) + Decimal(i) * Decimal("0.3"))
        elif i < 2 * seg:
            closes.append(Decimal(10) + Decimal(seg) * Decimal("0.3") - Decimal(i - seg) * Decimal("0.3"))
        else:
            closes.append(Decimal(10) + Decimal(i - 2 * seg) * Decimal("0.3"))
    return [
        StockDailyQuote(
            code="600000", trade_date=base + timedelta(days=i), period="daily",
            open_price=c - Decimal("0.1"), high_price=c + Decimal("0.2"),
            low_price=c - Decimal("0.2"), close_price=c, volume=Decimal(1000),
        )
        for i, c in enumerate(closes)
    ]


def _sig_key(s):
    """一致性比对键：(signal_type, signal_time, trigger_price)。"""
    return (s.signal_type, s.signal_time, s.trigger_price)


# ---------------------------------------------------------------------------
# 测试
# ---------------------------------------------------------------------------

async def test_monitor_and_backtest_produce_identical_signals():
    """SC-005：同一合成股票，监控与回测产出的信号集合 100% 一致。"""
    data = _recent_daily(150)

    # --- 监控管线 ---
    monitor_calc = ChanlunCalcUseCase(FakeStockDataRepo(daily=data), FakeChanlunRepo(), algo_version="1.0.0")
    monitor_signals, _snapshot, _added = await monitor_calc.compute_and_persist("600000", "daily")

    # --- 回测管线（独立实例，同一输入数据） ---
    bt_repo = FakeBacktestRepo()
    bt_calc = ChanlunCalcUseCase(FakeStockDataRepo(daily=data), FakeChanlunRepo(), algo_version="1.0.0")
    bt = ChanlunBacktestUseCase(chanlun_calc=bt_calc, backtest_repo=bt_repo)
    await bt.run(
        user_id="u1", range_label="5y", periods=["daily"],
        stock_codes=["600000"],
    )

    monitor_keys = {_sig_key(s) for s in monitor_signals}
    backtest_keys = {_sig_key(d) for d in bt_repo.details}

    # 两端要么都为空（合成数据未触发信号），要么完全相等（SC-005）
    if monitor_keys or backtest_keys:
        assert monitor_keys == backtest_keys, (
            f"监控与回测信号不一致：仅监控={monitor_keys - backtest_keys}，"
            f"仅回测={backtest_keys - monitor_keys}"
        )

    # 回测明细全部落在请求区间内（区间过滤生效）
    end = date.today()
    start = end - timedelta(days=1825)  # 5y
    for d in bt_repo.details:
        sd = d.signal_time.date()
        assert start <= sd <= end


async def test_backtest_summary_consistent_with_details():
    """汇总的样本数 ≤ 明细总数，且每个聚合组的样本均可溯源到明细。"""
    data = _recent_daily(150)
    bt_repo = FakeBacktestRepo()
    bt_calc = ChanlunCalcUseCase(FakeStockDataRepo(daily=data), FakeChanlunRepo(), algo_version="1.0.0")
    bt = ChanlunBacktestUseCase(chanlun_calc=bt_calc, backtest_repo=bt_repo)
    await bt.run(user_id="u1", range_label="3y", periods=["daily"], stock_codes=["600000"])

    # 每个 summary 的 sample_count 不超过对应 (period, signal_type) 的明细数
    from collections import defaultdict
    detail_cnt = defaultdict(int)
    for d in bt_repo.details:
        detail_cnt[(d.period, d.signal_type)] += 1
    for s in bt_repo.summaries:
        assert s.sample_count <= detail_cnt.get((s.period, s.signal_type), 0)
