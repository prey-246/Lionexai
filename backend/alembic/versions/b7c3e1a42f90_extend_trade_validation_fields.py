"""Extend trades for paper validation capture

Revision ID: b7c3e1a42f90
Revises: 46e562f55a1a
Create Date: 2026-06-19 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'b7c3e1a42f90'
down_revision = '46e562f55a1a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('trades', sa.Column('exchange', sa.String(), nullable=True))
    op.add_column('trades', sa.Column('execution_latency_ms', sa.Float(), nullable=True))
    op.add_column('trades', sa.Column('strategy_name', sa.String(), nullable=True))
    op.add_column('trades', sa.Column('rejection_reason', sa.Text(), nullable=True))
    op.add_column(
        'trades',
        sa.Column('trade_source', sa.String(), nullable=False, server_default='MANUAL'),
    )
    op.create_index('ix_trades_trade_source', 'trades', ['trade_source'], unique=False)
    op.create_index('ix_trades_exchange', 'trades', ['exchange'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_trades_exchange', table_name='trades')
    op.drop_index('ix_trades_trade_source', table_name='trades')
    op.drop_column('trades', 'trade_source')
    op.drop_column('trades', 'rejection_reason')
    op.drop_column('trades', 'strategy_name')
    op.drop_column('trades', 'execution_latency_ms')
    op.drop_column('trades', 'exchange')
