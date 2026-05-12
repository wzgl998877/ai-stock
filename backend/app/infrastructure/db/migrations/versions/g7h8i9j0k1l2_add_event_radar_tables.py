"""add event radar tables (module 4)

Revision ID: g7h8i9j0k1l2
Revises: f6a7b8c9d0e1
Create Date: 2026-05-11 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.mysql import JSON


revision: str = 'g7h8i9j0k1l2'
down_revision: Union[str, None] = 'f6a7b8c9d0e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. t_impact_event
    op.create_table(
        't_impact_event',
        sa.Column('event_id', sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('summary', sa.String(500), nullable=True),
        sa.Column('event_type', sa.String(20), nullable=True),
        sa.Column('sentiment', sa.String(10), nullable=True),
        sa.Column('importance', sa.String(10), nullable=True),
        sa.Column('affected_industries', JSON, nullable=True),
        sa.Column('affected_stocks', JSON, nullable=True),
        sa.Column('source_count', sa.Integer, nullable=False, server_default='1'),
        sa.Column('first_seen_at', sa.DateTime, nullable=False),
        sa.Column('last_seen_at', sa.DateTime, nullable=False),
        sa.Column('is_active', sa.SmallInteger, nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('NOW()')),
        sa.Index('idx_first_seen', 'first_seen_at'),
        sa.Index('idx_event_type', 'event_type'),
        sa.Index('idx_is_active', 'is_active'),
    )

    # 2. t_impact_article
    op.create_table(
        't_impact_article',
        sa.Column('article_id', sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column('event_id', sa.BigInteger, sa.ForeignKey('t_impact_event.event_id'), nullable=False),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('content', sa.String(500), nullable=True),
        sa.Column('source', sa.String(50), nullable=False),
        sa.Column('url', sa.String(500), nullable=False),
        sa.Column('url_hash', sa.String(32), nullable=False, unique=True),
        sa.Column('published_at', sa.DateTime, nullable=True),
        sa.Column('crawled_at', sa.DateTime, nullable=False, server_default=sa.text('NOW()')),
        sa.Index('idx_url_hash', 'url_hash', unique=True),
        sa.Index('idx_event_id', 'event_id'),
    )

    # 3. t_user_impact
    op.create_table(
        't_user_impact',
        sa.Column('id', sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.String(32), nullable=False),
        sa.Column('event_id', sa.BigInteger, sa.ForeignKey('t_impact_event.event_id'), nullable=False),
        sa.Column('matched_stocks', JSON, nullable=True),
        sa.Column('matched_industries', JSON, nullable=True),
        sa.Column('priority', sa.String(5), nullable=False),
        sa.Column('is_read', sa.SmallInteger, nullable=False, server_default='0'),
        sa.Column('is_alert_sent', sa.SmallInteger, nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('NOW()')),
        sa.Index('idx_user_priority', 'user_id', 'priority'),
        sa.Index('idx_user_read', 'user_id', 'is_read'),
        sa.Index('idx_event_id', 'event_id'),
    )

    # 4. t_user_alert
    op.create_table(
        't_user_alert',
        sa.Column('id', sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.String(32), nullable=False),
        sa.Column('user_impact_id', sa.BigInteger, sa.ForeignKey('t_user_impact.id'), nullable=False),
        sa.Column('priority', sa.String(5), nullable=False),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('summary', sa.String(500), nullable=True),
        sa.Column('is_read', sa.SmallInteger, nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('NOW()')),
        sa.Index('idx_user_read', 'user_id', 'is_read'),
        sa.Index('idx_created', 'created_at'),
    )

    # 5. t_morning_briefing
    op.create_table(
        't_morning_briefing',
        sa.Column('id', sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.String(32), nullable=False),
        sa.Column('briefing_date', sa.Date, nullable=False),
        sa.Column('ai_summary', sa.String(200), nullable=True),
        sa.Column('content', JSON, nullable=False),
        sa.Column('is_read', sa.SmallInteger, nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('NOW()')),
        sa.UniqueConstraint('user_id', 'briefing_date', name='uq_user_briefing_date'),
    )

    # 6. t_radar_config
    op.create_table(
        't_radar_config',
        sa.Column('id', sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.String(32), nullable=False, unique=True),
        sa.Column('focused_industries', JSON, nullable=True),
        sa.Column('event_types', JSON, nullable=True),
        sa.Column('alert_sensitivity', sa.String(10), nullable=False, server_default='medium'),
        sa.Column('quiet_hours_start', sa.Time, nullable=True),
        sa.Column('quiet_hours_end', sa.Time, nullable=True),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.text('NOW()'), onupdate=sa.text('NOW()')),
    )


def downgrade() -> None:
    op.drop_table('t_radar_config')
    op.drop_table('t_morning_briefing')
    op.drop_table('t_user_alert')
    op.drop_table('t_user_impact')
    op.drop_table('t_impact_article')
    op.drop_table('t_impact_event')
