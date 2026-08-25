"""widen t_wechat_command.msg_id to 128

Revision ID: m7n8o9p0q1r2
Revises: l6m7n8o9p0q1
Create Date: 2026-08-21 00:00:00.000000

真机实测 iLink 入站消息 client_id 为 92 字符长格式
（mmassistant_bypmsg_inbox_<uin>@weclaw_<ts>_<n>_xwechat_<n>），
原 VARCHAR(64) 撞 1406 Data too long。扩至 128。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'm7n8o9p0q1r2'
down_revision: Union[str, None] = 'l6m7n8o9p0q1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        't_wechat_command', 'msg_id',
        existing_type=sa.String(64), type_=sa.String(128),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        't_wechat_command', 'msg_id',
        existing_type=sa.String(128), type_=sa.String(64),
        existing_nullable=False,
    )
