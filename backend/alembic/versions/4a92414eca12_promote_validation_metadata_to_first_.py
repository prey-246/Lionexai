"""Promote validation metadata to first-class columns

Revision ID: 4a92414eca12
Revises: c4d8e2f91a03
Create Date: 2026-06-19 05:55:58.025588

"""
from alembic import op
import sqlalchemy as sa


revision = "4a92414eca12"
down_revision = "c4d8e2f91a03"
branch_labels = None
depends_on = None

_META_COLUMNS = (
    ("total_orders", sa.Integer()),
    ("filled_orders", sa.Integer()),
    ("rejected_orders", sa.Integer()),
    ("best_portfolio", sa.String()),
    ("worst_portfolio", sa.String()),
    ("best_strategy", sa.String()),
    ("worst_strategy", sa.String()),
    ("exchange_distribution", sa.JSON()),
)

_TABLES = ("validation_snapshots", "validation_snapshot_history")

_BACKFILL_SQL = """
UPDATE {table}
SET
    total_orders = COALESCE(
        (chart_data->'meta'->>'total_orders')::integer,
        total_orders,
        0
    ),
    filled_orders = COALESCE(
        (chart_data->'meta'->>'filled_orders')::integer,
        filled_orders,
        0
    ),
    rejected_orders = COALESCE(
        (chart_data->'meta'->>'rejected_orders')::integer,
        rejected_orders,
        0
    ),
    best_portfolio = COALESCE(
        chart_data->'meta'->>'best_portfolio',
        best_portfolio
    ),
    worst_portfolio = COALESCE(
        chart_data->'meta'->>'worst_portfolio',
        worst_portfolio
    ),
    best_strategy = COALESCE(
        chart_data->'meta'->>'best_strategy',
        best_strategy
    ),
    worst_strategy = COALESCE(
        chart_data->'meta'->>'worst_strategy',
        worst_strategy
    ),
    exchange_distribution = COALESCE(
        chart_data->'meta'->'exchange_distribution',
        exchange_distribution
    )
"""


def upgrade() -> None:
    for table in _TABLES:
        for name, col_type in _META_COLUMNS:
            op.add_column(table, sa.Column(name, col_type, nullable=True))

    for table in _TABLES:
        op.execute(_BACKFILL_SQL.format(table=table))
        op.execute(
            f"""
            UPDATE {table}
            SET
                total_orders = COALESCE(total_orders, 0),
                filled_orders = COALESCE(filled_orders, 0),
                rejected_orders = COALESCE(rejected_orders, 0)
            """
        )
        for int_col in ("total_orders", "filled_orders", "rejected_orders"):
            op.alter_column(
                table,
                int_col,
                existing_type=sa.Integer(),
                nullable=False,
                server_default="0",
            )
        for int_col in ("total_orders", "filled_orders", "rejected_orders"):
            op.alter_column(table, int_col, server_default=None)


def downgrade() -> None:
    for table in reversed(_TABLES):
        for name, _ in reversed(_META_COLUMNS):
            op.drop_column(table, name)
