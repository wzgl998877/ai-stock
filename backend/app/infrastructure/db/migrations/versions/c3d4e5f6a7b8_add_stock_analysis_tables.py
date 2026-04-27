"""add t_stock_analysis and t_stock_analysis_detail tables

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-04-27 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.mysql import DECIMAL, JSON


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- t_stock_analysis ---
    op.create_table(
        't_stock_analysis',
        sa.Column('analysis_id', sa.String(32), primary_key=True),
        sa.Column('stock_code', sa.String(10), nullable=False),
        sa.Column('stock_name', sa.String(50), nullable=False),
        sa.Column('analysis_mode', sa.String(10), nullable=False, server_default='full'),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('current_phase', sa.String(20), nullable=False, server_default='analysts'),
        sa.Column('title', sa.String(100), nullable=False, server_default=''),
        sa.Column('summary', sa.String(500), nullable=False, server_default=''),
        sa.Column('full_content', sa.Text, nullable=True),
        sa.Column('decision_action', sa.String(20), nullable=True),
        sa.Column('target_price', DECIMAL(12, 3), nullable=True),
        sa.Column('confidence', DECIMAL(5, 4), nullable=True),
        sa.Column('risk_score', DECIMAL(5, 4), nullable=True),
        sa.Column('reasoning', sa.Text, nullable=True),
        sa.Column('industries', JSON, nullable=True),
        sa.Column('data_source', sa.String(20), nullable=False, server_default=''),
        sa.Column('article_id', sa.String(32), nullable=True),
        sa.Column('session_id', sa.String(32), nullable=True),
        sa.Column('user_id', sa.String(32), nullable=False),
        # AuditMixin fields
        sa.Column('create_time', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('update_time', sa.DateTime, nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('create_user', sa.String(64), nullable=True),
        sa.Column('update_user', sa.String(64), nullable=True),
        sa.Column('deleted', sa.CHAR(1), nullable=False, server_default='0'),
    )
    op.create_index('idx_sa_stock_code', 't_stock_analysis', ['stock_code'])
    op.create_index('idx_sa_status', 't_stock_analysis', ['status'])
    op.create_index('idx_sa_user_id', 't_stock_analysis', ['user_id'])
    op.create_index('idx_sa_create_time', 't_stock_analysis', ['create_time'])
    op.create_index('idx_sa_article_id', 't_stock_analysis', ['article_id'])

    # --- t_stock_analysis_detail ---
    op.create_table(
        't_stock_analysis_detail',
        sa.Column('detail_id', sa.String(32), primary_key=True),
        sa.Column('analysis_id', sa.String(32),
                  sa.ForeignKey('t_stock_analysis.analysis_id', ondelete='CASCADE'),
                  nullable=False),
        sa.Column('agent_name', sa.String(50), nullable=False),
        sa.Column('phase', sa.String(20), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('summary', sa.String(500), nullable=True),
        sa.Column('full_report', sa.Text, nullable=True),
        sa.Column('thinking_steps', JSON, nullable=True),
        sa.Column('debate_data', JSON, nullable=True),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('completed_at', sa.DateTime, nullable=True),
        sa.Column('display_order', sa.Integer, nullable=False, server_default='0'),
        # AuditMixin fields
        sa.Column('create_time', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('update_time', sa.DateTime, nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('create_user', sa.String(64), nullable=True),
        sa.Column('update_user', sa.String(64), nullable=True),
        sa.Column('deleted', sa.CHAR(1), nullable=False, server_default='0'),
    )
    op.create_index('idx_sad_analysis_id', 't_stock_analysis_detail', ['analysis_id'])
    op.create_index('idx_sad_agent_name', 't_stock_analysis_detail', ['agent_name'])
    op.create_index('idx_sad_phase', 't_stock_analysis_detail', ['phase'])
    op.create_index('idx_sad_status', 't_stock_analysis_detail', ['status'])


def downgrade() -> None:
    op.drop_table('t_stock_analysis_detail')
    op.drop_table('t_stock_analysis')
