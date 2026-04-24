"""add datasource integration tables and extend stock model

Revision ID: a1b2c3d4e5f6
Revises: f0ec562f649a
Create Date: 2026-04-24 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.mysql import DECIMAL, JSON


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'f0ec562f649a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Extend t_stock with data_source and market_type columns
    op.add_column('t_stock', sa.Column('data_source', sa.String(20), nullable=True, default=''))
    op.add_column('t_stock', sa.Column('market_type', sa.String(20), nullable=True))

    # Create t_datasource_config
    op.create_table(
        't_datasource_config',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('source_type', sa.String(20), nullable=False, unique=True),
        sa.Column('api_key', sa.String(512), nullable=True),
        sa.Column('is_enabled', sa.Boolean, nullable=False, default=True),
        sa.Column('priority', sa.Integer, nullable=False, default=99),
        sa.Column('config_json', JSON, nullable=True),
        sa.Column('create_time', sa.DateTime, nullable=False),
        sa.Column('update_time', sa.DateTime, nullable=False),
        sa.Column('create_user', sa.String(64), nullable=True),
        sa.Column('update_user', sa.String(64), nullable=True),
        sa.Column('deleted', sa.CHAR(1), nullable=False, default='0'),
    )

    # Create t_sync_task
    op.create_table(
        't_sync_task',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('task_id', sa.String(36), nullable=False, unique=True),
        sa.Column('source_type', sa.String(20), nullable=False),
        sa.Column('data_type', sa.String(30), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, default='pending'),
        sa.Column('total_count', sa.Integer, nullable=True),
        sa.Column('processed_count', sa.Integer, nullable=True),
        sa.Column('success_count', sa.Integer, nullable=True),
        sa.Column('fail_count', sa.Integer, nullable=True),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('start_time', sa.DateTime, nullable=True),
        sa.Column('end_time', sa.DateTime, nullable=True),
        sa.Column('duration_ms', sa.Integer, nullable=True),
        sa.Column('create_time', sa.DateTime, nullable=False),
        sa.Index('idx_source_status', 'source_type', 'status'),
        sa.Index('idx_create_time', 'create_time'),
    )

    # Create t_market_quote
    op.create_table(
        't_market_quote',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('code', sa.String(10), nullable=False),
        sa.Column('price', DECIMAL(12, 3), nullable=True),
        sa.Column('change_pct', DECIMAL(8, 2), nullable=True),
        sa.Column('change_amount', DECIMAL(12, 3), nullable=True),
        sa.Column('volume', DECIMAL(18, 0), nullable=True),
        sa.Column('amount', DECIMAL(18, 2), nullable=True),
        sa.Column('open_price', DECIMAL(12, 3), nullable=True),
        sa.Column('high_price', DECIMAL(12, 3), nullable=True),
        sa.Column('low_price', DECIMAL(12, 3), nullable=True),
        sa.Column('pre_close', DECIMAL(12, 3), nullable=True),
        sa.Column('quote_time', sa.DateTime, nullable=False),
        sa.Column('data_source', sa.String(20), nullable=False),
        sa.Column('create_time', sa.DateTime, nullable=False),
        sa.Column('update_time', sa.DateTime, nullable=False),
        sa.UniqueConstraint('code', 'data_source', name='uk_code_source'),
    )

    # Create t_stock_daily_quote
    op.create_table(
        't_stock_daily_quote',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('code', sa.String(10), nullable=False),
        sa.Column('trade_date', sa.Date, nullable=False),
        sa.Column('period', sa.String(10), nullable=False),
        sa.Column('open_price', DECIMAL(12, 3), nullable=True),
        sa.Column('high_price', DECIMAL(12, 3), nullable=True),
        sa.Column('low_price', DECIMAL(12, 3), nullable=True),
        sa.Column('close_price', DECIMAL(12, 3), nullable=True),
        sa.Column('pre_close', DECIMAL(12, 3), nullable=True),
        sa.Column('volume', DECIMAL(18, 0), nullable=True),
        sa.Column('amount', DECIMAL(18, 2), nullable=True),
        sa.Column('pct_chg', DECIMAL(8, 2), nullable=True),
        sa.Column('data_source', sa.String(20), nullable=False),
        sa.Column('create_time', sa.DateTime, nullable=False),
        sa.Column('update_time', sa.DateTime, nullable=False),
        sa.UniqueConstraint('code', 'trade_date', 'data_source', 'period', name='uk_code_date_source_period'),
    )

    # Create t_stock_financial
    op.create_table(
        't_stock_financial',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('code', sa.String(10), nullable=False),
        sa.Column('report_date', sa.Date, nullable=False),
        sa.Column('roe', DECIMAL(8, 2), nullable=True),
        sa.Column('net_profit', DECIMAL(18, 2), nullable=True),
        sa.Column('revenue', DECIMAL(18, 2), nullable=True),
        sa.Column('eps', DECIMAL(8, 4), nullable=True),
        sa.Column('gross_margin', DECIMAL(8, 2), nullable=True),
        sa.Column('debt_ratio', DECIMAL(8, 2), nullable=True),
        sa.Column('data_source', sa.String(20), nullable=False),
        sa.Column('create_time', sa.DateTime, nullable=False),
        sa.Column('update_time', sa.DateTime, nullable=False),
        sa.UniqueConstraint('code', 'report_date', 'data_source', name='uk_code_date_source'),
    )


def downgrade() -> None:
    op.drop_table('t_stock_financial')
    op.drop_table('t_stock_daily_quote')
    op.drop_table('t_market_quote')
    op.drop_table('t_sync_task')
    op.drop_table('t_datasource_config')
    op.drop_column('t_stock', 'market_type')
    op.drop_column('t_stock', 'data_source')
