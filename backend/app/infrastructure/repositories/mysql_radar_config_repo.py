"""MySQL RadarConfig Repository"""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.radar_config import RadarConfig
from app.domain.repositories.radar_config_repo import RadarConfigRepository
from app.infrastructure.db.models import RadarConfigModel


def _to_entity(m: RadarConfigModel) -> RadarConfig:
    return RadarConfig(
        id=m.id,
        user_id=m.user_id,
        focused_industries=m.focused_industries,
        event_types=m.event_types,
        alert_sensitivity=m.alert_sensitivity,
        quiet_hours_start=m.quiet_hours_start,
        quiet_hours_end=m.quiet_hours_end,
        updated_at=m.updated_at,
    )


class MySQLRadarConfigRepository(RadarConfigRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_user(self, user_id: str) -> Optional[RadarConfig]:
        stmt = select(RadarConfigModel).where(RadarConfigModel.user_id == user_id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return _to_entity(model) if model else None

    async def create(self, config: RadarConfig) -> RadarConfig:
        model = RadarConfigModel(
            user_id=config.user_id,
            focused_industries=config.focused_industries,
            event_types=config.event_types,
            alert_sensitivity=config.alert_sensitivity,
            quiet_hours_start=config.quiet_hours_start,
            quiet_hours_end=config.quiet_hours_end,
        )
        self.session.add(model)
        await self.session.flush()
        config.id = model.id
        config.updated_at = model.updated_at
        return config

    async def update(self, config: RadarConfig) -> RadarConfig:
        stmt = select(RadarConfigModel).where(RadarConfigModel.user_id == config.user_id)
        result = await self.session.execute(stmt)
        model = result.scalar_one()
        model.focused_industries = config.focused_industries
        model.event_types = config.event_types
        model.alert_sensitivity = config.alert_sensitivity
        model.quiet_hours_start = config.quiet_hours_start
        model.quiet_hours_end = config.quiet_hours_end
        await self.session.flush()
        config.updated_at = model.updated_at
        return config
