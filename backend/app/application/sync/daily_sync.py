"""日线 K 线增量同步 + 数据到位校验（模块三）。

从 ``chanlun_scheduler``（Infrastructure）迁入——「拉取 → 清洗 → 落库」是应用
流程，与同目录 ``chanlun_30m_sync`` / ``sync_executor`` / ``watchlist_batch_sync``
同构；迁入同时消除了微信工具（Application）反向 import 调度器（Infrastructure）
的分层违规。

2026-09-14 事故背景见 ``app.domain.services.daily_readiness``。本模块两个关键职责：

1. **单轮拉取** :func:`pull_daily_quotes` 返回结构化结果，能区分「两源皆无返回」
   「拉到了但数据没更新」「已到位」——旧实现返回 ``list[str]`` 只表达异常，而
   「新浪空 + 腾讯空」这条路径既不抛异常也不进失败列表，被静默当作成功。
2. **带到位校验的重试** :func:`sync_daily_quotes` 逐轮重拉未到位的股票，直到
   到位或轮数用尽。新浪 456 是 5-60 分钟自解的滚动封禁，收盘后等几轮即可。

增量策略与降级链沿用原实现：库内已有日 K 时窗口从「最近 30 自然日」缩为
「库内最新日期 → 今天」；新浪拉不到（空返回，含被限流）→ 腾讯日 K 兜底。

``upsert_daily_batch`` 只删除批次内日期，故库内 ``max(trade_date)`` 单调不回退
—— :func:`_build_outcome` 据此推断落库后的最新日期，无需额外回读（回读会多一次
DB 往返，并破坏既有测试对每股 session 次数的断言）。
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Awaitable, Callable, Optional, Sequence

from app.core.config import settings
from app.domain.entities.strategy import ScanPreflight
from app.domain.services.daily_readiness import (
    DailyReadinessVerdict,
    expected_daily_date,
    is_daily_data_in_place,
    judge_daily_readiness,
    parse_hhmm,
)

logger = logging.getLogger(__name__)

# 单股 state 三态：到位 / 拉到了但数据没推进 / 拉取或落库失败
STATE_IN_PLACE = "in_place"
STATE_STALE = "stale"
STATE_FAILED = "failed"


@dataclass
class DailyPullOutcome:
    """单股日线拉取结果（诊断粒度）。"""

    code: str
    state: str                                  # in_place / stale / failed
    source: str = ""                            # "sina" / "tencent" / ""=两源皆无返回
    rows_written: int = 0
    latest_date: Optional[date] = None          # 落库后库内最新日 K
    error: str = ""


@dataclass
class DailyPullResult:
    """一轮（或多轮）日线数据前置的汇总结果。"""

    expected_date: date
    total: int
    outcomes: dict[str, DailyPullOutcome] = field(default_factory=dict)
    attempts: int = 1
    verdict: Optional[DailyReadinessVerdict] = None

    @property
    def ready(self) -> bool:
        """是否全部到位。单轮结果（无 verdict）直接按逐股 state 判断。"""
        if self.verdict is not None:
            return self.verdict.ready
        return all(o.state == STATE_IN_PLACE for o in self.outcomes.values())

    @property
    def in_place_codes(self) -> list[str]:
        return [c for c, o in self.outcomes.items() if o.state == STATE_IN_PLACE]

    @property
    def stale_codes(self) -> list[str]:
        return [c for c, o in self.outcomes.items() if o.state == STATE_STALE]

    @property
    def failed_codes(self) -> list[str]:
        return [c for c, o in self.outcomes.items() if o.state == STATE_FAILED]

    def to_preflight(self, max_notes: int = 10) -> ScanPreflight:
        """转成扫描前置诊断（写进 run_log）。

        ``notes`` 刻意保持 ``{stock_code, reason}`` 形状——前端
        ``StrategyMonitorPage`` 按 ``{stock_code}: {reason}`` 渲染且只取前 20 条，
        多出的 ``kind`` 键运行时无害。
        """
        verdict = self.verdict
        if verdict is None or verdict.ready:
            return ScanPreflight(ok=True)

        tail = (
            "疑似数据源故障或非交易日" if verdict.should_retry
            else "孤例未触发重试（疑似停牌/退市）"
        )
        notes: list[dict] = [{
            "stock_code": "数据前置",
            "reason": (
                f"日线数据未到位 {verdict.not_in_place}/{verdict.total}"
                f"（期望 {verdict.expected_date}，重试 {self.attempts} 轮）：{tail}"
            ),
            "kind": "preflight",
        }]
        for code in [*verdict.failed_codes, *verdict.stale_codes][:max_notes]:
            outcome = self.outcomes.get(code)
            if outcome is None:
                continue
            if outcome.state == STATE_FAILED:
                reason = f"日线拉取/落库失败: {outcome.error or 'unknown'}"
            elif outcome.source == "":
                reason = (
                    f"日线数据源无返回（期望 {verdict.expected_date}，"
                    f"库内最新 {outcome.latest_date or '无'}）"
                )
            else:
                reason = (
                    f"日线数据未更新（源={outcome.source}，期望 {verdict.expected_date}，"
                    f"库内最新 {outcome.latest_date or '无'}）"
                )
            notes.append({"stock_code": code, "reason": reason, "kind": "data"})
        return ScanPreflight(ok=False, status="data_stale", notes=notes)


def _is_deadlock(exc: Exception) -> bool:
    """MySQL 死锁 1213（并发先删后插 gap lock 交叉，2026-08-27 全量兜底首跑爆发）。

    死锁牺牲者事务已被 InnoDB 回滚，重跑安全。
    """
    return "1213" in str(exc) or "Deadlock" in str(exc)


async def _fetch_daily_raw(code: str, start: str, end: str) -> tuple[list[dict], str]:
    """拉取原始日 K：新浪 → 腾讯降级。返回 ``(窗口过滤后的行, 数据源)``。

    ``source`` 三态语义（区别于旧实现只返回列表、无法分辨「失败」与「无数据」）：

    - ``"sina"``    —— 新浪有返回，新鲜度由调用方按日期窗口判断；
    - ``"tencent"`` —— 新浪空/被限流，腾讯有返回（**行可能是空列表**，即源是活的
      但窗口内没有新数据——2026-09-14 事故的真实形态）；
    - ``""``        —— 两源都无返回（新浪 456 且腾讯也拿不到），源不可用。

    腾讯无 start/end 参数，返回后按日期窗口过滤。
    """
    from app.application.sync.sina_sync_client import SinaSyncClient
    from app.infrastructure.market.tencent_kline_client import TencentKlineClient

    raw = await asyncio.to_thread(
        SinaSyncClient().fetch_daily_quote,
        code=code, start_date=start, end_date=end, period="daily",
    )
    if raw:
        return raw, "sina"
    logger.info("缠论日线拉取：新浪无数据/被限流，降级腾讯 code=%s", code)
    # 增量缺口换算条数：自然日 → 交易日近似（×5/7）+ 余量；至少 10
    gap_days = (
        datetime.strptime(end, "%Y-%m-%d") - datetime.strptime(start, "%Y-%m-%d")
    ).days
    count = max(10, int(gap_days * 5 / 7) + 5)
    rows = await TencentKlineClient().fetch(code, period="daily", count=count)
    filtered = [r for r in rows if start <= r.get("trade_date", "") <= end]
    return filtered, ("tencent" if rows else "")


async def _upsert_with_deadlock_retry(
    code: str, quotes: list, session_factory
) -> None:
    """落库日 K，MySQL 死锁 1213 重试最多 3 次（牺牲者已回滚，重跑安全）。

    死锁成因：并发「先删后插」在 ``uk_code_date_period`` 相邻 code 边界的 gap
    lock 交叉（封禁断档股索引空洞大、命中不存在行的 DELETE 加 gap 锁 + INSERT
    插入意向锁互等）。

    失败时抛异常，由调用方转成 ``DailyPullOutcome(state="failed")``。
    """
    from app.infrastructure.repositories.mysql_stock_data_repo import (
        MySQLStockDataRepository,
    )

    for attempt in range(3):
        try:
            async with session_factory() as s:
                repo = MySQLStockDataRepository(s)
                try:
                    await repo.upsert_daily_batch(quotes)
                    await s.commit()
                except Exception:
                    # 回滚必须在 session 作用域内：原实现在 session 关闭后调用
                    # rollback()，实际作用于已释放的连接
                    await s.rollback()
                    raise
            return
        except Exception as exc:
            if attempt < 2 and _is_deadlock(exc):
                logger.warning(
                    "缠论日线拉取 %s 死锁重试 %d/3: %s", code, attempt + 1, exc
                )
                await asyncio.sleep(0.5 * (attempt + 1))
                continue
            raise


def _build_outcome(
    code: str,
    latest: Optional[date],
    source: str,
    written: int,
    expected: date,
    quotes: Sequence = (),
) -> DailyPullOutcome:
    """构造单股结果；到位判定用「落库后的库内最新日期」。

    不额外查库：``upsert_daily_batch`` 只删批次内日期，库内 ``max(trade_date)``
    单调不回退，故 ``max(拉取前 latest, 本批 max(trade_date))`` 即落库后的真实
    最新日期。
    """
    observed = latest
    batch_dates = [q.trade_date for q in quotes if getattr(q, "trade_date", None)]
    if batch_dates:
        batch_max = max(batch_dates)
        observed = batch_max if observed is None else max(observed, batch_max)
    state = (
        STATE_IN_PLACE if is_daily_data_in_place(observed, expected) else STATE_STALE
    )
    return DailyPullOutcome(
        code=code,
        state=state,
        source=source,
        rows_written=written,
        latest_date=observed,
    )


async def pull_daily_quotes(
    session_factory,
    codes: list[str],
    days: int = 30,
    *,
    expected: Optional[date] = None,
    concurrency: Optional[int] = None,
) -> DailyPullResult:
    """**单轮**：并发拉取日 K → 清洗 → upsert → 清缓存 → 逐股到位判定。

    每股独立 session（``AsyncSession`` 非并发安全）；单股失败不阻断其他股票。
    增量窗口取「库内最新日期 → 今天」，无历史则用 ``days`` 自然日窗口回补。

    Args:
        expected: 期望的库内最新日 K 日期；None 则按当前时间推算。
    """
    from app.application.sync.sync_executor import _clear_kline_cache
    from app.domain.services.data_cleaner import clean_daily_quote
    from app.infrastructure.repositories.mysql_stock_data_repo import (
        MySQLStockDataRepository,
    )

    now = datetime.now()
    expected = expected or expected_daily_date(
        now, parse_hhmm(settings.chanlun_daily_ready_after)
    )
    end_date = now.date().strftime("%Y-%m-%d")
    default_start = (now.date() - timedelta(days=days)).strftime("%Y-%m-%d")
    sem = asyncio.Semaphore(max(1, concurrency or settings.chanlun_concurrency))

    async def pull(code: str) -> DailyPullOutcome:
        async with sem:
            try:
                async with session_factory() as s:
                    latest = await MySQLStockDataRepository(s).get_latest_daily_date(
                        code, period="daily"
                    )
                start = latest.strftime("%Y-%m-%d") if latest else default_start
                raw, source = await _fetch_daily_raw(code, start, end_date)

                quotes = []
                for r in raw:
                    try:
                        # 来源按实际数据源标记（原实现恒传 "sina"，腾讯降级数据
                        # 也被标成 sina，无法溯源）
                        quotes.append(clean_daily_quote(r, source))
                    except Exception as exc:
                        logger.warning("缠论日线拉取 %s 脏数据跳过: %s", code, exc)

                if not quotes:
                    # 两源皆空 / 全是脏数据 / 窗口内无新行 —— 库内数据未推进，
                    # 正是 2026-09-14 事故的形态：旧实现此分支静默返回成功
                    return _build_outcome(code, latest, source, 0, expected)

                await _upsert_with_deadlock_retry(code, quotes, session_factory)
                await _clear_kline_cache(code, "daily")
                return _build_outcome(
                    code, latest, source, len(quotes), expected, quotes
                )
            except Exception as exc:
                logger.warning("缠论日线拉取 %s 失败: %s", code, exc)
                return DailyPullOutcome(code, STATE_FAILED, error=str(exc))

    results = await asyncio.gather(
        *[pull(c) for c in codes], return_exceptions=True
    )
    outcomes: dict[str, DailyPullOutcome] = {}
    for code, result in zip(codes, results):
        if isinstance(result, BaseException):
            logger.warning("缠论日线拉取 %s 失败: %s", code, result)
            outcomes[code] = DailyPullOutcome(code, STATE_FAILED, error=str(result))
        else:
            outcomes[code] = result

    return DailyPullResult(
        expected_date=expected, total=len(codes), outcomes=outcomes
    )


async def sync_daily_quotes(
    session_factory,
    codes: list[str],
    days: int = 30,
    *,
    now: Optional[datetime] = None,
    max_attempts: Optional[int] = None,
    retry_interval: Optional[float] = None,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> DailyPullResult:
    """带到位校验的日线数据前置（日线扫描用）。

    每轮只重拉上一轮未到位（stale ∪ failed）的股票，已到位的股票不重复拉取。
    停止条件：全部到位 / 未到位只数未达阈值（孤例停牌，不值得空等）/ 轮数用尽。

    ``sleep`` 作为参数注入而非直接调用 ``asyncio.sleep``，便于测试注入 mock
    而不 patch 全局（patch 全局会波及同一事件循环内的其他任务）。
    """
    now = now or datetime.now()
    expected = expected_daily_date(now, parse_hhmm(settings.chanlun_daily_ready_after))
    if not codes:
        return DailyPullResult(expected_date=expected, total=0, attempts=0)

    max_attempts = max(1, max_attempts or settings.chanlun_daily_pull_retry_max)
    interval = (
        retry_interval if retry_interval is not None
        else settings.chanlun_daily_pull_retry_interval_sec
    )

    outcomes: dict[str, DailyPullOutcome] = {}
    pending = list(codes)
    verdict: Optional[DailyReadinessVerdict] = None
    attempts = 0

    for attempt in range(1, max_attempts + 1):
        attempts = attempt
        round_result = await pull_daily_quotes(
            session_factory, pending, days=days, expected=expected
        )
        outcomes.update(round_result.outcomes)
        verdict = judge_daily_readiness(
            total=len(codes),
            stale_codes=[c for c, o in outcomes.items() if o.state == STATE_STALE],
            failed_codes=[c for c, o in outcomes.items() if o.state == STATE_FAILED],
            expected_date=expected,
            stale_ratio_threshold=settings.chanlun_daily_pull_stale_ratio,
            stale_min_count=settings.chanlun_daily_pull_stale_min,
        )
        if verdict.ready or not verdict.should_retry or attempt == max_attempts:
            break
        pending = verdict.retry_codes
        logger.warning(
            "缠论日线数据未到位 %d/%d（期望 %s），%d 秒后第 %d/%d 轮重试：%s",
            verdict.not_in_place, verdict.total, expected, interval,
            attempt + 1, max_attempts, pending[:10],
        )
        await sleep(interval)

    return DailyPullResult(
        expected_date=expected,
        total=len(codes),
        outcomes=outcomes,
        attempts=attempts,
        verdict=verdict,
    )
