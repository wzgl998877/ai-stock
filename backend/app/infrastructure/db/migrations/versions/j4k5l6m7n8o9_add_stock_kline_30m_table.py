"""add t_stock_kline_30m table (module 3 chanlun 30m kline)

Revision ID: j4k5l6m7n8o9
Revises: i3j4k5l6m7n8
Create Date: 2026-08-05 00:00:00.000000

独立 30 分钟 K 线表。research.md D1 原定复用 t_stock_daily_quote(period='m30')，
但该表 trade_date 为 DATE、无法区分同日 8 根 30m，故改用独立表（见 memory
chanlun-30m-storage-decision）。trade_time 存区间结束时刻（10:00/10:30/.../15:00）。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.mysql import DECIMAL


revision: str = 'j4k5l6m7n8o9'
down_revision: Union[str, None] = 'i3j4k5l6m7n8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        't_stock_kline_30m',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('code', sa.String(10), nullable=False),
        sa.Column('trade_time', sa.DateTime, nullable=False),
        sa.Column('open_price', DECIMAL(precision=12, scale=3), nullable=True),
        sa.Column('high_price', DECIMAL(precision=12, scale=3), nullable=True),
        sa.Column('low_price', DECIMAL(precision=12, scale=3), nullable=True),
        sa.Column('close_price', DECIMAL(precision=12, scale=3), nullable=True),
        sa.Column('volume', DECIMAL(precision=18, scale=0), nullable=True),
        sa.Column('amount', DECIMAL(precision=18, scale=2), nullable=True),
        sa.Column('data_source', sa.String(20), nullable=False),
        sa.Column('create_time', sa.DateTime, nullable=False, server_default=sa.text('NOW()')),
        sa.Column('update_time', sa.DateTime, nullable=False, server_default=sa.text('NOW()'), onupdate=sa.text('NOW()')),
        sa.UniqueConstraint('code', 'trade_time', 'data_source', name='uk_code_time_source_30m'),
        sa.Index('idx_k30m_code_time', 'code', 'trade_time'),
    )


def downgrade() -> None:
    op.drop_table('t_stock_kline_30m')
