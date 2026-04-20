"""add_event_type_and_thinking_steps_to_chat_tables

Revision ID: f0ec562f649a
Revises:
Create Date: 2026-04-20 23:25:53.150663
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision: str = 'f0ec562f649a'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('t_chat_session', sa.Column('event_type', sa.String(length=20), nullable=True))
    op.add_column('t_chat_message', sa.Column('thinking_steps', mysql.JSON(), nullable=True))
    op.add_column('t_chat_message', sa.Column('event_type', sa.String(length=20), nullable=True))


def downgrade() -> None:
    op.drop_column('t_chat_message', 'event_type')
    op.drop_column('t_chat_message', 'thinking_steps')
    op.drop_column('t_chat_session', 'event_type')
