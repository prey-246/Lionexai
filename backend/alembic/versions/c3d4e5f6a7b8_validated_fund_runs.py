"""Validated fund-level historical backtest runs."""

from alembic import op
import sqlalchemy as sa

revision = "c3d4e5f6a7b8_vfund"
down_revision = "b2c3d4e5f6a7_p6_institutional"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "validated_fund_runs",
        sa.Column("pk_id", sa.Integer(), primary_key=True),
        sa.Column("id", sa.String(length=30), nullable=False),
        sa.Column("fund_id", sa.String(length=20), nullable=False),
        sa.Column("validation_type", sa.String(length=30), nullable=False, server_default="BACKTEST"),
        sa.Column("period_start", sa.DateTime(), nullable=True),
        sa.Column("period_end", sa.DateTime(), nullable=True),
        sa.Column("initial_capital", sa.Float(), nullable=False, server_default="1000000"),
        sa.Column("metrics", sa.JSON(), nullable=False),
        sa.Column("equity_curve", sa.JSON(), nullable=False),
        sa.Column("rebalance_log", sa.JSON(), nullable=False),
        sa.Column("allocation_policy_snapshot", sa.JSON(), nullable=False),
        sa.Column("data_coverage", sa.JSON(), nullable=False),
        sa.Column("data_source", sa.String(length=40), nullable=False, server_default="HISTORICAL_MARKET_BARS"),
        sa.Column("provenance", sa.String(length=40), nullable=False, server_default="VALIDATED_HISTORICAL"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_validated_fund_runs_id", "validated_fund_runs", ["id"], unique=True)
    op.create_index("ix_validated_fund_runs_fund_id", "validated_fund_runs", ["fund_id"])


def downgrade():
    op.drop_index("ix_validated_fund_runs_fund_id", table_name="validated_fund_runs")
    op.drop_index("ix_validated_fund_runs_id", table_name="validated_fund_runs")
    op.drop_table("validated_fund_runs")
