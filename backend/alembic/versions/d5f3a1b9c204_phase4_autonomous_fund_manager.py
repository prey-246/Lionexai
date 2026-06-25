"""Phase 4: autonomous multi-asset fund manager schema

Revision ID: d5f3a1b9c204
Revises: 4a92414eca12
Create Date: 2026-06-24 00:00:00.000000

Additive-only migration: new tables for the multi-asset registry, unified market
bars, AI funds + universes, portfolio allocations, rebalance audit, regime /
global market state, strategy scores and the LNX ecosystem index, plus a few
nullable columns on existing tables. No existing columns are dropped or altered,
so this is safe to run on a populated database.
"""
from alembic import op
import sqlalchemy as sa


revision = "d5f3a1b9c204"
down_revision = "4a92414eca12"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- Asset registry ---
    op.create_table(
        "assets",
        sa.Column("pk_id", sa.Integer(), primary_key=True),
        sa.Column("symbol", sa.String(), nullable=False),
        sa.Column("display_name", sa.String(), nullable=False),
        sa.Column("asset_class", sa.String(), nullable=False),
        sa.Column("data_provider", sa.String(), nullable=False, server_default="binance"),
        sa.Column("data_symbol", sa.String(), nullable=False),
        sa.Column("execution_venue", sa.String(), nullable=False, server_default="SIMULATED"),
        sa.Column("quote_currency", sa.String(), nullable=False, server_default="USD"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_tradable", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_assets_symbol", "assets", ["symbol"], unique=True)
    op.create_index("ix_assets_asset_class", "assets", ["asset_class"])

    # --- Unified market bars ---
    op.create_table(
        "market_bars",
        sa.Column("symbol", sa.String(), primary_key=True),
        sa.Column("timeframe", sa.String(), primary_key=True),
        sa.Column("timestamp", sa.DateTime(), primary_key=True),
        sa.Column("open", sa.Float(), nullable=False),
        sa.Column("high", sa.Float(), nullable=False),
        sa.Column("low", sa.Float(), nullable=False),
        sa.Column("close", sa.Float(), nullable=False),
        sa.Column("volume", sa.Float(), nullable=False, server_default="0"),
    )

    # --- Funds + universes ---
    op.create_table(
        "funds",
        sa.Column("pk_id", sa.Integer(), primary_key=True),
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("mandate_pk_id", sa.Integer(), nullable=True),
        sa.Column("allocation_policy", sa.JSON(), nullable=True),
        sa.Column("target_return_label", sa.String(), nullable=True),
        sa.Column("risk_label", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_funds_id", "funds", ["id"], unique=True)
    op.create_foreign_key("fk_funds_mandate", "funds", "mandates", ["mandate_pk_id"], ["pk_id"], use_alter=True)

    op.create_table(
        "fund_asset_universe",
        sa.Column("pk_id", sa.Integer(), primary_key=True),
        sa.Column("fund_pk_id", sa.Integer(), nullable=False),
        sa.Column("asset_pk_id", sa.Integer(), nullable=False),
        sa.Column("min_weight_pct", sa.Float(), nullable=False, server_default="0"),
        sa.Column("max_weight_pct", sa.Float(), nullable=False, server_default="100"),
    )
    op.create_index("ix_fau_fund", "fund_asset_universe", ["fund_pk_id"])
    op.create_foreign_key("fk_fau_fund", "fund_asset_universe", "funds", ["fund_pk_id"], ["pk_id"], use_alter=True)
    op.create_foreign_key("fk_fau_asset", "fund_asset_universe", "assets", ["asset_pk_id"], ["pk_id"], use_alter=True)

    op.create_table(
        "fund_strategy_universe",
        sa.Column("pk_id", sa.Integer(), primary_key=True),
        sa.Column("fund_pk_id", sa.Integer(), nullable=False),
        sa.Column("strategy_pk_id", sa.Integer(), nullable=False),
        sa.Column("enabled_regimes", sa.JSON(), nullable=True),
    )
    op.create_index("ix_fsu_fund", "fund_strategy_universe", ["fund_pk_id"])
    op.create_foreign_key("fk_fsu_fund", "fund_strategy_universe", "funds", ["fund_pk_id"], ["pk_id"], use_alter=True)
    op.create_foreign_key("fk_fsu_strategy", "fund_strategy_universe", "strategies", ["strategy_pk_id"], ["pk_id"], use_alter=True)

    # --- Portfolio allocations + rebalance audit ---
    op.create_table(
        "portfolio_allocations",
        sa.Column("pk_id", sa.Integer(), primary_key=True),
        sa.Column("portfolio_id", sa.Integer(), nullable=False),
        sa.Column("asset_pk_id", sa.Integer(), nullable=False),
        sa.Column("strategy_pk_id", sa.Integer(), nullable=True),
        sa.Column("target_weight_pct", sa.Float(), nullable=False, server_default="0"),
        sa.Column("current_weight_pct", sa.Float(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_pa_portfolio", "portfolio_allocations", ["portfolio_id"])
    op.create_foreign_key("fk_pa_portfolio", "portfolio_allocations", "portfolios", ["portfolio_id"], ["pk_id"], use_alter=True)
    op.create_foreign_key("fk_pa_asset", "portfolio_allocations", "assets", ["asset_pk_id"], ["pk_id"], use_alter=True)
    op.create_foreign_key("fk_pa_strategy", "portfolio_allocations", "strategies", ["strategy_pk_id"], ["pk_id"], use_alter=True)

    op.create_table(
        "rebalance_events",
        sa.Column("pk_id", sa.Integer(), primary_key=True),
        sa.Column("id", sa.String(length=30), nullable=False),
        sa.Column("portfolio_id", sa.Integer(), nullable=False),
        sa.Column("trigger", sa.String(), nullable=True),
        sa.Column("regime", sa.String(), nullable=True),
        sa.Column("global_risk_score", sa.Float(), nullable=True),
        sa.Column("decisions", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_rebalance_events_id", "rebalance_events", ["id"], unique=True)
    op.create_index("ix_reb_portfolio", "rebalance_events", ["portfolio_id"])
    op.create_index("ix_reb_created", "rebalance_events", ["created_at"])
    op.create_foreign_key("fk_reb_portfolio", "rebalance_events", "portfolios", ["portfolio_id"], ["pk_id"], use_alter=True)

    # --- Regime + global market state ---
    op.create_table(
        "market_regimes",
        sa.Column("pk_id", sa.Integer(), primary_key=True),
        sa.Column("scope", sa.String(), nullable=False),
        sa.Column("regime", sa.String(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("indicators", sa.JSON(), nullable=True),
        sa.Column("detected_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_market_regimes_scope", "market_regimes", ["scope"])
    op.create_index("ix_market_regimes_detected", "market_regimes", ["detected_at"])

    op.create_table(
        "global_market_state",
        sa.Column("pk_id", sa.Integer(), primary_key=True),
        sa.Column("global_risk_score", sa.Float(), nullable=False, server_default="50"),
        sa.Column("market_regime", sa.String(), nullable=False, server_default="SIDEWAYS"),
        sa.Column("risk_on_off", sa.String(), nullable=False, server_default="NEUTRAL"),
        sa.Column("asset_ranking", sa.JSON(), nullable=True),
        sa.Column("macro_inputs", sa.JSON(), nullable=True),
        sa.Column("computed_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_global_market_state_computed", "global_market_state", ["computed_at"])

    # --- Strategy scores ---
    op.create_table(
        "strategy_scores",
        sa.Column("pk_id", sa.Integer(), primary_key=True),
        sa.Column("strategy_pk_id", sa.Integer(), nullable=True),
        sa.Column("strategy_name", sa.String(), nullable=False),
        sa.Column("asset_symbol", sa.String(), nullable=True),
        sa.Column("period", sa.String(), nullable=False, server_default="30D"),
        sa.Column("sharpe", sa.Float(), nullable=False, server_default="0"),
        sa.Column("win_rate", sa.Float(), nullable=False, server_default="0"),
        sa.Column("max_drawdown", sa.Float(), nullable=False, server_default="0"),
        sa.Column("profit_factor", sa.Float(), nullable=False, server_default="0"),
        sa.Column("composite_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("rank", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("computed_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_strategy_scores_name", "strategy_scores", ["strategy_name"])
    op.create_index("ix_strategy_scores_asset", "strategy_scores", ["asset_symbol"])
    op.create_index("ix_strategy_scores_computed", "strategy_scores", ["computed_at"])
    op.create_foreign_key("fk_ss_strategy", "strategy_scores", "strategies", ["strategy_pk_id"], ["pk_id"], use_alter=True)

    # --- LNX ecosystem index ---
    op.create_table(
        "lnx_index_snapshots",
        sa.Column("pk_id", sa.Integer(), primary_key=True),
        sa.Column("nav", sa.Float(), nullable=False, server_default="0"),
        sa.Column("treasury_health", sa.Float(), nullable=False, server_default="0"),
        sa.Column("strategy_performance", sa.Float(), nullable=False, server_default="0"),
        sa.Column("execution_quality", sa.Float(), nullable=False, server_default="0"),
        sa.Column("aum_growth", sa.Float(), nullable=False, server_default="0"),
        sa.Column("composite_index", sa.Float(), nullable=False, server_default="0"),
        sa.Column("computed_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_lnx_index_computed", "lnx_index_snapshots", ["computed_at"])

    # --- Additive columns on existing tables ---
    op.add_column("portfolios", sa.Column("fund_pk_id", sa.Integer(), nullable=True))
    op.add_column("portfolios", sa.Column("auto_managed", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_foreign_key("fk_portfolios_fund", "portfolios", "funds", ["fund_pk_id"], ["pk_id"], use_alter=True)

    op.add_column("trades", sa.Column("asset_pk_id", sa.Integer(), nullable=True))
    op.create_foreign_key("fk_trades_asset", "trades", "assets", ["asset_pk_id"], ["pk_id"], use_alter=True)

    op.add_column(
        "global_settings",
        sa.Column("autonomous_v2_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("global_settings", "autonomous_v2_enabled")

    op.drop_constraint("fk_trades_asset", "trades", type_="foreignkey")
    op.drop_column("trades", "asset_pk_id")

    op.drop_constraint("fk_portfolios_fund", "portfolios", type_="foreignkey")
    op.drop_column("portfolios", "auto_managed")
    op.drop_column("portfolios", "fund_pk_id")

    op.drop_table("lnx_index_snapshots")
    op.drop_table("strategy_scores")
    op.drop_table("global_market_state")
    op.drop_table("market_regimes")
    op.drop_table("rebalance_events")
    op.drop_table("portfolio_allocations")
    op.drop_table("fund_strategy_universe")
    op.drop_table("fund_asset_universe")
    op.drop_table("funds")
    op.drop_table("market_bars")
    op.drop_table("assets")
