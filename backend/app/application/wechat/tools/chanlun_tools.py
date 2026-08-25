"""缠论指令工具（specs/010 US1/US2）。

- ``RunChanlunTool``（slow）：30m 补数 → 全量/指定股票缠论重算，复用
  ``chanlun_scheduler.scan_m30`` 的编排范式与 ``ChanlunMonitorUseCase.scan``
  （``trigger_type="manual"`` 与定时扫描溯源区分，research D7）；
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
    """跑缠论（US1）。"""

    name = "run_chanlun"
    domain = "strategy"
    description = (
        "对股票执行缠论 30 分钟级别计算并产出买卖点信号。"
        "示例：「跑缠论」算全部自选股；「缠论 002940」只算指定股票；"
        "「帮我把自选股的缠论都过一遍」。"
    )
    parameters = {
        "codes": {
            "type": "array",
            "items": {"type": "string", "pattern": "^\\d{6}$"},
            "description": "股票代码列表；留空则计算全部自选股",
        },
    }
    kind = "slow"
    lock_key = "chanlun"
    risk = "read_only"
    usage = "跑缠论 / 缠论 002940"
    patterns = [r"^(?:跑|执行|算)?缠论$", r"^缠论\s+(?P<codes_str>全部|自选|\d{6}(?:\s*,\s*\d{6})*)$"]

    async def execute(self, ctx: ToolContext) -> ToolResult:
        from app.application.sync.chanlun_30m_sync import sync_stock_30m
        from app.infrastructure.repositories.mysql_stock_data_repo import (
            MySQLStockDataRepository,
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
        done = 0

        async def pull(code: str) -> None:
            nonlocal done
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
            done += 1
            await ctx.report_progress(f"{done}/{len(codes)}")

        # 2) 并发补数（对标 scan_m30 内层）
        await asyncio.gather(*[pull(c) for c in codes])

        # 3) 缠论计算（trigger_type="manual" 溯源；跳过补数失败的股票）。
        #    user_id 传 "wechat"：t_strategy_run_log.user_id 为 String(32)（按系统 uuid
        #    设计），微信 openid 37 字符会 1406；对标定时扫描传 "system" 的先例，
        #    完整溯源（msg_id/原文/微信 user_id）已在 t_wechat_command 记录。
        ok_codes = [c for c in codes if c not in {f["code"] for f in failed_items}]
        run_log = None
        if ok_codes:
            async with ctx.session_factory() as session:
                monitor = _build_monitor(session, ctx.session_factory)
                run_log = await monitor.scan(
                    "m30", user_id="wechat",
                    trigger_type="manual", stock_codes=ok_codes,
                )
                await session.commit()

        # 4) 摘要（统计 + 失败明细 + 免责尾注）
        if run_log is None:
            summary = f"缠论计算未执行：{len(codes)} 只股票数据全部拉取失败。"
        else:
            skipped = run_log.total - run_log.success - run_log.failed
            summary = (
                f"缠论 30m 计算完成：共 {run_log.total} 只，"
                f"成功 {run_log.success}、失败 {run_log.failed}、无新数据跳过 {skipped}。\n"
                "新信号（如有）已单独推送；详情可在网页端信号页查看。"
            )
        return ToolResult(
            summary=summary + DISCLAIMER_SUFFIX,
            succeeded=run_log.success if run_log else 0,
            failed_items=failed_items,
            meta={"run_log_id": run_log.id if run_log else None},
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
