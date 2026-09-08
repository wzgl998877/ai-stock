"""MySQL Repository 实现缠论策略（模块三）。

对照 ``data-model.md``：信号幂等 upsert（``dedup_key``）、查询、失效标记；
结构快照覆盖式 upsert（``stock_code+period``）；运行日志。
结构对象（``Bi``/``Segment``/``Zhongshu``）序列化为 JSON 存储（宪章允许仅用于结构快照扩展字段）。
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.chanlun import (
    Bi,
    ChanlunSignal,
    Direction,
    Fractal,
    FractalType,
    Segment,
    StructureSnapshot,
    Zhongshu,
)
from app.domain.entities.strategy import MonitorConfig, StrategyRunLog
from app.domain.repositories.chanlun_repo import ChanlunRepository
from app.infrastructure.db.models import (
    StrategyMonitorConfigModel,
    StrategyRunLogModel,
    StrategySignalModel,
    StrategyStructureModel,
)


# ---------------------------------------------------------------------------
# 结构对象 ↔ JSON 序列化
# ---------------------------------------------------------------------------

def _dt_iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat(sep=" ") if dt else None


def _dt_parse(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    return datetime.fromisoformat(s)


def _fractal_to_dict(fr: Fractal) -> dict:
    return {
        "type": fr.type.value,
        "kline_index": fr.kline_index,
        "price": str(fr.price),
        "time": _dt_iso(fr.time),
    }


def _fractal_from_dict(d: dict) -> Fractal:
    return Fractal(
        type=FractalType(d["type"]),
        kline_index=d["kline_index"],
        price=Decimal(d["price"]),
        time=_dt_parse(d["time"]),
    )


def _bi_to_dict(bi: Bi) -> dict:
    return {
        "direction": bi.direction.value,
        "start": _fractal_to_dict(bi.start),
        "end": _fractal_to_dict(bi.end),
        "kline_count": bi.kline_count,
        "confirmed": bi.confirmed,
    }


def _bi_from_dict(d: dict) -> Bi:
    return Bi(
        direction=Direction(d["direction"]),
        start=_fractal_from_dict(d["start"]),
        end=_fractal_from_dict(d["end"]),
        kline_count=d["kline_count"],
        confirmed=d.get("confirmed", True),
    )


def _segment_to_dict(seg: Segment) -> dict:
    return {
        "direction": seg.direction.value,
        "start": _fractal_to_dict(seg.start),
        "end": _fractal_to_dict(seg.end),
        "bi_count": seg.bi_count,
        "confirmed": seg.confirmed,
        "break_type": seg.break_type,
    }


def _segment_from_dict(d: dict) -> Segment:
    return Segment(
        direction=Direction(d["direction"]),
        start=_fractal_from_dict(d["start"]),
        end=_fractal_from_dict(d["end"]),
        bi_count=d["bi_count"],
        confirmed=d.get("confirmed", True),
        break_type=d.get("break_type", ""),
    )


def _zhongshu_to_dict(zs: Zhongshu) -> dict:
    return {
        "zg": str(zs.zg), "zd": str(zs.zd), "gg": str(zs.gg), "dd": str(zs.dd),
        "enter_time": _dt_iso(zs.enter_time), "exit_time": _dt_iso(zs.exit_time),
        "enter_index": zs.enter_index, "state": zs.state,
    }


def _zhongshu_from_dict(d: dict) -> Zhongshu:
    return Zhongshu(
        zg=Decimal(d["zg"]), zd=Decimal(d["zd"]), gg=Decimal(d["gg"]), dd=Decimal(d["dd"]),
        enter_time=_dt_parse(d["enter_time"]), exit_time=_dt_parse(d["exit_time"]),
        enter_index=d.get("enter_index", 0), state=d.get("state", "ended"),
    )


# ---------------------------------------------------------------------------
# 信号 ORM ↔ Entity
# ---------------------------------------------------------------------------

def _signal_to_entity(m: StrategySignalModel) -> ChanlunSignal:
    return ChanlunSignal(
        id=m.id,
        user_id=m.user_id,
        stock_code=m.stock_code,
        period=m.period,
        signal_type=m.signal_type,
        structure_level=m.structure_level,
        signal_time=m.signal_time,
        confirmed_at=m.confirmed_at,
        trigger_price=m.trigger_price,
        status=m.status,
        invalidated_reason=m.invalidated_reason,
        algo_version=m.algo_version,
        dedup_key=m.dedup_key,
        push_status=m.push_status,
        push_message_id=m.push_message_id,
        push_time=m.push_time,
        create_time=m.create_time,
        update_time=m.update_time,
    )


def _run_log_to_entity(m: StrategyRunLogModel) -> StrategyRunLog:
    return StrategyRunLog(
        id=m.id,
        user_id=m.user_id,
        period=m.period,
        trigger_type=m.trigger_type,
        status=m.status,
        total=m.total,
        success=m.success,
        failed=m.failed,
        failed_detail=m.failed_detail,
        started_at=m.started_at,
        finished_at=m.finished_at,
        duration_ms=m.duration_ms,
        algo_version=m.algo_version,
    )


def _config_to_entity(m: StrategyMonitorConfigModel) -> MonitorConfig:
    return MonitorConfig(
        id=m.id,
        user_id=m.user_id,
        stock_code=m.stock_code,
        daily_enabled=bool(m.daily_enabled),
        m30_enabled=bool(m.m30_enabled),
        create_time=m.create_time,
        update_time=m.update_time,
    )


class MySQLChanlunRepository(ChanlunRepository):
    """缠论策略 Repository 的 MySQL 实现。"""

    def __init__(self, session: AsyncSession):
        self.session = session

    # --- 信号 ---

    async def upsert_signals_batch(self, signals: list[ChanlunSignal]) -> list[ChanlunSignal]:
        """幂等批量写入；已存在的 confirmed 信号不覆盖。返回新增的信号实体列表。

        flush 后把自增 ``id`` 回填到实体——下游（微信推送结果回写）需要按 id 定位行。
        """
        if not signals:
            return []
        inserted: list[ChanlunSignal] = []
        added: list[tuple[ChanlunSignal, StrategySignalModel]] = []
        for sig in signals:
            key = sig.dedup_key or sig.make_dedup_key()
            stmt = select(StrategySignalModel).where(StrategySignalModel.dedup_key == key)
            result = await self.session.execute(stmt)
            existing = result.scalar_one_or_none()
            if existing is not None:
                # 已确认信号不重绘；仅当原为 invalidated 不回退
                continue
            model = StrategySignalModel(
                user_id=sig.user_id,
                stock_code=sig.stock_code,
                period=sig.period,
                signal_type=sig.signal_type,
                structure_level=sig.structure_level,
                signal_time=sig.signal_time,
                confirmed_at=sig.confirmed_at,
                trigger_price=sig.trigger_price,
                status=sig.status or "confirmed",
                invalidated_reason=sig.invalidated_reason,
                algo_version=sig.algo_version,
                dedup_key=key,
            )
            self.session.add(model)
            sig.dedup_key = key
            inserted.append(sig)
            added.append((sig, model))
        await self.session.flush()
        for sig, model in added:
            sig.id = model.id
        return inserted

    async def get_signals(
        self,
        stock_code: str,
        period: str,
        status: Optional[str] = None,
        limit: int = 100,
        algo_version: Optional[str] = None,
    ) -> list[ChanlunSignal]:
        conditions = [
            StrategySignalModel.stock_code == stock_code,
            StrategySignalModel.period == period,
        ]
        if status:
            conditions.append(StrategySignalModel.status == status)
        if algo_version:
            conditions.append(StrategySignalModel.algo_version == algo_version)
        stmt = (
            select(StrategySignalModel)
            .where(*conditions)
            .order_by(StrategySignalModel.signal_time.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return [_signal_to_entity(m) for m in result.scalars().all()]

    async def get_latest_signals_for_stocks(
        self, stock_codes: list[str], period: str,
        algo_version: Optional[str] = None,
    ) -> list[ChanlunSignal]:
        """每只股票取最新一条 confirmed 信号（按 signal_time 倒序后去重）。"""
        if not stock_codes:
            return []
        conditions = [
            StrategySignalModel.stock_code.in_(stock_codes),
            StrategySignalModel.period == period,
            StrategySignalModel.status == "confirmed",
        ]
        if algo_version:
            conditions.append(StrategySignalModel.algo_version == algo_version)
        stmt = (
            select(StrategySignalModel)
            .where(*conditions)
            .order_by(StrategySignalModel.signal_time.desc())
        )
        result = await self.session.execute(stmt)
        seen: set[str] = set()
        out: list[ChanlunSignal] = []
        for m in result.scalars().all():
            if m.stock_code in seen:
                continue
            seen.add(m.stock_code)
            out.append(_signal_to_entity(m))
        return out

    async def invalidate_signals(
        self, stock_code: str, period: str, reason: str
    ) -> int:
        stmt = (
            update(StrategySignalModel)
            .where(
                StrategySignalModel.stock_code == stock_code,
                StrategySignalModel.period == period,
                StrategySignalModel.status == "confirmed",
            )
            .values(status="invalidated", invalidated_reason=reason, update_time=datetime.now())
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount or 0

    async def update_push_result(
        self,
        signal_ids: list[int],
        status: str,
        message_id: Optional[str] = None,
    ) -> int:
        """批量回写推送结果；同时落 push_time（对账证据链）。"""
        if not signal_ids:
            return 0
        now = datetime.now()
        stmt = (
            update(StrategySignalModel)
            .where(StrategySignalModel.id.in_(signal_ids))
            .values(
                push_status=status,
                push_message_id=message_id or None,
                push_time=now,
                update_time=now,
            )
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount or 0

    # --- 结构快照 ---

    async def upsert_structure(self, snapshot: StructureSnapshot) -> None:
        stmt = select(StrategyStructureModel).where(
            StrategyStructureModel.stock_code == snapshot.stock_code,
            StrategyStructureModel.period == snapshot.period,
            StrategyStructureModel.algo_version == snapshot.algo_version,
        )
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()
        payload = {
            "strokes_json": [_bi_to_dict(b) for b in snapshot.strokes],
            "segments_json": [_segment_to_dict(s) for s in snapshot.segments],
            "zhongshu_json": [_zhongshu_to_dict(z) for z in snapshot.zhongshu],
            "last_kline_time": snapshot.last_kline_time,
            "algo_version": snapshot.algo_version,
            "update_time": datetime.now(),
        }
        if existing is None:
            self.session.add(
                StrategyStructureModel(
                    stock_code=snapshot.stock_code,
                    period=snapshot.period,
                    **payload,
                )
            )
        else:
            for k, v in payload.items():
                setattr(existing, k, v)
        await self.session.flush()

    async def get_structure(
        self, stock_code: str, period: str, algo_version: Optional[str] = None
    ) -> Optional[StructureSnapshot]:
        conditions = [
            StrategyStructureModel.stock_code == stock_code,
            StrategyStructureModel.period == period,
        ]
        if algo_version:
            conditions.append(StrategyStructureModel.algo_version == algo_version)
        stmt = (
            select(StrategyStructureModel)
            .where(*conditions)
            .order_by(StrategyStructureModel.update_time.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        m = result.scalar_one_or_none()
        if m is None:
            return None
        strokes_raw = m.strokes_json or []
        segments_raw = m.segments_json or []
        zhongshu_raw = m.zhongshu_json or []
        return StructureSnapshot(
            stock_code=m.stock_code,
            period=m.period,
            strokes=[_bi_from_dict(d) for d in strokes_raw],
            segments=[_segment_from_dict(d) for d in segments_raw],
            zhongshu=[_zhongshu_from_dict(d) for d in zhongshu_raw],
            last_kline_time=m.last_kline_time,
            algo_version=m.algo_version,
            update_time=m.update_time,
        )

    # --- 运行日志 ---

    async def create_run_log(self, log: StrategyRunLog) -> StrategyRunLog:
        model = StrategyRunLogModel(
            user_id=log.user_id,
            period=log.period,
            trigger_type=log.trigger_type,
            status=log.status or "running",
            total=log.total,
            started_at=log.started_at or datetime.now(),
            algo_version=log.algo_version,
        )
        self.session.add(model)
        await self.session.flush()
        return _run_log_to_entity(model)

    async def finish_run_log(
        self,
        log_id: int,
        status: str,
        success: int,
        failed: int,
        failed_detail: Optional[list[dict]] = None,
        duration_ms: Optional[int] = None,
    ) -> None:
        stmt = (
            update(StrategyRunLogModel)
            .where(StrategyRunLogModel.id == log_id)
            .values(
                status=status,
                success=success,
                failed=failed,
                failed_detail=failed_detail,
                finished_at=datetime.now(),
                duration_ms=duration_ms,
            )
        )
        await self.session.execute(stmt)
        await self.session.flush()

    async def get_latest_run_log(
        self, period: str, algo_version: Optional[str] = None
    ) -> Optional[StrategyRunLog]:
        conditions = [StrategyRunLogModel.period == period]
        if algo_version:
            conditions.append(StrategyRunLogModel.algo_version == algo_version)
        stmt = (
            select(StrategyRunLogModel)
            .where(*conditions)
            .order_by(StrategyRunLogModel.started_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        m = result.scalar_one_or_none()
        return _run_log_to_entity(m) if m else None

    # --- 监控配置（T050/T051）---

    async def get_monitor_config(
        self, user_id: str, stock_code: str
    ) -> Optional[MonitorConfig]:
        stmt = select(StrategyMonitorConfigModel).where(
            StrategyMonitorConfigModel.user_id == user_id,
            StrategyMonitorConfigModel.stock_code == stock_code,
        )
        result = await self.session.execute(stmt)
        m = result.scalar_one_or_none()
        return _config_to_entity(m) if m else None

    async def get_monitor_configs(self, user_id: str) -> list[MonitorConfig]:
        stmt = select(StrategyMonitorConfigModel).where(
            StrategyMonitorConfigModel.user_id == user_id,
        )
        result = await self.session.execute(stmt)
        return [_config_to_entity(m) for m in result.scalars().all()]

    async def upsert_monitor_config(self, config: MonitorConfig) -> MonitorConfig:
        stmt = select(StrategyMonitorConfigModel).where(
            StrategyMonitorConfigModel.user_id == config.user_id,
            StrategyMonitorConfigModel.stock_code == config.stock_code,
        )
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()
        payload = {
            "daily_enabled": 1 if config.daily_enabled else 0,
            "m30_enabled": 1 if config.m30_enabled else 0,
            "update_time": datetime.now(),
        }
        if existing is None:
            model = StrategyMonitorConfigModel(
                user_id=config.user_id,
                stock_code=config.stock_code,
                **payload,
            )
            self.session.add(model)
        else:
            for k, v in payload.items():
                setattr(existing, k, v)
            model = existing
        await self.session.flush()
        return _config_to_entity(model)

    async def delete_monitor_config(self, user_id: str, stock_code: str) -> int:
        stmt = delete(StrategyMonitorConfigModel).where(
            StrategyMonitorConfigModel.user_id == user_id,
            StrategyMonitorConfigModel.stock_code == stock_code,
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount or 0
