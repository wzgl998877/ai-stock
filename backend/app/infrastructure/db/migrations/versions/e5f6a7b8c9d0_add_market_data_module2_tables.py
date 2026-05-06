"""add market data module2 tables

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-05-06 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.mysql import DECIMAL


# revision identifiers, used by Alembic.
revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -----------------------------------------------------------------------
    # 1. 扩展 t_stock 表：增加行业和市值字段
    # -----------------------------------------------------------------------
    op.add_column(
        't_stock',
        sa.Column('industry_code', sa.String(10), nullable=True),
    )
    op.add_column(
        't_stock',
        sa.Column('industry_name', sa.String(50), nullable=True),
    )
    op.add_column(
        't_stock',
        sa.Column('total_market_cap', DECIMAL(18, 2), nullable=True),
    )
    op.add_column(
        't_stock',
        sa.Column('float_market_cap', DECIMAL(18, 2), nullable=True),
    )

    # -----------------------------------------------------------------------
    # 2. 扩展 t_market_quote 表：增加估值字段
    # -----------------------------------------------------------------------
    op.add_column(
        't_market_quote',
        sa.Column('pe_ttm', DECIMAL(10, 2), nullable=True),
    )
    op.add_column(
        't_market_quote',
        sa.Column('pb', DECIMAL(10, 2), nullable=True),
    )

    # -----------------------------------------------------------------------
    # 3. 创建 t_watchlist_group 表
    # -----------------------------------------------------------------------
    op.create_table(
        't_watchlist_group',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.String(64), nullable=False),
        sa.Column('name', sa.String(10), nullable=False),
        sa.Column('display_order', sa.Integer, nullable=False, server_default='0'),
        sa.Column('is_default', sa.Boolean, nullable=False, server_default='0'),
        sa.Column('create_time', sa.DateTime, nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('update_time', sa.DateTime, nullable=False, server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP')),
    )
    op.create_index('idx_wg_user_id', 't_watchlist_group', ['user_id'])

    # -----------------------------------------------------------------------
    # 4. 创建 t_watchlist_item 表
    # -----------------------------------------------------------------------
    op.create_table(
        't_watchlist_item',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('group_id', sa.Integer, sa.ForeignKey('t_watchlist_group.id', ondelete='CASCADE'), nullable=False),
        sa.Column('stock_code', sa.String(10), nullable=False),
        sa.Column('stock_name', sa.String(50), nullable=False),
        sa.Column('add_time', sa.DateTime, nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('create_time', sa.DateTime, nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    op.create_unique_constraint('uk_group_stock', 't_watchlist_item', ['group_id', 'stock_code'])
    op.create_index('idx_wi_group_id', 't_watchlist_item', ['group_id'])
    op.create_index('idx_wi_stock_code', 't_watchlist_item', ['stock_code'])

    # -----------------------------------------------------------------------
    # 5. 创建 t_stock_indicator 表
    # -----------------------------------------------------------------------
    op.create_table(
        't_stock_indicator',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('stock_code', sa.String(10), nullable=False),
        sa.Column('trade_date', sa.Date, nullable=False),
        sa.Column('period', sa.String(10), nullable=False, server_default='daily'),
        sa.Column('macd_dif', DECIMAL(12, 4), nullable=True),
        sa.Column('macd_dea', DECIMAL(12, 4), nullable=True),
        sa.Column('macd_bar', DECIMAL(12, 4), nullable=True),
        sa.Column('kdj_k', DECIMAL(8, 4), nullable=True),
        sa.Column('kdj_d', DECIMAL(8, 4), nullable=True),
        sa.Column('kdj_j', DECIMAL(8, 4), nullable=True),
        sa.Column('ma5', DECIMAL(12, 3), nullable=True),
        sa.Column('ma10', DECIMAL(12, 3), nullable=True),
        sa.Column('ma20', DECIMAL(12, 3), nullable=True),
        sa.Column('data_source', sa.String(20), nullable=False),
        sa.Column('create_time', sa.DateTime, nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('update_time', sa.DateTime, nullable=False, server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP')),
    )
    op.create_unique_constraint('uk_stock_indicator', 't_stock_indicator', ['stock_code', 'trade_date', 'period'])
    op.create_index('idx_si_stock_date', 't_stock_indicator', ['stock_code', 'trade_date'])


def downgrade() -> None:
    # 删除 t_stock_indicator
    op.drop_index('idx_si_stock_date', 't_stock_indicator')
    op.drop_constraint('uk_stock_indicator', 't_stock_indicator', type_='unique')
    op.drop_table('t_stock_indicator')

    # 删除 t_watchlist_item
    op.drop_index('idx_wi_stock_code', 't_watchlist_item')
    op.drop_index('idx_wi_group_id', 't_watchlist_item')
    op.drop_constraint('uk_group_stock', 't_watchlist_item', type_='unique')
    op.drop_table('t_watchlist_item')

    # 删除 t_watchlist_group
    op.drop_index('idx_wg_user_id', 't_watchlist_group')
    op.drop_table('t_watchlist_group')

    # 回退 t_market_quote 扩展字段
    op.drop_column('t_market_quote', 'pb')
    op.drop_column('t_market_quote', 'pe_ttm')

    # 回退 t_stock 扩展字段
    op.drop_column('t_stock', 'float_market_cap')
    op.drop_column('t_stock', 'total_market_cap')
    op.drop_column('t_stock', 'industry_name')
    op.drop_column('t_stock', 'industry_code')
