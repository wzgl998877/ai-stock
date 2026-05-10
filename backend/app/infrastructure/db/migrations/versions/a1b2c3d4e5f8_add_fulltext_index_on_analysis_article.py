"""add_fulltext_index_on_analysis_article

Revision ID: a1b2c3d4e5f8
Revises: a1b2c3d4e5f7
Create Date: 2026-05-10 01:00:00.000000
"""
from typing import Sequence, Union

from alembic import op

revision: str = 'a1b2c3d4e5f8'
down_revision: Union[str, None] = 'a1b2c3d4e5f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 创建 FULLTEXT 索引，用于 MATCH...AGAINST 全文搜索
    # MyISAM 原生支持，InnoDB 5.6+ 也支持
    op.execute(
        "ALTER TABLE t_analysis_article "
        "ADD FULLTEXT INDEX ft_article_search (title, summary, content)"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE t_analysis_article DROP INDEX ft_article_search")
