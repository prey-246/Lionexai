"""Phase 5 validated performance tables."""

from alembic import op
import sqlalchemy as sa

revision = "a1b2c3d4e5f6_p5_validated"
down_revision = "f9c2a4e01b06"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "validated_strategy_runs",
        sa.Column("pk_id", sa.Integer(), primary_key=True),
        sa.Column("id", sa.String(length=30), nullable=False),
        sa.Column("strategy_key", sa.String(length=40), nullable=False),
        sa.Column("symbol", sa.String(length=30), nullable=False),
        sa.Column("validation_type", sa.String(length=30), nullable=False),
        sa.Column("period_start", sa.DateTime(), nullable=True),
        sa.Column("period_end", sa.DateTime(), nullable=True),
        sa.Column("metrics", sa.JSON(), nullable=False),
        sa.Column("regime_breakdown", sa.JSON(), nullable=False),
        sa.Column("equity_curve", sa.JSON(), nullable=False),
        sa.Column("data_source", sa.String(length=40), nullable=False, server_default="HISTORICAL_MARKET_BARS"),
        sa.Column("provenance", sa.String(length=40), nullable=False, server_default="VALIDATED_HISTORICAL"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_validated_strategy_runs_id", "validated_strategy_runs", ["id"], unique=True)
    op.create_index("ix_validated_strategy_runs_strategy", "validated_strategy_runs", ["strategy_key"])
    op.create_index("ix_validated_strategy_runs_provenance", "validated_strategy_runs", ["provenance"])

    op.create_table(
        "paper_trading_validation_snapshots",
        sa.Column("pk_id", sa.Integer(), primary_key=True),
        sa.Column("id", sa.String(length=30), nullable=False),
        sa.Column("period", sa.String(length=10), nullable=False),
        sa.Column("scope", sa.String(length=20), nullable=False, server_default="GLOBAL"),
        sa.Column("scope_id", sa.String(length=50), nullable=True),
        sa.Column("metrics", sa.JSON(), nullable=False),
        sa.Column("provenance", sa.String(length=40), nullable=False, server_default="PAPER_LIVE"),
        sa.Column("computed_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_paper_val_snap_period", "paper_trading_validation_snapshots", ["period"])
    op.create_index("ix_paper_val_snap_id", "paper_trading_validation_snapshots", ["id"], unique=True)

    op.create_table(
        "allocation_integrity_alerts",
        sa.Column("pk_id", sa.Integer(), primary_key=True),
        sa.Column("id", sa.String(length=30), nullable=False),
        sa.Column("portfolio_id", sa.Integer(), sa.ForeignKey("portfolios.pk_id", name="fk_alloc_alert_portfolio"), nullable=False),
        sa.Column("alert_type", sa.String(length=40), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False, server_default="MEDIUM"),
        sa.Column("message", sa.String(length=500), nullable=False),
        sa.Column("symbol", sa.String(length=30), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("resolved", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_alloc_integrity_alert_portfolio", "allocation_integrity_alerts", ["portfolio_id"])
    op.create_index("ix_alloc_integrity_alert_id", "allocation_integrity_alerts", ["id"], unique=True)


def downgrade():
    op.drop_table("allocation_integrity_alerts")
    op.drop_table("paper_trading_validation_snapshots")
    op.drop_table("validated_strategy_runs")
