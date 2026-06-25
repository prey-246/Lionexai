"""Treasury economics: client settlements + fund weekly targets

Revision ID: e6a8c3d12f05
Revises: d5f3a1b9c204
Create Date: 2026-06-24 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "e6a8c3d12f05"
down_revision = "d5f3a1b9c204"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("funds", sa.Column("target_weekly_return_pct", sa.Float(), nullable=True))
    op.add_column("funds", sa.Column("target_monthly_return_pct", sa.Float(), nullable=True))

    op.add_column("portfolios", sa.Column("principal", sa.Float(), nullable=True))
    op.add_column("portfolios", sa.Column("last_settled_at", sa.DateTime(), nullable=True))

    op.create_table(
        "client_settlements",
        sa.Column("pk_id", sa.Integer(), primary_key=True),
        sa.Column("id", sa.String(length=30), nullable=False),
        sa.Column("portfolio_id", sa.Integer(), nullable=False),
        sa.Column("period_start", sa.DateTime(), nullable=False),
        sa.Column("period_end", sa.DateTime(), nullable=False),
        sa.Column("iso_week_key", sa.String(length=10), nullable=False),
        sa.Column("opening_equity", sa.Float(), nullable=False, server_default="0"),
        sa.Column("closing_marked_equity", sa.Float(), nullable=False, server_default="0"),
        sa.Column("period_pnl", sa.Float(), nullable=False, server_default="0"),
        sa.Column("target_return_pct", sa.Float(), nullable=False, server_default="0"),
        sa.Column("client_entitlement", sa.Float(), nullable=False, server_default="0"),
        sa.Column("excess_routed", sa.Float(), nullable=False, server_default="0"),
        sa.Column("shortfall_topup", sa.Float(), nullable=False, server_default="0"),
        sa.Column("uncovered", sa.Float(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(), nullable=False, server_default="SETTLED"),
        sa.Column("breakdown", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_client_settlements_id", "client_settlements", ["id"], unique=True)
    op.create_index("ix_client_settlements_portfolio", "client_settlements", ["portfolio_id"])
    op.create_index("ix_client_settlements_week", "client_settlements", ["iso_week_key"])
    op.create_index("ix_client_settlements_portfolio_week", "client_settlements", ["portfolio_id", "iso_week_key"], unique=True)
    op.create_foreign_key(
        "fk_settlement_portfolio", "client_settlements", "portfolios",
        ["portfolio_id"], ["pk_id"], use_alter=True,
    )

    op.add_column("treasury_transactions", sa.Column("settlement_pk_id", sa.Integer(), nullable=True))
    op.create_index("ix_treasury_tx_settlement", "treasury_transactions", ["settlement_pk_id"])
    op.create_foreign_key(
        "fk_treasury_tx_settlement", "treasury_transactions", "client_settlements",
        ["settlement_pk_id"], ["pk_id"], use_alter=True,
    )


def downgrade() -> None:
    op.drop_constraint("fk_treasury_tx_settlement", "treasury_transactions", type_="foreignkey")
    op.drop_index("ix_treasury_tx_settlement", "treasury_transactions")
    op.drop_column("treasury_transactions", "settlement_pk_id")

    op.drop_table("client_settlements")

    op.drop_column("portfolios", "last_settled_at")
    op.drop_column("portfolios", "principal")

    op.drop_column("funds", "target_monthly_return_pct")
    op.drop_column("funds", "target_weekly_return_pct")
