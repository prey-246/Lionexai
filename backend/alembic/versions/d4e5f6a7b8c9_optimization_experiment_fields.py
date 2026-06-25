"""Add experiment_config and rank_score to validated_fund_runs."""

from alembic import op
import sqlalchemy as sa

revision = "d4e5f6a7b8c9_opt"
down_revision = "c3d4e5f6a7b8_vfund"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "validated_fund_runs",
        sa.Column("experiment_config", sa.JSON(), nullable=False, server_default="{}"),
    )
    op.add_column(
        "validated_fund_runs",
        sa.Column("rank_score", sa.Float(), nullable=True),
    )
    op.create_index("ix_validated_fund_runs_rank_score", "validated_fund_runs", ["rank_score"])


def downgrade() -> None:
    op.drop_index("ix_validated_fund_runs_rank_score", table_name="validated_fund_runs")
    op.drop_column("validated_fund_runs", "rank_score")
    op.drop_column("validated_fund_runs", "experiment_config")
