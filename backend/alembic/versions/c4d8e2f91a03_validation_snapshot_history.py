"""Add validation snapshot history archive table and scope_id column."""

from alembic import op
import sqlalchemy as sa


revision = "c4d8e2f91a03"
down_revision = "b7c3e1a42f90"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("validation_snapshots", sa.Column("scope_id", sa.String(), nullable=True))
    op.create_index("ix_validation_snapshots_scope_id", "validation_snapshots", ["scope_id"], unique=False)

    op.create_table(
        "validation_snapshot_history",
        sa.Column("pk_id", sa.Integer(), nullable=False),
        sa.Column("archive_date", sa.Date(), nullable=False),
        sa.Column("snapshot_key", sa.String(), nullable=False),
        sa.Column("snapshot_type", sa.String(), nullable=False),
        sa.Column("period", sa.String(), nullable=False),
        sa.Column("scope_id", sa.String(), nullable=True),
        sa.Column("total_trades", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("winning_trades", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("losing_trades", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("win_rate_pct", sa.Float(), nullable=False, server_default="0"),
        sa.Column("total_pnl", sa.Float(), nullable=False, server_default="0"),
        sa.Column("profit_factor", sa.Float(), nullable=True),
        sa.Column("sharpe_ratio", sa.Float(), nullable=True),
        sa.Column("max_drawdown_pct", sa.Float(), nullable=False, server_default="0"),
        sa.Column("avg_return_pct", sa.Float(), nullable=False, server_default="0"),
        sa.Column("largest_win", sa.Float(), nullable=False, server_default="0"),
        sa.Column("largest_loss", sa.Float(), nullable=False, server_default="0"),
        sa.Column("avg_latency_ms", sa.Float(), nullable=False, server_default="0"),
        sa.Column("fill_rate_pct", sa.Float(), nullable=False, server_default="0"),
        sa.Column("chart_data", sa.JSON(), nullable=True),
        sa.Column("archived_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("pk_id"),
        sa.UniqueConstraint("archive_date", "snapshot_key", name="uq_validation_history_date_key"),
    )
    op.create_index("ix_validation_snapshot_history_archive_date", "validation_snapshot_history", ["archive_date"])
    op.create_index("ix_validation_snapshot_history_snapshot_key", "validation_snapshot_history", ["snapshot_key"])
    op.create_index("ix_validation_snapshot_history_snapshot_type", "validation_snapshot_history", ["snapshot_type"])
    op.create_index("ix_validation_snapshot_history_period", "validation_snapshot_history", ["period"])
    op.create_index("ix_validation_snapshot_history_scope_id", "validation_snapshot_history", ["scope_id"])


def downgrade() -> None:
    op.drop_index("ix_validation_snapshot_history_scope_id", table_name="validation_snapshot_history")
    op.drop_index("ix_validation_snapshot_history_period", table_name="validation_snapshot_history")
    op.drop_index("ix_validation_snapshot_history_snapshot_type", table_name="validation_snapshot_history")
    op.drop_index("ix_validation_snapshot_history_snapshot_key", table_name="validation_snapshot_history")
    op.drop_index("ix_validation_snapshot_history_archive_date", table_name="validation_snapshot_history")
    op.drop_table("validation_snapshot_history")
    op.drop_index("ix_validation_snapshots_scope_id", table_name="validation_snapshots")
    op.drop_column("validation_snapshots", "scope_id")
