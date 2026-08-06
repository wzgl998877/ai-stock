"""merge multi heads (a1b2c3d4e5f8 + h2i3j4k5l6m7)

Revision ID: i3j4k5l6m7n8
Revises: a1b2c3d4e5f8, h2i3j4k5l6m7
Create Date: 2026-08-05 00:00:00.000000

合并预存分叉：f6a7b8c9d0e1 之后存在两条平行分支
  - 分支 A：a1b2c3d4e5f7 → a1b2c3d4e5f8（chat_message 扩展 + 全文索引）
  - 分支 B：g7h8i9j0k1l2 → h2i3j4k5l6m7（事件雷达 + 缠论策略）
本迁移为纯拓扑合并节点，无 DDL，确保 ``alembic upgrade head`` 指向单一 head。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa  # noqa: F401


revision: str = 'i3j4k5l6m7n8'
down_revision: Union[str, Sequence[str], None] = ('a1b2c3d4e5f8', 'h2i3j4k5l6m7')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
