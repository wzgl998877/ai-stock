"""add push result fields to t_strategy_signal

Revision ID: k5l6m7n8o9p0
Revises: j4k5l6m7n8o9
Create Date: 2026-08-19 00:00:00.000000

缠论信号微信推送结果落库：push_status（success/skipped/failed，NULL=未尝试）、
push_message_id（iLink 网关受理返回的消息 ID，与推送日志对账用）、push_time。
背景：网关 ret=0 不等于实际送达（存在受理成功但静默丢弃），需要表级证据链。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'k5l6m7n8o9p0'
down_revision: Union[str, None] = 'j4k5l6m7n8o9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('t_strategy_signal', sa.Column('push_status', sa.String(12), nullable=True))
    op.add_column('t_strategy_signal', sa.Column('push_message_id', sa.String(64), nullable=True))
    op.add_column('t_strategy_signal', sa.Column('push_time', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column('t_strategy_signal', 'push_time')
    op.drop_column('t_strategy_signal', 'push_message_id')
    op.drop_column('t_strategy_signal', 'push_status')
