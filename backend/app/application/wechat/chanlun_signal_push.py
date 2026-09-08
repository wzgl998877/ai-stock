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
"""

from __future__ import annotations

import logging
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

SIGNAL_LABELS = {
    "buy1": "一买", "buy2": "二买", "buy3": "三买",
    "sell1": "一卖", "sell2": "二卖", "sell3": "三卖",
}
LEVEL_LABELS = {"stroke": "笔", "segment": "线段"}
PERIOD_LABELS = {"daily": "日线", "m30": "30分钟"}
# 双版本并存（2026-09-08）：标题带口径短标签，区分 v1/v2 推送；未知版本原样回显
VERSION_SHORT_LABELS = {"1.0.0": "v1", "1.1.0": "v2"}


def format_signals_message(
    new_signals: list[ChanlunSignal], names: Optional[dict[str, str]] = None
) -> str:
    """把本批新增信号聚合成一条推送文本（纯函数）。

    按信号时间倒序；名称缺失回退纯代码；末尾固定免责声明（产品定位要求）。
    """
    names = names or {}
    period = new_signals[0].period if new_signals else ""
    period_label = PERIOD_LABELS.get(period, period)
    # 单次 scan 只产单一版本信号，取首条的 algo_version 作口径标签
    version = new_signals[0].algo_version if new_signals else ""
    version_label = VERSION_SHORT_LABELS.get(version, version)
    version_seg = f"·{version_label}" if version_label else ""

    ordered = sorted(new_signals, key=lambda s: s.signal_time or datetime.min, reverse=True)
    lines = [f"【缠论信号{version_seg}】{period_label}周期 · 新增{len(ordered)}"]
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

    async def push(self, new_signals: list[ChanlunSignal]) -> None:
        """聚合推送本批新增信号。任何失败只记日志，不向上抛。

        ``max_signal_age_days`` 生效时先过滤陈旧信号（signal_time 早于
        now - N 天）：bump algo_version 后首轮全量重算重插会把全部历史信号
        当"新增"送来，年龄过滤把它们拦在推送侧（被剔除者不回写 push_status，
        仍为 NULL=未尝试），避免一次性轰炸接收人。
        """
        try:
            if not new_signals:
                return

            if self.max_signal_age_days is not None:
                cutoff = datetime.now() - timedelta(days=self.max_signal_age_days)
                fresh = [s for s in new_signals if s.signal_time and s.signal_time >= cutoff]
                stale = len(new_signals) - len(fresh)
                if stale:
                    logger.info(
                        "推送年龄过滤：%d 条信号超过 %d 天被拦截（不推送、不回写状态）",
                        stale, self.max_signal_age_days,
                    )
                if not fresh:
                    return
                new_signals = fresh

            # ids 在过滤之后取：被拦截信号不进回写（push_status 保持 NULL）
            ids = [s.id for s in new_signals if s.id is not None]

            names: dict[str, str] = {}
            if self.name_lookup is not None:
                try:
                    names = await self.name_lookup(
                        sorted({s.stock_code for s in new_signals})
                    ) or {}
                except Exception:
                    logger.warning("推送前查询股票名称失败，回退纯代码", exc_info=True)

            context_token = await self.store.get_context_token(self.to_user_id)
            if not context_token:
                logger.warning(
                    "微信推送跳过：无 %s 的 context_token（需接收人先给 bot 发送一条消息激活）",
                    self.to_user_id,
                )
                await self._record(ids, "skipped", None)
                return

            text = format_signals_message(new_signals, names)
            message_id = await self.client.send_text_with_fallback(
                self.to_user_id, text, context_token
            )
            logger.info(
                "缠论信号已推送微信：%d 条新增（message_id=%s）", len(new_signals), message_id
            )
            await self._record(ids, "success", message_id or None)
        except Exception:
            logger.warning("缠论信号微信推送失败（不影响信号落库）", exc_info=True)
            await self._record(ids, "failed", None)


def build_signal_pusher(session_factory) -> Optional[SignalPusher]:
    """按 settings 装配推送器；未启用返回 ``None``（监控层零成本兼容）。

    推送器闭包持有独立资源：查股票名用 ``session_factory`` 建独立 session
    （推送发生在扫描事务提交之后，不复用监控 session）。
    """
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
    return uc.push
