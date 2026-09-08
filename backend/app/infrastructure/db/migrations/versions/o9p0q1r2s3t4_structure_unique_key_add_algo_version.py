"""缠论结构快照唯一键加 algo_version（v1/v2 双版本并存）

Revision ID: o9p0q1r2s3t4
Revises: n8o9p0q1r2s3
Create Date: 2026-09-08 00:00:00.000000

背景（2026-09-08 双口径并存）：缠论引擎 v1(1.0.0)/v2(1.1.0) 双版本并行
运行（定时扫描双跑、手动/微信/回测可指定版本）。结构快照表
``t_strategy_structure`` 原唯一键 ``(stock_code, period)`` 不含版本——
两版本交替写库互相覆盖，且监控层 ``_is_stale`` 水位线比较会在版本切换后
误判（前一版本刚写的快照挡住后一版本的重算，或每次都强制全量双算）。

改法：唯一键改为 ``(stock_code, period, algo_version)``。``algo_version``
列已存在（String(16)），存量行保留其真实版本标签（生产存量全部为 1.0.0），
无需数据迁移；两版本各自维护独立快照行与水位线。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'o9p0q1r2s3t4'
down_revision: Union[str, None] = 'n8o9p0q1r2s3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_OLD_CONSTRAINT = 'uq_strategy_structure_code_period'
_NEW_CONSTRAINT = 'uq_strategy_structure_code_period_version'
_TABLE = 't_strategy_structure'


def upgrade() -> None:
    op.drop_constraint(_OLD_CONSTRAINT, _TABLE, type_='unique')
    op.create_unique_constraint(
        _NEW_CONSTRAINT, _TABLE,
        ['stock_code', 'period', 'algo_version'],
    )


def downgrade() -> None:
    # 回滚有数据风险：两版本快照并存时同 (code, period) 有两行，需先手动
    # 清理非当前版本行，否则唯一约束建不回去
    op.drop_constraint(_NEW_CONSTRAINT, _TABLE, type_='unique')
    op.create_unique_constraint(_OLD_CONSTRAINT, _TABLE, ['stock_code', 'period'])
