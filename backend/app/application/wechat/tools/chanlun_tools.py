"""缠论指令工具（specs/010 US1/US2）。

- ``RunChanlunTool``（slow）：30m/日线补数 → 全量/指定股票缠论重算，复用
  ``chanlun_scheduler.scan_m30`` / ``scan_daily`` 的编排范式与
  ``ChanlunMonitorUseCase.scan``（``trigger_type="manual"`` 与定时扫描溯源区分，
  research D7；日线为 D7 预留的 P2 增强，2026-08-26 落地）；
- ``ChanlunStatusTool``（fast，纯规则）：当前缠论任务进度 / 最近一次结果。
"""

from __future__ import annotations

import asyncio
import logging

from app.application.wechat.tools.base import (
    DISCLAIMER_SUFFIX,
    ToolContext,
    ToolResult,
    WeChatTool,
)
from app.core.config import settings

logger = logging.getLogger(__name__)

# 周期别名归一化：规则层 period_str（日线/日K/30分钟/30m）与 LLM 层 period
# （daily/m30）统一映射到 scan() 的周期标识；缺省 m30（保持既有行为）
_PERIOD_ALIASES = {
    "日线": "daily", "日k": "daily", "daily": "daily",
    "30分钟": "m30", "30m": "m30", "m30": "m30",
}
# 「全部周期」语义（LLM 层 enum 含 all，见 parameters）：等价于不带周期
_PERIOD_ALL = "all"
_PERIOD_LABELS = {"daily": "日线", "m30": "30m"}


async def _all_watchlist_codes(session) -> list[str]:
    """全部用户自选股并集（与 chanlun_scheduler._all_watchlist_codes 一致）。"""
    from sqlalchemy import text as sql_text

    stmt = sql_text(
        "SELECT DISTINCT wi.stock_code FROM t_watchlist_item wi "
        "JOIN t_watchlist_group wg ON wi.group_id = wg.id "
        "WHERE wi.stock_code <> ''"
    )
    result = await session.execute(stmt)
    return sorted({row[0] for row in result.fetchall() if row[0]})


def _build_monitor(session, session_factory):
    """装配 ChanlunMonitorUseCase（对标 chanlun_scheduler._build_monitor）。"""
    from app.application.use_cases.chanlun_calc import ChanlunCalcUseCase
    from app.application.use_cases.chanlun_monitor import ChanlunMonitorUseCase
    from app.application.wechat.chanlun_signal_push import build_signal_pusher
    from app.infrastructure.repositories.mysql_chanlun_repo import MySQLChanlunRepository
    from app.infrastructure.repositories.mysql_stock_data_repo import MySQLStockDataRepository
    from app.infrastructure.repositories.mysql_watchlist_repo import MySQLWatchlistRepository

    def _build_calc(s):
        return ChanlunCalcUseCase(
            stock_data_repo=MySQLStockDataRepository(s),
            chanlun_repo=MySQLChanlunRepository(s),
        )

    return ChanlunMonitorUseCase(
        watchlist_repo=MySQLWatchlistRepository(session),
        chanlun_repo=MySQLChanlunRepository(session),
        algo_version=settings.chanlun_algo_version,
        session_factory=session_factory,
        build_calc=_build_calc,
        signal_pusher=build_signal_pusher(session_factory),
    )


class RunChanlunTool(WeChatTool):
    """跑缠论（US1；日线周期为 D7 预留 P2 增强）。"""

    name = "run_chanlun"
    domain = "strategy"
    description = (
        "对股票执行缠论计算并产出买卖点信号。不带周期时 30m 和日线都算；"
        "也可只指定其一。示例：「跑缠论」全部自选股双周期；「缠论 002940」只算该股"
        "（双周期）；「缠论 日线」或「缠论 30分钟 002940」只跑指定周期；"
        "「帮我把自选股的缠论都过一遍」。"
    )
    parameters = {
        "codes": {
            "type": "array",
            "items": {"type": "string", "pattern": "^\\d{6}$"},
            "description": "股票代码列表；留空则计算全部自选股",
        },
        "period": {
            "type": "string",
            "enum": ["daily", "m30", "all"],
            "description": "K线周期；留空/传 all 时 30m+日线都算；只跑单周期传 daily 或 m30",
        },
    }
    kind = "slow"
    lock_key = "chanlun"
    risk = "read_only"
    usage = "跑缠论 / 缠论 002940 / 缠论 日线"
    # 单条合并 pattern：周期与代码均可选、周期在前（「缠论 002940 日线」语序
    # 不进规则层，交给 LLM 层，FR-005/006 分层设计本意）
    patterns = [
        r"^(?:跑|执行|算)?缠论"
        r"(?:\s+(?P<period_str>日线|日K|30分钟|30m))?"
        r"(?:\s+(?P<codes_str>全部|自选|\d{6}(?:\s*,\s*\d{6})*))?$"
    ]

    async def execute(self, ctx: ToolContext) -> ToolResult:
        from app.application.sync.chanlun_30m_sync import sync_stock_30m
        from app.infrastructure.repositories.mysql_stock_data_repo import (
            MySQLStockDataRepository,
        )

        # 0) 周期归一化：规则层 period_str / LLM 层 period → 周期列表；
        #    不带周期或显式 all = 30m + 日线双跑（用户主诉"怕漏"，默认路径必须
        #    覆盖日线，2026-08-26 修正：此前默认只跑 30m，日线漏算无手动兜底
        #    入口）；非法值回引导文案不执行
        period_raw = str(
            ctx.params.get("period") or ctx.params.get("period_str") or ""
        ).strip().lower()
        if period_raw == _PERIOD_ALL:
            periods = ["m30", "daily"]
        elif period_raw and period_raw not in _PERIOD_ALIASES:
            return ToolResult(summary=(
                f"暂不支持的周期：「{period_raw}」。目前支持「日线」和「30分钟」，"
                "不带周期则两个都算，例如「缠论 日线」或「跑缠论」。"
            ))
        else:
            periods = (
                [_PERIOD_ALIASES[period_raw]] if period_raw else ["m30", "daily"]
            )

        # 1) 目标股票：参数指定 or 自选股并集。
        # 规则层捕获 codes_str（"全部"/"自选"/"002940,000333"），LLM 层产 codes 数组——统一归一化
        codes_raw = ctx.params.get("codes")
        if codes_raw is None:
            codes_str = str(ctx.params.get("codes_str") or "").strip()
            if codes_str and codes_str not in ("全部", "自选", "自选股"):
                codes_raw = [
                    c for c in codes_str.replace("，", ",").replace(" ", ",").split(",") if c
                ]
        if isinstance(codes_raw, str):
            codes_raw = [c for c in codes_raw.replace("，", ",").split(",") if c]
        if codes_raw:
            codes = list(dict.fromkeys(str(c) for c in codes_raw))
        else:
            async with ctx.session_factory() as s:
                codes = await _all_watchlist_codes(s)
        if not codes:
            return ToolResult(summary="自选股为空，先在网页端添加自选股后再试。")

        failed_items: list[dict] = []
        sem = asyncio.Semaphore(max(1, settings.chanlun_concurrency))
        done_box = [0]  # 闭包内可变计数（nonlocal 只到 pull_m30 一层）

        async def pull_m30(codes: list[str]) -> None:
            """30m 逐股补数（对标 scan_m30 内层），逐股报进度。"""
            async def pull(code: str) -> None:
                async with sem:
                    async with ctx.session_factory() as s:
                        try:
                            repo = MySQLStockDataRepository(s)
                            await sync_stock_30m(code, repo)
                            await s.commit()
                        except Exception as e:  # 单股失败不阻断（FR-013 收明细）
                            await s.rollback()
                            logger.warning("微信跑缠论：30m 拉取 %s 失败: %s", code, e)
                            failed_items.append({"code": code, "reason": f"数据拉取失败: {e}"})
                done_box[0] += 1
                await ctx.report_progress(f"{done_box[0]}/{len(codes)}")

            await asyncio.gather(*[pull(c) for c in codes])

        async def pull_daily(codes: list[str]) -> None:
            """日线批量补数（对标 scan_daily 数据前置），进度粗粒度。"""
            from app.infrastructure.scheduler.chanlun_scheduler import _pull_daily_quotes

            await ctx.report_progress("日线补数中…")
            failed = await _pull_daily_quotes(ctx.session_factory, codes)
            for code in failed:
                failed_items.append({"code": code, "reason": "日线数据拉取失败"})
            await ctx.report_progress(
                f"日线补数完成 {len(codes) - len(failed)}/{len(codes)}"
            )

        # 2) + 3) 逐周期：补数 → scan（每轮一条 run_log，摘要逐周期一行）
        #    user_id 传 "wechat"：t_strategy_run_log.user_id 为 String(32)（按系统 uuid
        #    设计），微信 openid 37 字符会 1406；对标定时扫描传 "system" 的先例，
        #    完整溯源（msg_id/原文/微信 user_id）已在 t_wechat_command 记录。
        run_logs: list[tuple[str, object]] = []  # (period_label, run_log)
        failed_before = 0  # 本轮周期开始时 failed_items 已有长度
        for period in periods:
            if period == "daily":
                await pull_daily(codes)
            else:
                await pull_m30(codes)
            # 各周期独立失败集合：30m 拉数失败的股只跳过 30m 轮，日线轮照常算，
            # 反之亦然——只看本轮新增的失败，不累计上一轮的
            failed_now = {f["code"] for f in failed_items[failed_before:]}
            failed_before = len(failed_items)
            ok_codes = [c for c in codes if c not in failed_now]
            if ok_codes:
                async with ctx.session_factory() as session:
                    monitor = _build_monitor(session, ctx.session_factory)
                    log = await monitor.scan(
                        period, user_id="wechat",
                        trigger_type="manual", stock_codes=ok_codes,
                    )
                    await session.commit()
                    run_logs.append((_PERIOD_LABELS[period], log))

        # 4) 摘要（逐周期一行统计 + 免责尾注）
        lines = []
        for label, log in run_logs:
            skipped = log.total - log.success - log.failed
            lines.append(
                f"缠论 {label}计算完成：共 {log.total} 只，"
                f"成功 {log.success}、失败 {log.failed}、无新数据跳过 {skipped}。"
            )
        if not lines:
            summary = f"缠论计算未执行：{len(codes)} 只股票数据全部拉取失败。"
        else:
            summary = "\n".join(lines) + (
                "\n新信号（如有）已单独推送；详情可在网页端信号页查看。"
            )
        return ToolResult(
            summary=summary + DISCLAIMER_SUFFIX,
            succeeded=sum(log.success for _, log in run_logs),
            failed_items=failed_items,
            meta={
                "run_log_ids": [log.id for _, log in run_logs],
            },
        )


class ChanlunStatusTool(WeChatTool):
    """缠论进度/最近结果查询（US2，纯规则保底）。"""

    name = "chanlun_status"
    domain = "strategy"
    description = "查询当前缠论任务进度，或最近一次缠论计算的结果。示例：「缠论状态」"
    parameters = {}
    kind = "fast"
    lock_key = None
    risk = "read_only"
    usage = "缠论状态"
    patterns = [r"^缠论状态$"]

    async def execute(self, ctx: ToolContext) -> ToolResult:
        from app.infrastructure.repositories.mysql_wechat_command_repo import (
            MySQLWeChatCommandRepository,
        )

        async with ctx.session_factory() as s:
            repo = MySQLWeChatCommandRepository(s)
            running = await repo.find_running(user_id=ctx.user_id, exclude_id=ctx.cmd_id)

        if running:
            cur = running[0]
            if cur.progress:
                text = f"正在执行 {cur.tool_name}，进度 {cur.progress}。"
            else:
                text = f"正在执行 {cur.tool_name}，稍等片刻。"
            return ToolResult(summary=text, succeeded=1)

        async with ctx.session_factory() as s:
            repo = MySQLWeChatCommandRepository(s)
            recent = await repo.recent_for_user(ctx.user_id, limit=20, include_closed=True)
        last = next((c for c in recent if c.tool_name == "run_chanlun"), None)
        if last and last.result_summary:
            return ToolResult(summary=f"最近一次缠论计算（{last.status.value}）：\n{last.result_summary[:600]}")
        return ToolResult(summary="当前没有缠论任务在执行，最近也没有缠论计算记录。发「跑缠论」可开始。")
