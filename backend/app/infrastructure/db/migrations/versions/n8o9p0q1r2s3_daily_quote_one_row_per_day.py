"""daily quote 一天一条：去重存量 + 唯一索引去掉 data_source

Revision ID: n8o9p0q1r2s3
Revises: m7n8o9p0q1r2
Create Date: 2026-08-25 00:00:00.000000

背景（2026-08-25 缠论数据断档排查）：原唯一索引
``(code, trade_date, data_source, period)`` 允许同股同日多源并存，
``get_daily`` 按"数据源优先级"挑一份返回——tushare(1) > akshare(2) >
baostock(3)，sina 不在表内。日常同步实际只有 sina 在跑（缠论调度器/
自选股批量同步），tushare/baostock 存量是历史手动同步留下的死数据，
导致 10 只股票缠论一直用陈年数据计算（000707 停在 2024-12-31）。

业务语义改为「一个股票一个交易日只有一条数据」：
1. 存量去重：每个 (code, trade_date, period) 保留 update_time 最新一行
   （绝大多数是 sina，即最新数据），删除其余源的旧行；
2. 唯一索引改为 (code, trade_date, period)，data_source 退化为纯审计
   字段（记录该行数据来源），不再参与唯一性；
3. 此后 upsert_daily_batch 删除条件不含 data_source——同步即全源覆盖。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'n8o9p0q1r2s3'
down_revision: Union[str, None] = 'm7n8o9p0q1r2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1) 存量去重：保留每 (code, trade_date, period) 下 update_time 最新的行
    #    （子查询取每组的最大 id——id 与 update_time 单调一致，且 id 是主键
    #    避免 update_time 相同的并列歧义）
    op.execute(
        """
        DELETE d FROM t_stock_daily_quote d
        JOIN t_stock_daily_quote newer
          ON newer.code = d.code
         AND newer.trade_date = d.trade_date
         AND newer.period = d.period
         AND (newer.update_time > d.update_time
              OR (newer.update_time = d.update_time AND newer.id > d.id))
        """
    )
    # 2) 唯一索引去掉 data_source
    op.drop_index('uk_code_date_source_period', table_name='t_stock_daily_quote')
    op.create_unique_constraint(
        'uk_code_date_period', 't_stock_daily_quote',
        ['code', 'trade_date', 'period'],
    )


def downgrade() -> None:
    op.drop_constraint('uk_code_date_period', table_name='t_stock_daily_quote', type_='unique')
    # 回滚无法恢复被删除的多源行；仅恢复索引结构
    op.create_unique_constraint(
        'uk_code_date_source_period', 't_stock_daily_quote',
        ['code', 'trade_date', 'data_source', 'period'],
    )
