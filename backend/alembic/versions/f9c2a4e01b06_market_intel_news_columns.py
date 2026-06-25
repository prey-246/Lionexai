"""Market intelligence news region/asset_class columns

Revision ID: f9c2a4e01b06
Revises: e6a8c3d12f05
Create Date: 2026-06-24 14:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "f9c2a4e01b06"
down_revision = "e6a8c3d12f05"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("market_news_articles", sa.Column("region", sa.String(length=20), nullable=True))
    op.add_column("market_news_articles", sa.Column("asset_classes", sa.JSON(), nullable=True))
    op.create_index("ix_market_news_region", "market_news_articles", ["region"])


def downgrade() -> None:
    op.drop_index("ix_market_news_region", table_name="market_news_articles")
    op.drop_column("market_news_articles", "asset_classes")
    op.drop_column("market_news_articles", "region")
