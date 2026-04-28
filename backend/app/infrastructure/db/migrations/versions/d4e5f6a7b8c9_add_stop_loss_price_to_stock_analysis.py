"""add stop_loss_price column to t_stock_analysis

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-04-28 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.mysql import DECIMAL


# revision identifiers, used by Alembic.
revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        't_stock_analysis',
        sa.Column('stop_loss_price', DECIMAL(12, 3), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('t_stock_analysis', 'stop_loss_price')
