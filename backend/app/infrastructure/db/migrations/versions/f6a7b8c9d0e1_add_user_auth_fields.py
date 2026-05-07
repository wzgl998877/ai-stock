"""add user auth fields

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-05-07 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f6a7b8c9d0e1'
down_revision: Union[str, None] = 'e5f6a7b8c9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 扩展 password 字段长度以支持 salt:hash 格式
    op.alter_column('t_user', 'password',
                    existing_type=sa.String(128),
                    new_type=sa.String(256),
                    existing_nullable=False)

    # 添加 email 字段
    op.add_column('t_user', sa.Column('email', sa.String(100), nullable=True))

    # 添加 user_account 唯一索引
    op.create_index('uq_user_account', 't_user', ['user_account'], unique=True)

    # 添加 email 唯一索引
    op.create_index('uq_user_email', 't_user', ['email'], unique=True)


def downgrade() -> None:
    op.drop_index('uq_user_email', table_name='t_user')
    op.drop_index('uq_user_account', table_name='t_user')
    op.drop_column('t_user', 'email')
    op.alter_column('t_user', 'password',
                    existing_type=sa.String(256),
                    new_type=sa.String(128),
                    existing_nullable=False)
