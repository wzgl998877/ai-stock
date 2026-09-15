"""缠论信号微信推送用例 + 消息格式化。

推送链路：监控扫描聚合本批新增信号 → ``format_signals_message`` 拼一条消息 →
经 ``ILinkBotClient.send_message`` 发给配置的接收人。

推送结果回写：每次尝试（success / skipped / failed）都把结果与网关返回的
``message_id`` 落到 ``t_strategy_signal``（经 ``result_writer`` 回调，由装配层
建独立 session 完成并 commit）——网关 ret=0 不等于实际送达，表级记录是与
推送日志对账的唯一证据。

失败安全边界：``push`` 全程捕获异常只记 warning——推送失败绝不影响信号落库
主流程（监控层调用点还有一层 try/except 兜底）；推送结果回写失败同样只记
warning。

自动补推（2026-09-15 事故）：iLink 的 ``context_token`` 约 24h 过期，且
``send_text_with_fallback`` 的 tokenless 降级通道**已被网关拒绝**（同样返回
ret=-2），"推送失败即永久丢失"不再可接受。``push_retry`` 把近期未送达
（failed / skipped）的信号按周期与口径分组重发，由 ``build_signal_retrier``
装配、在扫描收尾或 token 刷新时触发。
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta
from typing import Awaitable, Callable, Optional

from app.domain.entities.chanlun import ChanlunSignal
from app.infrastructure.wechat.ilink_client import ILinkBotClient
from app.infrastructure.wechat.ilink_token_store import ILinkTokenStore

logger = logging.getLogger(__name__)

# 名称查找器：给定股票代码列表，返回 {stock_code: stock_name}
NameLookup = Callable[[list[str]], Awaitable[dict[str, str]]]
# 推送结果回写器：(signal_ids, push_status, message_id) → None
PushResultWriter = Callable[[list[int], str, Optional[str]], Awaitable[None]]
# 推送器签名（监控层注入）
SignalPusher = Callable[[list[ChanlunSignal]], Awaitable[None]]
# 补推器签名：一次调用 = 一轮补推，返回本轮尝试条数
SignalRetrier = Callable[[], Awaitable[int]]

SIGNAL_LABELS = {
    "buy1": "一买", "buy2": "二买", "buy3": "三买",
    "sell1": "一卖", "sell2": "二卖", "sell3": "三卖",
}
LEVEL_LABELS = {"stroke": "笔", "segment": "线段"}
PERIOD_LABELS = {"daily": "日线", "m30": "30分钟"}
# 双版本并存（2026-09-08）：标题带口径短标签，区分 v1/v2 推送；未知版本原样回显
VERSION_SHORT_LABELS = {"1.0.0": "v1", "1.1.0": "v2"}

# 补推候选状态：failed=推送尝试失败；skipped=推送时无 context_token。
# 两者都是「未送达、可重试」，故补推时一并作为候选
RETRYABLE_PUSH_STATUSES = ["failed", "skipped"]

# token 刷新后补推的去抖间隔（秒）：用户连打几条消息只补推一次
_TOKEN_RETRY_DEBOUNCE_SEC = 60.0


def format_signals_message(
    new_signals: list[ChanlunSignal], names: Optional[dict[str, str]] = None,
    *, kind: str = "new",
) -> str:
    """把本批信号聚合成一条推送文本（纯函数）。

    按信号时间倒序；名称缺失回退纯代码；末尾固定免责声明（产品定位要求）。

    ``kind="retry"`` 时标题标注「补推」，避免与实时新增混淆（补推的消息可能是
    一天前就该送达的）。
    """
    names = names or {}
    period = new_signals[0].period if new_signals else ""
    period_label = PERIOD_LABELS.get(period, period)
    # 单次 scan 只产单一版本信号，取首条的 algo_version 作口径标签
    version = new_signals[0].algo_version if new_signals else ""
    version_label = VERSION_SHORT_LABELS.get(version, version)
    version_seg = f"·{version_label}" if version_label else ""

    retrying = kind == "retry"
    kind_seg = "·补推" if retrying else ""
    action = "补推" if retrying else "新增"

    ordered = sorted(new_signals, key=lambda s: s.signal_time or datetime.min, reverse=True)
    lines = [f"【缠论信号{version_seg}{kind_seg}】{period_label}周期 · {action}{len(ordered)}"]
    for i, s in enumerate(ordered, 1):
        name = names.get(s.stock_code, "")
        head = f"{s.stock_code} {name}" if name else s.stock_code
        label = SIGNAL_LABELS.get(s.signal_type, s.signal_type)
        level = LEVEL_LABELS.get(s.structure_level, s.structure_level or "")
        price = f"{s.trigger_price:.2f}" if s.trigger_price is not None else ""
        ts = s.signal_time.strftime("%m-%d %H:%M") if s.signal_time else ""
        # 确认时刻晚于信号位置（分型右肩 K 线收盘才可确认，常见于尾盘信号）时
        # 拆两行展示，避免「昨天 15:00 的信号今天才推」的困惑
        need_second_line = (
            s.confirmed_at is not None
            and s.signal_time is not None
            and s.confirmed_at != s.signal_time
        )
        first = f"{i}. {head} {label}"
        if level:
            first += f"({level})"
        parts = [first]
        if price:
            parts.append(price)
        if ts and not need_second_line:
            parts.append(ts)
        lines.append(" ".join(parts))
        if need_second_line:
            confirmed_ts = s.confirmed_at.strftime("%m-%d %H:%M")
            lines.append(f"   信号 {ts} · 确认于 {confirmed_ts}")
    lines.append("—— ai-stock 缠论监控，仅供参考，不构成投资建议")
    return "\n".join(lines)


class ChanlunSignalPushUseCase:
    """缠论新增信号微信推送（单接收人，个人工具场景）。"""

    def __init__(
        self,
        client: ILinkBotClient,
        store: ILinkTokenStore,
        to_user_id: str,
        name_lookup: Optional[NameLookup] = None,
        result_writer: Optional[PushResultWriter] = None,
        max_signal_age_days: Optional[int] = None,
    ):
        self.client = client
        self.store = store
        self.to_user_id = to_user_id
        self.name_lookup = name_lookup
        self.result_writer = result_writer
        self.max_signal_age_days = max_signal_age_days

    async def _record(self, ids: list[int], status: str, message_id: Optional[str]) -> None:
        """回写推送结果；失败只记 warning（不影响任何主流程）。"""
        if self.result_writer is None or not ids:
            return
        try:
            await self.result_writer(ids, status, message_id)
        except Exception:
            logger.warning("推送结果回写失败（status=%s）", status, exc_info=True)

    async def _attempt(self, signals: list[ChanlunSignal], *, kind: str) -> int:
        """单批发送 + 结果回写；返回实际进入发送流程的条数。

        年龄过滤先于取 id：被拦截的信号不推送也不回写（``push_status`` 保持
        NULL=未尝试）。``kind="retry"`` 时无 token **刻意不回写** —— 把候选的
        ``failed`` 洗成 ``skipped`` 会让该信号退出候选集，永远不再补推。
        """
        if not signals:
            return 0

        if self.max_signal_age_days is not None:
            cutoff = datetime.now() - timedelta(days=self.max_signal_age_days)
            fresh = [s for s in signals if s.signal_time and s.signal_time >= cutoff]
            stale = len(signals) - len(fresh)
            if stale:
                logger.info(
                    "推送年龄过滤：%d 条信号超过 %d 天被拦截（不推送、不回写状态）",
                    stale, self.max_signal_age_days,
                )
            if not fresh:
                return 0
            signals = fresh

        ids = [s.id for s in signals if s.id is not None]

        try:
            names: dict[str, str] = {}
            if self.name_lookup is not None:
                try:
                    names = await self.name_lookup(
                        sorted({s.stock_code for s in signals})
                    ) or {}
                except Exception:
                    logger.warning("推送前查询股票名称失败，回退纯代码", exc_info=True)

            context_token = await self.store.get_context_token(self.to_user_id)
            if not context_token:
                logger.warning(
                    "微信推送跳过：无 %s 的 context_token（需接收人先给 bot 发送一条消息激活）",
                    self.to_user_id,
                )
                if kind == "new":
                    await self._record(ids, "skipped", None)
                # 补推路径不回写：保持候选原状，等 token 恢复后重来
                return 0

            text = format_signals_message(signals, names, kind=kind)
            message_id = await self.client.send_text_with_fallback(
                self.to_user_id, text, context_token
            )
            logger.info(
                "缠论信号已推送微信：%d 条%s（message_id=%s）",
                len(signals), "补推" if kind == "retry" else "新增", message_id,
            )
            await self._record(ids, "success", message_id or None)
            return len(signals)
        except Exception:
            logger.warning("缠论信号微信推送失败（不影响信号落库）", exc_info=True)
            await self._record(ids, "failed", None)
            return len(signals)

    async def push(self, new_signals: list[ChanlunSignal]) -> None:
        """聚合推送本批新增信号。任何失败只记日志，不向上抛。"""
        try:
            await self._attempt(new_signals, kind="new")
        except Exception:
            # _attempt 内部已全捕获；此层仅防御未预期异常（如 _record 实现变更）
            logger.warning("缠论信号微信推送失败（不影响信号落库）", exc_info=True)

    async def push_retry(self, pending: list[ChanlunSignal]) -> int:
        """补推未送达信号；按 ``(period, algo_version)`` 分组各发一条。

        分组而非混批的原因：``format_signals_message`` 的标题取自首条信号的
        ``period`` / ``algo_version``，混批会渲染出错误的周期与口径标签。
        单组失败不阻断其他组（``_attempt`` 内部全捕获）。
        """
        if not pending:
            return 0
        groups: dict[tuple[str, str], list[ChanlunSignal]] = {}
        for signal in pending:
            groups.setdefault(
                (signal.period or "", signal.algo_version or ""), []
            ).append(signal)

        sent = 0
        for key in sorted(groups):
            sent += await self._attempt(groups[key], kind="retry")
        return sent


def _build_push_use_case(session_factory) -> Optional[ChanlunSignalPushUseCase]:
    """按 settings 装配推送用例；未启用或未配置返回 ``None``（pusher/retrier 共用）。"""
    from app.core.config import settings

    if (
        not settings.wechat_push_enabled
        or not settings.wechat_ilink_bot_token
        or not settings.wechat_ilink_user_id
    ):
        return None

    client = ILinkBotClient(
        bot_token=settings.wechat_ilink_bot_token,
        base_url=settings.wechat_ilink_base_url,
        client_version=settings.wechat_ilink_client_version,
    )
    uc = ChanlunSignalPushUseCase(
        client=client,
        store=ILinkTokenStore(),
        to_user_id=settings.wechat_ilink_user_id,
        max_signal_age_days=settings.chanlun_push_max_signal_age_days,
    )

    async def _write_push_result(
        ids: list[int], status: str, message_id: Optional[str]
    ) -> None:
        """推送结果回写：独立 session + 显式 commit（写操作规范）。"""
        from app.infrastructure.repositories.mysql_chanlun_repo import (
            MySQLChanlunRepository,
        )

        async with session_factory() as s:
            repo = MySQLChanlunRepository(s)
            await repo.update_push_result(ids, status, message_id)
            await s.commit()

    uc.result_writer = _write_push_result

    async def _lookup_names(codes: list[str]) -> dict[str, str]:
        from sqlalchemy import bindparam, text as sql_text

        async with session_factory() as s:
            result = await s.execute(
                sql_text(
                    "SELECT stock_code, name FROM t_stock WHERE stock_code IN :codes"
                ).bindparams(bindparam("codes", expanding=True)),
                {"codes": codes},
            )
            return {row[0]: row[1] for row in result.fetchall() if row[1]}

    uc.name_lookup = _lookup_names
    return uc


def build_signal_pusher(session_factory) -> Optional[SignalPusher]:
    """按 settings 装配推送器；未启用返回 ``None``（监控层零成本兼容）。

    推送器闭包持有独立资源：查股票名用 ``session_factory`` 建独立 session
    （推送发生在扫描事务提交之后，不复用监控 session）。
    """
    uc = _build_push_use_case(session_factory)
    return uc.push if uc is not None else None


def build_signal_retrier(session_factory) -> Optional[SignalRetrier]:
    """装配「未送达信号补推器」：一次调用 = 一轮补推，返回本轮尝试条数。

    无 ``context_token`` 时直接返回 0，**既不查询也不回写任何状态**——保持
    ``push_status`` 原样（failed / skipped）留作候选，等 token 恢复后重来。
    若此处照常查询并回写 skipped，会把「推送尝试失败」的痕迹洗掉（与日志对账
    时说不清是网关拒绝还是根本没激活），且每轮无谓刷新 ``push_time``。

    触发点：日线扫描收尾（``chanlun_scheduler.run_daily_scan``）、
    入站消息刷新 token 后（``ilink_polling_service``）。
    """
    from app.core.config import settings

    if not settings.chanlun_push_retry_enabled:
        return None
    uc = _build_push_use_case(session_factory)
    if uc is None:
        return None

    async def retry() -> int:
        if not await uc.store.get_context_token(uc.to_user_id):
            logger.info(
                "缠论信号补推跳过：无 context_token（需接收人先给 bot 发消息激活）"
            )
            return 0
        cutoff = datetime.now() - timedelta(days=settings.chanlun_push_retry_window_days)
        from app.infrastructure.repositories.mysql_chanlun_repo import (
            MySQLChanlunRepository,
        )

        async with session_factory() as s:
            pending = await MySQLChanlunRepository(s).get_signals_by_push_status(
                push_statuses=RETRYABLE_PUSH_STATUSES,
                signal_time_from=cutoff,
                limit=settings.chanlun_push_retry_max_signals,
            )
        if not pending:
            return 0
        return await uc.push_retry(pending)

    return retry


def make_token_refresh_hook(
    session_factory,
) -> Optional[Callable[[], Awaitable[None]]]:
    """构造「context_token 刚刷新」回调：补推未送达信号（去抖 + 全捕获）。

    这是 2026-09-15 事故「用户给 bot 发消息激活 token 后，漏推信号补不回来」的
    直接解药——消息到达的这一刻 token 最新鲜，补推成功率最高。

    返回 ``None`` 表示补推未启用/未配置（轮询侧跳过，零成本）。
    """
    retrier = build_signal_retrier(session_factory)
    if retrier is None:
        return None

    last_at = 0.0

    async def hook() -> None:
        nonlocal last_at
        now = time.monotonic()
        if now - last_at < _TOKEN_RETRY_DEBOUNCE_SEC:
            return
        last_at = now
        try:
            sent = await retrier()
            if sent:
                logger.info("token 刷新后补推：本轮尝试 %d 条未送达信号", sent)
        except Exception:
            logger.warning(
                "token 刷新后补推失败（忽略，不影响轮询）", exc_info=True
            )

    return hook
