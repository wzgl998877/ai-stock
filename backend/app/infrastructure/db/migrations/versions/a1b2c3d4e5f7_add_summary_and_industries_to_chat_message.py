"""add_summary_and_industries_to_chat_message

Revision ID: a1b2c3d4e5f7
Revises: f0ec562f649a
Create Date: 2026-05-10 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision: str = 'a1b2c3d4e5f7'
down_revision: Union[str, None] = 'f6a7b8c9d0e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('t_chat_message', sa.Column('summary', sa.String(length=500), nullable=True))
    op.add_column('t_chat_message', sa.Column('industries', mysql.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('t_chat_message', 'industries')
    op.drop_column('t_chat_message', 'summary')
