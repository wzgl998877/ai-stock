"""add chanlun strategy monitor and backtest tables (module 3)

Revision ID: h2i3j4k5l6m7
Revises: g7h8i9j0k1l2
Create Date: 2026-08-05 00:00:00.000000

七张表（对照 specs/009-chanlun-signal-system/data-model.md）：
  t_strategy_signal / t_strategy_structure / t_strategy_monitor_config /
  t_strategy_run_log / t_backtest_report / t_backtest_signal_detail / t_backtest_summary
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.mysql import JSON, DECIMAL


revision: str = 'h2i3j4k5l6m7'
down_revision: Union[str, None] = 'g7h8i9j0k1l2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. t_strategy_signal（缠论信号历史，核心）
    op.create_table(
        't_strategy_signal',
        sa.Column('id', sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.String(32), nullable=True),
        sa.Column('stock_code', sa.String(10), nullable=False),
        sa.Column('period', sa.String(8), nullable=False),
        sa.Column('signal_type', sa.String(8), nullable=False),
        sa.Column('structure_level', sa.String(8), nullable=False),
        sa.Column('signal_time', sa.DateTime, nullable=False),
        sa.Column('confirmed_at', sa.DateTime, nullable=True),
        sa.Column('trigger_price', DECIMAL(precision=12, scale=3), nullable=True),
        sa.Column('status', sa.String(12), nullable=False, server_default='confirmed'),
        sa.Column('invalidated_reason', sa.String(64), nullable=True),
        sa.Column('algo_version', sa.String(16), nullable=False, server_default=''),
        sa.Column('dedup_key', sa.String(128), nullable=False),
        sa.Column('create_time', sa.DateTime, nullable=False, server_default=sa.text('NOW()')),
        sa.Column('update_time', sa.DateTime, nullable=False, server_default=sa.text('NOW()'), onupdate=sa.text('NOW()')),
        sa.UniqueConstraint('dedup_key', name='uq_strategy_signal_dedup'),
        sa.Index('idx_ss_code_period_time', 'stock_code', 'period', 'signal_time'),
        sa.Index('idx_ss_user_status', 'user_id', 'status'),
    )

    # 2. t_strategy_structure（缠论结构快照，覆盖式更新）
    op.create_table(
        't_strategy_structure',
        sa.Column('id', sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column('stock_code', sa.String(10), nullable=False),
        sa.Column('period', sa.String(8), nullable=False),
        sa.Column('strokes_json', JSON, nullable=True),
        sa.Column('segments_json', JSON, nullable=True),
        sa.Column('zhongshu_json', JSON, nullable=True),
        sa.Column('last_kline_time', sa.DateTime, nullable=True),
        sa.Column('algo_version', sa.String(16), nullable=False, server_default=''),
        sa.Column('update_time', sa.DateTime, nullable=False, server_default=sa.text('NOW()'), onupdate=sa.text('NOW()')),
        sa.UniqueConstraint('stock_code', 'period', name='uq_strategy_structure_code_period'),
    )

    # 3. t_strategy_monitor_config（逐股监控配置）
    op.create_table(
        't_strategy_monitor_config',
        sa.Column('id', sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.String(32), nullable=False),
        sa.Column('stock_code', sa.String(10), nullable=False),
        sa.Column('daily_enabled', sa.SmallInteger, nullable=False, server_default='1'),
        sa.Column('m30_enabled', sa.SmallInteger, nullable=False, server_default='1'),
        sa.Column('create_time', sa.DateTime, nullable=False, server_default=sa.text('NOW()')),
        sa.Column('update_time', sa.DateTime, nullable=False, server_default=sa.text('NOW()'), onupdate=sa.text('NOW()')),
        sa.UniqueConstraint('user_id', 'stock_code', name='uq_monitor_user_stock'),
    )

    # 4. t_strategy_run_log（计算任务日志）
    op.create_table(
        't_strategy_run_log',
        sa.Column('id', sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.String(32), nullable=True),
        sa.Column('period', sa.String(8), nullable=False),
        sa.Column('trigger_type', sa.String(12), nullable=False),
        sa.Column('status', sa.String(12), nullable=False, server_default='running'),
        sa.Column('total', sa.Integer, nullable=True),
        sa.Column('success', sa.Integer, nullable=True),
        sa.Column('failed', sa.Integer, nullable=True),
        sa.Column('failed_detail', JSON, nullable=True),
        sa.Column('started_at', sa.DateTime, nullable=False, server_default=sa.text('NOW()')),
        sa.Column('finished_at', sa.DateTime, nullable=True),
        sa.Column('duration_ms', sa.Integer, nullable=True),
        sa.Column('algo_version', sa.String(16), nullable=False, server_default=''),
        sa.Index('idx_srl_period_started', 'period', 'started_at'),
    )

    # 5. t_backtest_report（回测报告，明细/汇总的父表）
    op.create_table(
        't_backtest_report',
        sa.Column('id', sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.String(32), nullable=False),
        sa.Column('range_label', sa.String(4), nullable=False),
        sa.Column('start_date', sa.Date, nullable=False),
        sa.Column('end_date', sa.Date, nullable=False),
        sa.Column('stock_count', sa.Integer, nullable=True),
        sa.Column('signal_total', sa.Integer, nullable=True),
        sa.Column('excluded_invalidated', sa.Integer, nullable=True),
        sa.Column('benchmark_return', DECIMAL(precision=8, scale=6), nullable=True),
        sa.Column('algo_version', sa.String(16), nullable=False, server_default=''),
        sa.Column('status', sa.String(12), nullable=False, server_default='running'),
        sa.Column('create_time', sa.DateTime, nullable=False, server_default=sa.text('NOW()')),
        sa.Index('idx_br_user_created', 'user_id', 'create_time'),
    )

    # 6. t_backtest_signal_detail（回测信号明细）
    op.create_table(
        't_backtest_signal_detail',
        sa.Column('id', sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column('report_id', sa.BigInteger, sa.ForeignKey('t_backtest_report.id', ondelete='CASCADE'), nullable=False),
        sa.Column('stock_code', sa.String(10), nullable=False),
        sa.Column('period', sa.String(8), nullable=False),
        sa.Column('signal_type', sa.String(8), nullable=False),
        sa.Column('structure_level', sa.String(8), nullable=False),
        sa.Column('signal_time', sa.DateTime, nullable=False),
        sa.Column('trigger_price', DECIMAL(precision=12, scale=3), nullable=True),
        sa.Column('ret_5', DECIMAL(precision=8, scale=6), nullable=True),
        sa.Column('ret_10', DECIMAL(precision=8, scale=6), nullable=True),
        sa.Column('ret_20', DECIMAL(precision=8, scale=6), nullable=True),
        sa.Column('ret_60', DECIMAL(precision=8, scale=6), nullable=True),
        sa.Column('window_complete', sa.SmallInteger, nullable=False, server_default='1'),
        sa.UniqueConstraint(
            'report_id', 'stock_code', 'period', 'signal_type', 'signal_time',
            name='uq_bsd_report_signal',
        ),
        sa.Index('idx_bsd_report_type', 'report_id', 'period', 'signal_type'),
    )

    # 7. t_backtest_summary（回测聚合统计）
    op.create_table(
        't_backtest_summary',
        sa.Column('id', sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column('report_id', sa.BigInteger, sa.ForeignKey('t_backtest_report.id', ondelete='CASCADE'), nullable=False),
        sa.Column('period', sa.String(8), nullable=False),
        sa.Column('signal_type', sa.String(8), nullable=False),
        sa.Column('window', sa.SmallInteger, nullable=False),
        sa.Column('sample_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('win_rate', DECIMAL(precision=8, scale=6), nullable=True),
        sa.Column('avg_return', DECIMAL(precision=8, scale=6), nullable=True),
        sa.Column('median_return', DECIMAL(precision=8, scale=6), nullable=True),
        sa.Column('profit_loss_ratio', DECIMAL(precision=8, scale=6), nullable=True),
        sa.Column('note', sa.String(32), nullable=True),
        sa.UniqueConstraint(
            'report_id', 'period', 'signal_type', 'window',
            name='uq_bs_report_window',
        ),
    )


def downgrade() -> None:
    op.drop_table('t_backtest_summary')
    op.drop_table('t_backtest_signal_detail')
    op.drop_table('t_backtest_report')
    op.drop_table('t_strategy_run_log')
    op.drop_table('t_strategy_monitor_config')
    op.drop_table('t_strategy_structure')
    op.drop_table('t_strategy_signal')
