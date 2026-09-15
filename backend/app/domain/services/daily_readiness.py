"""日线数据到位判定（纯函数：无 IO、不依赖 settings）。

2026-09-14 事故：15:40 日线扫描时新浪返回 HTTP 456（IP 被限流），降级腾讯虽有
返回但数据未更新，日期窗口过滤后零新行入库 → 库内最新日 K 不变 → 扫描层
``_is_stale`` 把 41 只股票全判为「无新数据」跳过 → run_log 记
``status='done', success=0, failed=0``，全链路无任何告警。数据侧铁证：
``t_stock_daily_quote`` 的 ``create_time`` 分布里当天完全缺席。

本模块提供「数据是否到位」的判定规则，供 Application 层的数据前置流程决定
是否重试、并把诊断写进 run_log。判定规则是业务规则（而非技术细节），故放
Domain，保证零 mock 可单测。
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

# A 股 15:00 收盘，行情源日 K 通常 15:00-15:05 落定。早于该时刻运行（如上午
# 手动重算）时当日 K 线尚未产生，期望日期须回退上一工作日，否则每次盘中运行
# 都会误判未到位而白跑重试。
CLOSE_SETTLED = time(15, 5)


def parse_hhmm(raw: str, default: time = CLOSE_SETTLED) -> time:
    """``"15:05"`` → ``time(15, 5)``；非法值回落 ``default``（配置容错）。"""
    try:
        hour, minute = raw.split(":")
        return time(int(hour), int(minute))
    except Exception:
        return default


def prev_weekday(d: date) -> date:
    """``d`` 之前最近的一个工作日（不含 ``d`` 本身）。"""
    cur = d - timedelta(days=1)
    while cur.weekday() >= 5:
        cur -= timedelta(days=1)
    return cur


def expected_daily_date(now: datetime, ready_after: time = CLOSE_SETTLED) -> date:
    """期望的「库内最新日 K 日期」。

    - 工作日 且已过 ``ready_after`` → 今天；
    - 工作日 但早于 ``ready_after`` → 上一工作日；
    - 周末 → 最近的工作日（周五）。

    已知局限：项目无交易日历，节假日（国庆/春节）会被判为「应有数据」，
    只能靠 :func:`judge_daily_readiness` 的大面积阈值 + 重试轮数上限兜底，
    代价是每个节假日多等几轮（纯后台等待，不影响其他任务）。
    """
    if now.weekday() >= 5:
        return prev_weekday(now.date())
    if now.time() >= ready_after:
        return now.date()
    return prev_weekday(now.date())


def is_daily_data_in_place(latest: date | None, expected: date) -> bool:
    """库内最新日 K 是否已推进到期望日期（``None`` = 该股无任何数据 → 未到位）。"""
    return latest is not None and latest >= expected


@dataclass(frozen=True)
class DailyReadinessVerdict:
    """一轮拉取后的数据到位判定结果。"""

    ready: bool                    # 全部到位 → 可停止重试
    should_retry: bool             # 大面积未到位 → 值得等待重试
    expected_date: date
    total: int
    in_place: int
    stale_codes: tuple[str, ...]   # 拉到了但日期没推进到 expected
    failed_codes: tuple[str, ...]  # 拉取异常 / 落库失败
    threshold: int                 # 本轮触发重试的未到位只数阈值

    @property
    def retry_codes(self) -> list[str]:
        """下一轮需要重拉的股票（未到位 ∪ 拉取失败）。"""
        return [*self.stale_codes, *self.failed_codes]

    @property
    def not_in_place(self) -> int:
        return len(self.stale_codes) + len(self.failed_codes)


def judge_daily_readiness(
    *,
    total: int,
    stale_codes: list[str],
    failed_codes: list[str],
    expected_date: date,
    stale_ratio_threshold: float = 0.3,
    stale_min_count: int = 2,
) -> DailyReadinessVerdict:
    """逐股判断 + 大面积故障阈值。

    单只股票停牌/退市不该被误判为「数据源故障」而触发重试，故只有未到位只数
    达到阈值才 ``should_retry=True``：

    - ``total <= stale_min_count``：阈值退化为 ``total``（1-2 只的自选股若不
      退化，``stale_min_count`` 比 ``total`` 还大，会永远不重试）；
    - 常规：``max(stale_min_count, ceil(ratio * total))``。

    ``ready``（可否停止）与 ``should_retry``（是否值得等待）刻意分开：孤例停牌
    → ``ready=False, should_retry=False``，不空等，但仍写诊断。
    """
    stale_codes = list(stale_codes)
    failed_codes = list(failed_codes)
    not_in_place = len(stale_codes) + len(failed_codes)

    if total <= stale_min_count:
        threshold = total
    else:
        threshold = max(stale_min_count, math.ceil(stale_ratio_threshold * total))

    ready = not_in_place == 0
    should_retry = not ready and total > 0 and not_in_place >= threshold

    return DailyReadinessVerdict(
        ready=ready,
        should_retry=should_retry,
        expected_date=expected_date,
        total=total,
        in_place=max(0, total - not_in_place),
        stale_codes=tuple(stale_codes),
        failed_codes=tuple(failed_codes),
        threshold=threshold,
    )
