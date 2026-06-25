"""Phase 6 institutional production readiness."""

from alembic import op
import sqlalchemy as sa

revision = "b2c3d4e5f6a7_p6_institutional"
down_revision = "a1b2c3d4e5f6_p5_validated"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("assets", sa.Column("region", sa.String(length=20), nullable=True))
    op.add_column("assets", sa.Column("risk_tier", sa.String(length=20), nullable=True))
    op.add_column("assets", sa.Column("liquidity_score", sa.Float(), nullable=True))
    op.add_column("assets", sa.Column("volatility_score", sa.Float(), nullable=True))
    op.create_index("ix_assets_region", "assets", ["region"])
    op.create_index("ix_assets_risk_tier", "assets", ["risk_tier"])

    op.create_table(
        "live_validation_snapshots",
        sa.Column("pk_id", sa.Integer(), primary_key=True),
        sa.Column("id", sa.String(length=40), nullable=False),
        sa.Column("period", sa.String(length=10), nullable=False),
        sa.Column("scope", sa.String(length=20), server_default="GLOBAL"),
        sa.Column("scope_id", sa.String(length=50), nullable=True),
        sa.Column("metrics", sa.JSON(), nullable=False),
        sa.Column("provenance", sa.String(length=40), server_default="PAPER_LIVE"),
        sa.Column("computed_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_live_val_snap_id", "live_validation_snapshots", ["id"], unique=True)
    op.create_index("ix_live_val_snap_period", "live_validation_snapshots", ["period"])
    op.create_index("ix_live_val_snap_provenance", "live_validation_snapshots", ["provenance"])

    op.create_table(
        "execution_lifecycle_events",
        sa.Column("pk_id", sa.Integer(), primary_key=True),
        sa.Column("id", sa.String(length=30), nullable=False),
        sa.Column("stage", sa.String(length=40), nullable=False),
        sa.Column("trade_id", sa.String(length=30), nullable=True),
        sa.Column("portfolio_id", sa.String(length=50), nullable=True),
        sa.Column("symbol", sa.String(length=30), nullable=True),
        sa.Column("reference_id", sa.String(length=50), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("timestamp", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_exec_lifecycle_id", "execution_lifecycle_events", ["id"], unique=True)
    op.create_index("ix_exec_lifecycle_stage", "execution_lifecycle_events", ["stage"])
    op.create_index("ix_exec_lifecycle_trade", "execution_lifecycle_events", ["trade_id"])

    op.create_table(
        "lnx_attribution_snapshots",
        sa.Column("pk_id", sa.Integer(), primary_key=True),
        sa.Column("id", sa.String(length=30), nullable=False),
        sa.Column("index_delta", sa.Float(), server_default="0"),
        sa.Column("direction", sa.String(length=10), server_default="FLAT"),
        sa.Column("attribution", sa.JSON(), nullable=False),
        sa.Column("components", sa.JSON(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("computed_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_lnx_attr_id", "lnx_attribution_snapshots", ["id"], unique=True)

    op.create_table(
        "treasury_verification_runs",
        sa.Column("pk_id", sa.Integer(), primary_key=True),
        sa.Column("id", sa.String(length=30), nullable=False),
        sa.Column("solvency_score", sa.Float(), server_default="0"),
        sa.Column("status", sa.String(length=20), server_default="WATCH"),
        sa.Column("issues", sa.JSON(), nullable=True),
        sa.Column("pool_balances", sa.JSON(), nullable=True),
        sa.Column("routing_integrity_pct", sa.Float(), server_default="0"),
        sa.Column("settlement_coverage_pct", sa.Float(), server_default="0"),
        sa.Column("stress_results", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_treasury_ver_id", "treasury_verification_runs", ["id"], unique=True)

    op.create_table(
        "institutional_reports",
        sa.Column("pk_id", sa.Integer(), primary_key=True),
        sa.Column("id", sa.String(length=30), nullable=False),
        sa.Column("report_type", sa.String(length=30), nullable=False),
        sa.Column("fund_id", sa.String(length=30), nullable=True),
        sa.Column("period_start", sa.DateTime(), nullable=False),
        sa.Column("period_end", sa.DateTime(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_inst_report_id", "institutional_reports", ["id"], unique=True)
    op.create_index("ix_inst_report_fund", "institutional_reports", ["fund_id"])

    op.create_table(
        "macro_data_snapshots",
        sa.Column("pk_id", sa.Integer(), primary_key=True),
        sa.Column("id", sa.String(length=30), nullable=False),
        sa.Column("source", sa.String(length=30), server_default="FRED"),
        sa.Column("series_data", sa.JSON(), nullable=False),
        sa.Column("risk_drivers", sa.JSON(), nullable=True),
        sa.Column("computed_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_macro_snap_id", "macro_data_snapshots", ["id"], unique=True)


def downgrade():
    op.drop_table("macro_data_snapshots")
    op.drop_table("institutional_reports")
    op.drop_table("treasury_verification_runs")
    op.drop_table("lnx_attribution_snapshots")
    op.drop_table("execution_lifecycle_events")
    op.drop_table("live_validation_snapshots")
    op.drop_index("ix_assets_risk_tier", "assets")
    op.drop_index("ix_assets_region", "assets")
    op.drop_column("assets", "volatility_score")
    op.drop_column("assets", "liquidity_score")
    op.drop_column("assets", "risk_tier")
    op.drop_column("assets", "region")
