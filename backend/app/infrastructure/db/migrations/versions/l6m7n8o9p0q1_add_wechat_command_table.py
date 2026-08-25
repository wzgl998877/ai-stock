"""add t_wechat_command (微信指令助手)

Revision ID: l6m7n8o9p0q1
Revises: k5l6m7n8o9p0
Create Date: 2026-08-21 00:00:00.000000

微信指令助手（specs/010）：每条微信指令从接收、解析、执行到推送的
全生命周期记录。msg_id 取 iLink 入站消息 client_id，唯一索引兜底
去重（Redis 降级时的硬约束）；status 含 pending/running/completed/
failed/closed 五态（closed=未识别或未授权，仅留痕）。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.mysql import JSON


revision: str = 'l6m7n8o9p0q1'
down_revision: Union[str, None] = 'k5l6m7n8o9p0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        't_wechat_command',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('msg_id', sa.String(64), nullable=False),
        sa.Column('user_id', sa.String(64), nullable=False),
        sa.Column('raw_text', sa.String(512), nullable=False),
        sa.Column('tool_name', sa.String(64), nullable=True),
        sa.Column('params_json', JSON(), nullable=True),
        sa.Column('status', sa.String(16), nullable=False, server_default='pending'),
        sa.Column('progress', sa.String(64), nullable=True),
        sa.Column('result_summary', sa.Text(), nullable=True),
        sa.Column('push_status', sa.String(16), nullable=True),
        sa.Column('error_message', sa.String(1024), nullable=True),
        sa.Column('create_time', sa.DateTime(), nullable=False),
        sa.Column('update_time', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('msg_id', name='uk_wcmd_msg_id'),
    )
    op.create_index('idx_wcmd_user_time', 't_wechat_command', ['user_id', 'create_time'])
    op.create_index('idx_wcmd_status', 't_wechat_command', ['status'])


def downgrade() -> None:
    op.drop_index('idx_wcmd_status', table_name='t_wechat_command')
    op.drop_index('idx_wcmd_user_time', table_name='t_wechat_command')
    op.drop_table('t_wechat_command')
