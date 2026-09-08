"""缠论策略监控路由（模块三 US1，T029）。

端点（鉴权 ``Depends(get_current_user)``，所有信号响应附免责声明 FR-016）：
- ``GET  /api/v1/strategy/watchlist-signals``  自选股双周期信号徽标（Redis TTL600）
- ``GET  /api/v1/strategy/stocks/{code}/signals``  单股信号历史（分页、含 invalidated）
- ``POST /api/v1/strategy/recalculate``  SSE 重算进度流（后台解耦 + Queue，范式 A）

价格 Decimal → float 在本路由序列化层完成（T060 宪章数据约束）。
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from decimal import Decimal
from typing import AsyncGenerator, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.dtos.chanlun_dto import (
    FractalDTO,
    MonitorConfigBody,
    MonitorConfigDTO,
    RecalculateRequest,
    RunStatusDTO,
    RunStatusResponse,
    SegmentDTO,
    SignalDTO,
    SignalListResponse,
    SignalMarkDTO,
    SignalSummaryDTO,
    StrokeDTO,
    StructureResponse,
    WatchlistSignalItem,
    WatchlistSignalsResponse,
    ZhongshuDTO,
)
from app.application.use_cases.chanlun_calc import ChanlunCalcUseCase
from app.application.use_cases.chanlun_monitor import ChanlunMonitorUseCase
from app.core.config import settings
from app.core.database import async_session, get_db
from app.core.deps import CurrentUser, get_current_user
from app.domain.entities.chanlun import Bi, ChanlunSignal, Fractal, Segment, Zhongshu
from app.domain.entities.strategy import MonitorConfig
from app.domain.services.chanlun_service import normalize_algo_version
from app.infrastructure.cache.redis_cache import redis_cache
from app.infrastructure.repositories.mysql_chanlun_repo import MySQLChanlunRepository
from app.infrastructure.repositories.mysql_stock_data_repo import MySQLStockDataRepository
from app.infrastructure.repositories.mysql_watchlist_repo import MySQLWatchlistRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/strategy", tags=["strategy"])

WATCHLIST_SIGNALS_TTL = 600
# 信号新鲜度窗口（日历天，纯展示属性）：日K 7 天、30m 2 天，超窗视为「历史信号」
FRESH_WINDOW_DAYS = {"daily": 7, "m30": 2}
# 后台 SSE 任务引用集合，避免被 GC 回收
_bg_tasks: set = set()


# ---------------------------------------------------------------------------
# 序列化助手（Decimal→float、datetime→ISO；T060 宪章数据约束）
# ---------------------------------------------------------------------------

def jsonable(obj):
    """递归把 ``Decimal`` → ``float``、``datetime`` → ISO 字符串，便于 JSON 序列化。"""
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [jsonable(v) for v in obj]
    return obj


def sse(event: str, data: dict) -> str:
    """构造一条 SSE 报文：``event: <type>\\ndata: <json>\\n\\n``。"""
    return f"event: {event}\ndata: {json.dumps(jsonable(data), ensure_ascii=False)}\n\n"


def summary_from_signal(s: Optional[ChanlunSignal], period: str) -> Optional[SignalSummaryDTO]:
    if s is None:
        return None
    return SignalSummaryDTO(
        signal_type=s.signal_type,
        signal_time=s.signal_time,
        confirmed_at=s.confirmed_at,
        trigger_price=s.trigger_price,
        is_fresh=_is_fresh(period, s.signal_time),
    )


def _is_fresh(period: str, signal_time: Optional[datetime]) -> bool:
    """信号新鲜度判定：超出 ``FRESH_WINDOW_DAYS`` 窗口视为历史信号（置灰展示）。"""
    if signal_time is None:
        return False
    window = FRESH_WINDOW_DAYS.get(period, 7)
    return (datetime.now() - signal_time).days <= window


def _resolve_version(version: Optional[str]) -> str:
    """version Query/body 参数 → 规范串；None 用服务端默认版（settings）。

    端点 Query pattern 已限定 ^(v1|v2)$，此处 normalize 不会抛错，
    仅兜底 body 路径（RecalculateRequest 同样有 pattern 校验）。
    """
    if not version:
        return normalize_algo_version(settings.chanlun_algo_version)
    return normalize_algo_version(version)


async def _pull_m30(codes: list[str]) -> None:
    """手动重算 m30 前并发拉取 30m 行情（与调度器 ``scan_m30`` 第一步一致）。

    单股失败仅告警不阻断（可能无该周期行情权限/接口异常）。
    """
    from app.application.sync.chanlun_30m_sync import sync_stock_30m
    from app.infrastructure.repositories.mysql_stock_data_repo import (
        MySQLStockDataRepository,
    )

    sem = asyncio.Semaphore(max(1, settings.chanlun_concurrency))

    async def pull(code: str) -> None:
        async with sem:
            async with async_session() as s:
                try:
                    await sync_stock_30m(code, MySQLStockDataRepository(s))
                    await s.commit()
                except Exception as e:
                    await s.rollback()
                    logger.warning("recalculate: 30m 行情拉取 %s 失败: %s", code, e)

    if codes:
        await asyncio.gather(*[pull(c) for c in codes])


async def _invalidate_strategy_caches(user_id: str) -> None:
    """重算完成后失效徽标与结构缓存，避免用户等待 TTL 才看到新信号。

    双版本并存（2026-09-08）：徽标键含版本段 ``:{ver}``，用前缀 scan 删全部版本。
    """
    try:
        cursor = 0
        while True:
            cursor, keys = await redis_cache.scan(
                cursor, match=f"strategy:watchlist-signals:{user_id}*", count=100
            )
            for k in keys:
                await redis_cache.delete(k)
            if cursor == 0:
                break
        cursor = 0
        while True:
            cursor, keys = await redis_cache.scan(cursor, match="strategy:structure:*", count=100)
            for k in keys:
                await redis_cache.delete(k)
            if cursor == 0:
                break
    except Exception:
        logger.warning("recalculate: 策略缓存失效失败", exc_info=True)


def signal_to_dto(s: ChanlunSignal) -> SignalDTO:
    return SignalDTO(
        id=s.id,
        stock_code=s.stock_code,
        period=s.period,
        signal_type=s.signal_type,
        structure_level=s.structure_level,
        signal_time=s.signal_time,
        confirmed_at=s.confirmed_at,
        trigger_price=s.trigger_price,
        status=s.status,
        invalidated_reason=s.invalidated_reason,
        algo_version=s.algo_version,
        push_status=s.push_status,
        push_message_id=s.push_message_id,
        push_time=s.push_time,
    )


def build_monitor(session: AsyncSession, session_factory) -> ChanlunMonitorUseCase:
    """从主 session 装配监控 UseCase；每股计算用 session_factory 建独立 session。"""

    def _build_calc(s: AsyncSession) -> ChanlunCalcUseCase:
        return ChanlunCalcUseCase(
            stock_data_repo=MySQLStockDataRepository(s),
            chanlun_repo=MySQLChanlunRepository(s),
        )

    # 手动重算同样接入微信推送（settings 未启用时为 None，零成本）
    from app.application.wechat.chanlun_signal_push import build_signal_pusher

    return ChanlunMonitorUseCase(
        watchlist_repo=MySQLWatchlistRepository(session),
        chanlun_repo=MySQLChanlunRepository(session),
        algo_version=settings.chanlun_algo_version,
        session_factory=session_factory,
        build_calc=_build_calc,
        signal_pusher=build_signal_pusher(session_factory),
    )


# ---------------------------------------------------------------------------
# GET /watchlist-signals
# ---------------------------------------------------------------------------

def _latest_signal_time(it: "WatchlistSignalItem") -> datetime:
    """取某只股票「最新一次信号」时间（daily / m30 较新者），无信号返回 ``datetime.min``。

    用于 ``watchlist-signals`` 按信号出现时间排序的 key：刚出信号的股票排最前，
    无信号的排末尾。signal_time 统一转 naive（兼容 DB naive 与带 tz 两种存法）。
    """
    times = [
        t.replace(tzinfo=None) if t is not None else None
        for t in (
            it.daily.signal_time if it.daily else None,
            it.m30.signal_time if it.m30 else None,
        )
    ]
    valid = [t for t in times if t is not None]
    return max(valid) if valid else datetime.min


def _period_status(code, summary, period, cfg_map):
    """结合逐股监控配置推断徽标状态（T055）：关闭→disabled 且隐藏信号。"""
    cfg = cfg_map.get(code)
    if cfg is not None:
        enabled = cfg.daily_enabled if period == "daily" else cfg.m30_enabled
        if not enabled:
            return "disabled", None
    if summary and summary.signal_type:
        return "monitored", summary
    return "monitored_nodata", summary


@router.get("/watchlist-signals")
async def get_watchlist_signals(
    version: Optional[str] = Query(None, pattern="^(v1|v2)$", description="缠论算法口径；缺省用服务端默认版"),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """自选股双周期最新信号徽标（Redis ``strategy:watchlist-signals:{user_id}:{ver}`` TTL600）。

    徽标状态结合逐股监控配置（T055）：周期被关闭→该周期 ``disabled`` 且不返回信号。
    双版本并存：``version`` 指定口径时徽标取该口径下最新一条信号。
    """
    ver = _resolve_version(version)
    cache_key = f"strategy:watchlist-signals:{current_user.user_id}:{ver}"
    cached = await redis_cache.get(cache_key)
    if cached is not None:
        return cached

    wl_repo = MySQLWatchlistRepository(db)
    items = await wl_repo.get_all_items_by_user(current_user.user_id)
    codes = sorted({it.stock_code for it in items if it.stock_code})

    chanlun_repo = MySQLChanlunRepository(db)
    daily = await chanlun_repo.get_latest_signals_for_stocks(codes, "daily", algo_version=ver) if codes else []
    m30 = await chanlun_repo.get_latest_signals_for_stocks(codes, "m30", algo_version=ver) if codes else []
    daily_map = {s.stock_code: s for s in daily}
    m30_map = {s.stock_code: s for s in m30}

    configs = await chanlun_repo.get_monitor_configs(current_user.user_id)
    cfg_map = {c.stock_code: c for c in configs}

    out_items = []
    for it in items:
        if not it.stock_code:
            continue
        d_status, d_summary = _period_status(
            it.stock_code, summary_from_signal(daily_map.get(it.stock_code), "daily"), "daily", cfg_map,
        )
        m_status, m_summary = _period_status(
            it.stock_code, summary_from_signal(m30_map.get(it.stock_code), "m30"), "m30", cfg_map,
        )
        out_items.append(WatchlistSignalItem(
            stock_code=it.stock_code,
            stock_name=it.stock_name,
            daily=d_summary,
            m30=m_summary,
            daily_status=d_status,
            m30_status=m_status,
        ))

    # 按「最新信号时间」降序：daily / m30 取较新者，无信号者排末尾。
    out_items.sort(key=_latest_signal_time, reverse=True)

    response = WatchlistSignalsResponse(items=out_items)
    result = jsonable(response.model_dump())
    await redis_cache.set(cache_key, result, ttl=WATCHLIST_SIGNALS_TTL)
    return result


# ---------------------------------------------------------------------------
# PUT /stocks/{code}/config  +  GET /run-status（T050）
# ---------------------------------------------------------------------------

@router.put("/stocks/{code}/config")
async def update_stock_config(
    code: str,
    body: MonitorConfigBody,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """更新逐股监控开关（daily/m30）；回显更新后配置。

    联动失效该用户徽标缓存（配置变更影响徽标状态，T055）。
    """
    chanlun_repo = MySQLChanlunRepository(db)
    existing = await chanlun_repo.get_monitor_config(current_user.user_id, code)
    config = MonitorConfig(
        user_id=current_user.user_id,
        stock_code=code,
        daily_enabled=body.daily_enabled if body.daily_enabled is not None
        else (existing.daily_enabled if existing else True),
        m30_enabled=body.m30_enabled if body.m30_enabled is not None
        else (existing.m30_enabled if existing else True),
    )
    saved = await chanlun_repo.upsert_monitor_config(config)
    await db.commit()
    # 徽标键含版本段（双版本并存）：前缀 scan 删全部版本
    cursor = 0
    while True:
        cursor, keys = await redis_cache.scan(
            cursor, match=f"strategy:watchlist-signals:{current_user.user_id}*", count=100
        )
        for k in keys:
            await redis_cache.delete(k)
        if cursor == 0:
            break
    return jsonable(MonitorConfigDTO(
        stock_code=saved.stock_code,
        daily_enabled=saved.daily_enabled,
        m30_enabled=saved.m30_enabled,
    ).model_dump())


def _run_log_to_status(log, period: str) -> RunStatusDTO:
    """StrategyRunLog → RunStatusDTO（``last_run_at`` 取 finished_at 回退 started_at）。"""
    if log is None:
        return RunStatusDTO(period=period)
    return RunStatusDTO(
        period=period,
        last_run_at=log.finished_at or log.started_at,
        duration_ms=log.duration_ms,
        total=log.total,
        success=log.success,
        failed=log.failed,
        failed_detail=log.failed_detail,
        algo_version=log.algo_version,
    )


@router.get("/run-status")
async def get_run_status(
    version: Optional[str] = Query(None, pattern="^(v1|v2)$", description="缠论算法口径；缺省用服务端默认版"),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """计算任务状态（日线 / 30m 最近一次运行日志，运行状态卡片用）。

    双版本并存：``version`` 指定口径时展示该口径最近一次运行。
    """
    ver = _resolve_version(version)
    chanlun_repo = MySQLChanlunRepository(db)
    daily_log = await chanlun_repo.get_latest_run_log("daily", algo_version=ver)
    m30_log = await chanlun_repo.get_latest_run_log("m30", algo_version=ver)
    response = RunStatusResponse(
        daily=_run_log_to_status(daily_log, "daily"),
        m30=_run_log_to_status(m30_log, "m30"),
        algo_version=ver,
    )
    return jsonable(response.model_dump())


# ---------------------------------------------------------------------------
# GET /stocks/{code}/signals
# ---------------------------------------------------------------------------
@router.get("/stocks/{code}/signals")
async def get_stock_signals(
    code: str,
    period: str = Query("daily", pattern="^(daily|m30)$"),
    limit: int = Query(50, ge=1, le=200),
    status: Optional[str] = Query(None, description="confirmed / invalidated"),
    version: Optional[str] = Query(None, pattern="^(v1|v2)$", description="缠论算法口径；缺省用服务端默认版"),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """单股信号历史（按 signal_time 倒序，含已失效信号）。"""
    ver = _resolve_version(version)
    chanlun_repo = MySQLChanlunRepository(db)
    sigs = await chanlun_repo.get_signals(code, period, status=status, limit=limit, algo_version=ver)
    items = [signal_to_dto(s) for s in sigs]
    response = SignalListResponse(
        stock_code=code, period=period, items=items,
        total=len(items), page=1, page_size=limit,
    )
    return jsonable(response.model_dump())


# ---------------------------------------------------------------------------
# GET /stocks/{code}/structure  +  /signal-history
# ---------------------------------------------------------------------------

STRUCTURE_TTL = 600


def fractal_to_dto(f: Fractal) -> FractalDTO:
    return FractalDTO(type=f.type.value, kline_index=f.kline_index, price=f.price, time=f.time)


def stroke_to_dto(b: Bi) -> StrokeDTO:
    return StrokeDTO(
        direction=b.direction.value,
        start=fractal_to_dto(b.start),
        end=fractal_to_dto(b.end),
        kline_count=b.kline_count,
        confirmed=b.confirmed,
    )


def segment_to_dto(s: Segment) -> SegmentDTO:
    return SegmentDTO(
        direction=s.direction.value,
        start=fractal_to_dto(s.start),
        end=fractal_to_dto(s.end),
        bi_count=s.bi_count,
        confirmed=s.confirmed,
        break_type=s.break_type,
    )


def zhongshu_to_dto(z: Zhongshu) -> ZhongshuDTO:
    return ZhongshuDTO(
        zg=z.zg, zd=z.zd, gg=z.gg, dd=z.dd,
        enter_time=z.enter_time, exit_time=z.exit_time,
        enter_index=z.enter_index, state=z.state,
    )


def signal_to_mark_dto(s: ChanlunSignal, period: str) -> SignalMarkDTO:
    last = s.signal_type[-1] if s.signal_type else ""
    level = int(last) if last.isdigit() else 0
    return SignalMarkDTO(
        signal_type=s.signal_type,
        time=s.signal_time,
        price=s.trigger_price,
        confirmed_at=s.confirmed_at,
        level=level,
        period=period,
    )


@router.get("/stocks/{code}/structure")
async def get_stock_structure(
    code: str,
    period: str = Query("daily", pattern="^(daily|m30)$"),
    version: Optional[str] = Query(None, pattern="^(v1|v2)$", description="缠论算法口径；缺省用服务端默认版"),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """缠论结构快照 + 买卖点标注（Redis ``strategy:structure:{code}:{period}:{ver}`` TTL600）。

    双版本并存：快照按版本分身（唯一键含 algo_version），``version`` 指定口径；
    该口径无快照时回退最近一行并如实回显其 algo_version（前端可提示先重算）。
    """
    ver = _resolve_version(version)
    cache_key = f"strategy:structure:{code}:{period}:{ver}"
    cached = await redis_cache.get(cache_key)
    if cached is not None:
        return cached

    chanlun_repo = MySQLChanlunRepository(db)
    snapshot = await chanlun_repo.get_structure(code, period, algo_version=ver)
    if snapshot is None:
        # 该口径还没算过：回退任意版本快照（标注仍是旧口径画的，如实回显版本）
        snapshot = await chanlun_repo.get_structure(code, period)
    # 标注信号与快照同口径（回退时跟随快照真实版本，避免结构/标注口径错配）
    mark_ver = (snapshot.algo_version or ver) if snapshot else ver
    sigs = (
        await chanlun_repo.get_signals(code, period, limit=100, algo_version=mark_ver)
        if snapshot else []
    )
    marks = [signal_to_mark_dto(s, period) for s in sigs if s.status == "confirmed"]

    if snapshot is None:
        response = StructureResponse(stock_code=code, period=period, algo_version=ver)
    else:
        response = StructureResponse(
            stock_code=code,
            period=period,
            strokes=[stroke_to_dto(b) for b in snapshot.strokes],
            segments=[segment_to_dto(s) for s in snapshot.segments],
            zhongshu=[zhongshu_to_dto(z) for z in snapshot.zhongshu],
            signal_marks=marks,
            last_kline_time=snapshot.last_kline_time,
            algo_version=snapshot.algo_version or ver,
        )
    result = jsonable(response.model_dump())
    await redis_cache.set(cache_key, result, ttl=STRUCTURE_TTL)
    return result


@router.get("/stocks/{code}/signal-history")
async def get_signal_history(
    code: str,
    period: str = Query("daily", pattern="^(daily|m30)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    status: Optional[str] = Query(None, description="confirmed / invalidated"),
    version: Optional[str] = Query(None, pattern="^(v1|v2)$", description="缠论算法口径；缺省用服务端默认版"),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """单股信号历史（分页、含已失效信号，按 signal_time 倒序）。"""
    ver = _resolve_version(version)
    chanlun_repo = MySQLChanlunRepository(db)
    sigs = await chanlun_repo.get_signals(code, period, status=status, limit=page_size, algo_version=ver)
    items = [signal_to_dto(s) for s in sigs]
    response = SignalListResponse(
        stock_code=code, period=period, items=items,
        total=len(items), page=page, page_size=page_size,
    )
    return jsonable(response.model_dump())


# ---------------------------------------------------------------------------
# POST /recalculate  （SSE，后台解耦 + Queue，范式 A）
# ---------------------------------------------------------------------------

@router.post("/recalculate")
async def recalculate(
    body: RecalculateRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    """触发重算并流式推送进度。

    客户端断开后后台任务继续跑完（信号落库不丢）；进度事件 ``progress``、完成 ``done``、
    异常 ``error``、``heartbeat``（30s 无消息时）。
    """
    periods = ["daily", "m30"] if body.period == "both" else [body.period]
    queue: asyncio.Queue = asyncio.Queue()
    state = {"connected": True}

    async def progress_cb(msg: dict) -> None:
        """monitor 单股结果 → 前端 ``calc_progress``（success→done）。"""
        if state["connected"]:
            await queue.put({
                "event": "calc_progress",
                "data": {
                    "stock_code": msg["stock_code"],
                    "status": "done" if msg["status"] == "success" else msg["status"],
                    "reason": msg["reason"],
                },
            })

    async def background() -> None:
        try:
            async with async_session() as session:
                monitor = build_monitor(session, async_session)
                # 解析目标股票：显式列表优先，否则取用户全部自选股
                if body.stock_codes is not None:
                    codes = sorted(set(body.stock_codes))
                else:
                    wl_repo = MySQLWatchlistRepository(session)
                    items = await wl_repo.get_all_items_by_user(current_user.user_id)
                    codes = sorted({it.stock_code for it in items if it.stock_code})
                if not codes:
                    await queue.put({"event": "data_error", "data": {"message": "未找到自选股，无法重算"}})
                    return
                for p in periods:
                    if p == "m30":
                        # 手动重算不会走调度器的行情拉取，先并发同步 30m K 线再计算，
                        # 否则库中无数据时只会产出空信号（对齐 scheduler.scan_m30 第 1 步）
                        await queue.put({"event": "calc_syncing", "data": {"period": p, "total": len(codes)}})
                        await _pull_m30(codes)
                    await queue.put({"event": "calc_started", "data": {"period": p, "total": len(codes)}})
                    log = await monitor.scan(
                        period=p,
                        user_id=current_user.user_id,
                        trigger_type="manual",
                        stock_codes=codes,
                        progress_cb=progress_cb,
                        algo_version=body.version,
                    )
                    # 新信号已落库：立即失效徽标/结构缓存，不等 TTL
                    await _invalidate_strategy_caches(current_user.user_id)
                    await queue.put({
                        "event": "calc_completed",
                        "data": {
                            "total": log.total,
                            "success": log.success,
                            "failed": log.failed,
                            "duration_ms": log.duration_ms,
                            "algo_version": log.algo_version,
                        },
                    })
                await session.commit()
        except Exception as e:  # 后台异常不冒泡到已返回的响应
            logger.exception("recalculate 后台任务失败")
            await queue.put({"event": "calc_error", "data": {"message": str(e)}})
        finally:
            await queue.put(None)  # sentinel：通知 SSE 生成器结束

    task = asyncio.create_task(background())
    _bg_tasks.add(task)
    task.add_done_callback(_bg_tasks.discard)

    async def event_gen() -> AsyncGenerator[str, None]:
        try:
            while True:
                try:
                    msg = await asyncio.wait_for(queue.get(), timeout=30.0)
                except asyncio.TimeoutError:
                    yield sse("heartbeat", {})
                    continue
                if msg is None:
                    break
                yield sse(msg["event"], msg["data"])
        except asyncio.CancelledError:
            state["connected"] = False
            logger.info("recalculate SSE 客户端断开，后台任务继续")
            raise
        finally:
            state["connected"] = False

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
