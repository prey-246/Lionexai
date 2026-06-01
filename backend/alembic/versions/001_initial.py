"""Initial database schema creation

Revision ID: 001_initial
Revises:
Create Date: 2024-06-01 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('id', sa.String(), nullable=False, index=True),
        sa.Column('email', sa.String(), nullable=False, index=True, unique=True),
        sa.Column('role_tier', sa.String(), nullable=False, server_default='retail'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'mandates',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('max_leverage', sa.Float(), nullable=False),
        sa.Column('max_drawdown_pct', sa.Float(), nullable=False),
        sa.Column('daily_loss_limit_pct', sa.Float(), nullable=False),
        sa.Column('allowed_assets', postgresql.JSON(), nullable=False),
        sa.Column('kill_switch_active', sa.Boolean(), nullable=False, server_default='false'),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'portfolios',
        sa.Column('id', sa.String(), nullable=False, index=True),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('mandate_id', sa.String(), nullable=False),
        sa.Column('total_equity', sa.Float(), nullable=False, server_default='100000.0'),
        sa.Column('available_margin', sa.Float(), nullable=False, server_default='100000.0'),
        sa.Column('current_drawdown_pct', sa.Float(), nullable=False, server_default='0.0'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['mandate_id'], ['mandates.id']),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'trades',
        sa.Column('id', sa.String(), nullable=False, index=True),
        sa.Column('portfolio_id', sa.String(), nullable=False, index=True),
        sa.Column('symbol', sa.String(), nullable=False, index=True),
        sa.Column('side', sa.String(), nullable=False),
        sa.Column('size', sa.Float(), nullable=False),
        sa.Column('entry_price', sa.Float(), nullable=False),
        sa.Column('exit_price', sa.Float()),
        sa.Column('status', sa.String(), nullable=False, server_default='OPEN'),
        sa.Column('pnl', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('closed_at', sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(['portfolio_id'], ['portfolios.id']),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'audit_logs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()'), index=True),
        sa.Column('action_type', sa.String(), nullable=False, index=True),
        sa.Column('description', sa.String()),
        sa.Column('metadata_json', postgresql.JSON()),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'equity_curves',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('portfolio_id', sa.String(), nullable=False, index=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()'), index=True),
        sa.Column('equity', sa.Float(), nullable=False),
        sa.Column('drawdown_pct', sa.Float(), nullable=False, server_default='0.0'),
        sa.ForeignKeyConstraint(['portfolio_id'], ['portfolios.id']),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'strategies',
        sa.Column('id', sa.String(), nullable=False, index=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String()),
        sa.Column('strategy_type', sa.String()),
        sa.Column('parameters', postgresql.JSON()),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'backtest_results',
        sa.Column('id', sa.String(), nullable=False, index=True),
        sa.Column('strategy_id', sa.String(), nullable=False, index=True),
        sa.Column('start_date', sa.DateTime(timezone=True)),
        sa.Column('end_date', sa.DateTime(timezone=True)),
        sa.Column('initial_capital', sa.Float()),
        sa.Column('final_equity', sa.Float()),
        sa.Column('total_return_pct', sa.Float()),
        sa.Column('cagr', sa.Float()),
        sa.Column('sharpe_ratio', sa.Float()),
        sa.Column('sortino_ratio', sa.Float()),
        sa.Column('max_drawdown_pct', sa.Float()),
        sa.Column('win_rate', sa.Float()),
        sa.Column('profit_factor', sa.Float()),
        sa.Column('total_trades', sa.Integer()),
        sa.Column('winning_trades', sa.Integer()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('results_json', postgresql.JSON()),
        sa.ForeignKeyConstraint(['strategy_id'], ['strategies.id']),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'risk_events',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('portfolio_id', sa.String(), nullable=False, index=True),
        sa.Column('event_type', sa.String()),
        sa.Column('severity', sa.String()),
        sa.Column('description', sa.String()),
        sa.Column('triggered_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('resolved', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('metadata_json', postgresql.JSON()),
        sa.ForeignKeyConstraint(['portfolio_id'], ['portfolios.id']),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'reports',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('portfolio_id', sa.String(), nullable=False, index=True),
        sa.Column('report_type', sa.String()),
        sa.Column('period_start', sa.DateTime(timezone=True)),
        sa.Column('period_end', sa.DateTime(timezone=True)),
        sa.Column('performance_metrics', postgresql.JSON()),
        sa.Column('risk_metrics', postgresql.JSON()),
        sa.Column('trades_summary', postgresql.JSON()),
        sa.Column('html_content', sa.String()),
        sa.Column('pdf_content', sa.String()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['portfolio_id'], ['portfolios.id']),
        sa.PrimaryKeyConstraint('id')
    )

def downgrade() -> None:
    op.drop_table('reports')
    op.drop_table('risk_events')
    op.drop_table('backtest_results')
    op.drop_table('strategies')
    op.drop_table('equity_curves')
    op.drop_table('audit_logs')
    op.drop_table('trades')
    op.drop_table('portfolios')
    op.drop_table('mandates')
    op.drop_table('users')
