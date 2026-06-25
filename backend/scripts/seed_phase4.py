"""
Phase 4 seeder: multi-asset registry, AI funds and their asset/strategy universes,
and the autonomous_v2 feature flag.

Idempotent: safe to run repeatedly. Run AFTER alembic migrations and after the base
mandates exist (app.initial_data.seed_db). Usage:

  python scripts/seed_phase4.py [--enable-autonomous]
"""
import os
import sys
import argparse
import logging

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.models import domain
from app.initial_data import seed_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
from app.services.settlement_constants import DEFAULT_FUND_WEEKLY_TARGETS
from app.services.fund_performance_service import format_target_return_label

logger = logging.getLogger("seed_phase4")


# symbol, display_name, asset_class, data_provider, data_symbol, execution_venue, quote_currency
ASSETS = [
    ("BTC/USDT", "Bitcoin", "CRYPTO", "binance", "BTC/USDT", "binance", "USDT"),
    ("ETH/USDT", "Ethereum", "CRYPTO", "binance", "ETH/USDT", "binance", "USDT"),
    ("SOL/USDT", "Solana", "CRYPTO", "binance", "SOL/USDT", "binance", "USDT"),
    ("XAUUSD", "Gold", "METAL", "yfinance", "GC=F", "SIMULATED", "USD"),
    ("XAGUSD", "Silver", "METAL", "yfinance", "SI=F", "SIMULATED", "USD"),
    ("WTIUSD", "Crude Oil (WTI)", "ENERGY", "yfinance", "CL=F", "SIMULATED", "USD"),
    ("SPX", "S&P 500", "EQUITY_INDEX", "yfinance", "^GSPC", "SIMULATED", "USD"),
    ("NDX", "Nasdaq 100", "EQUITY_INDEX", "yfinance", "^NDX", "SIMULATED", "USD"),
    ("EURUSD", "Euro / US Dollar", "FX", "yfinance", "EURUSD=X", "SIMULATED", "USD"),
    ("GBPUSD", "British Pound / US Dollar", "FX", "yfinance", "GBPUSD=X", "SIMULATED", "USD"),
]

# fund_id -> config
FUNDS = {
    "PRESERVE": {
        "name": "Preserve Fund",
        "description": "Capital-preservation AI mandate. Low volatility, heavy cash floor, "
                       "diversified across blue-chip crypto and safe-haven metals.",
        "mandate_id": "PRESERVE",
        "target_return_label": format_target_return_label(
            DEFAULT_FUND_WEEKLY_TARGETS["PRESERVE"],
            round(DEFAULT_FUND_WEEKLY_TARGETS["PRESERVE"] * 4.33, 2),
        ),
        "target_weekly_return_pct": DEFAULT_FUND_WEEKLY_TARGETS["PRESERVE"],
        "risk_label": "Low",
        "allocation_policy": {
            "method": "inverse_vol",
            "rebalance_freq_days": 7,
            "cash_floor_pct": 40.0,
            "max_assets": 4,
        },
        "assets": ["BTC/USDT", "ETH/USDT", "XAUUSD", "XAGUSD"],
    },
    "BALANCE": {
        "name": "Balance Fund",
        "description": "Balanced-growth AI mandate. Diversified multi-asset exposure with "
                       "regime-aware tilts across crypto, metals, equity indices and FX.",
        "mandate_id": "BALANCE",
        "target_return_label": format_target_return_label(
            DEFAULT_FUND_WEEKLY_TARGETS["BALANCE"],
            round(DEFAULT_FUND_WEEKLY_TARGETS["BALANCE"] * 4.33, 2),
        ),
        "target_weekly_return_pct": DEFAULT_FUND_WEEKLY_TARGETS["BALANCE"],
        "risk_label": "Medium",
        "allocation_policy": {
            "method": "inverse_vol",
            "rebalance_freq_days": 7,
            "cash_floor_pct": 20.0,
            "max_assets": 6,
        },
        "assets": ["BTC/USDT", "ETH/USDT", "SOL/USDT", "XAUUSD", "SPX", "EURUSD"],
    },
    "ALPHA": {
        "name": "Alpha Fund",
        "description": "Aggressive-growth AI mandate. Full multi-asset universe, momentum and "
                       "regime-driven concentration, minimal cash floor.",
        "mandate_id": "ALPHA",
        "target_return_label": format_target_return_label(
            DEFAULT_FUND_WEEKLY_TARGETS["ALPHA"],
            round(DEFAULT_FUND_WEEKLY_TARGETS["ALPHA"] * 4.33, 2),
        ),
        "target_weekly_return_pct": DEFAULT_FUND_WEEKLY_TARGETS["ALPHA"],
        "risk_label": "High",
        "allocation_policy": {
            "method": "regime_momentum",
            "rebalance_freq_days": 3,
            "cash_floor_pct": 5.0,
            "max_assets": 8,
        },
        "assets": [a[0] for a in ASSETS],
    },
}


def seed_assets(db):
    by_symbol = {}
    for symbol, name, klass, provider, data_symbol, venue, quote in ASSETS:
        asset = db.query(domain.Asset).filter(domain.Asset.symbol == symbol).first()
        if not asset:
            asset = domain.Asset(
                symbol=symbol,
                display_name=name,
                asset_class=klass,
                data_provider=provider,
                data_symbol=data_symbol,
                execution_venue=venue,
                quote_currency=quote,
                is_active=True,
                is_tradable=True,
            )
            db.add(asset)
        by_symbol[symbol] = asset
    db.commit()
    logger.info("Assets seeded: %d", db.query(domain.Asset).count())
    return by_symbol


def seed_funds(db, assets_by_symbol):
    active_strategies = db.query(domain.Strategy).all()
    for fund_id, cfg in FUNDS.items():
        fund = db.query(domain.Fund).filter(domain.Fund.id == fund_id).first()
        mandate = db.query(domain.Mandate).filter(
            domain.Mandate.id == cfg["mandate_id"], domain.Mandate.is_active == True
        ).first()
        if not fund:
            fund = domain.Fund(
                id=fund_id,
                name=cfg["name"],
                description=cfg["description"],
                mandate_pk_id=mandate.pk_id if mandate else None,
                allocation_policy=cfg["allocation_policy"],
                target_return_label=cfg["target_return_label"],
                target_weekly_return_pct=cfg.get("target_weekly_return_pct"),
                target_monthly_return_pct=round(cfg.get("target_weekly_return_pct", 1) * 4.33, 2) if cfg.get("target_weekly_return_pct") else None,
                risk_label=cfg["risk_label"],
                is_active=True,
            )
            db.add(fund)
            db.flush()
        else:
            # keep policy/labels fresh without duplicating rows
            fund.allocation_policy = cfg["allocation_policy"]
            fund.target_return_label = cfg["target_return_label"]
            fund.target_weekly_return_pct = cfg.get("target_weekly_return_pct")
            fund.target_monthly_return_pct = round(cfg.get("target_weekly_return_pct", 1) * 4.33, 2) if cfg.get("target_weekly_return_pct") else None
            fund.risk_label = cfg["risk_label"]
            if mandate:
                fund.mandate_pk_id = mandate.pk_id

        # Align the mandate whitelist with the fund's multi-asset universe so the
        # Risk Engine's allowed_assets check doesn't block legitimately-configured
        # fund assets. ALPHA stays "ALL".
        if mandate and mandate.allowed_assets and "ALL" not in mandate.allowed_assets:
            mandate.allowed_assets = sorted(set(list(mandate.allowed_assets) + list(cfg["assets"])))

        # Asset universe (idempotent per fund/asset pair)
        for symbol in cfg["assets"]:
            asset = assets_by_symbol.get(symbol)
            if not asset:
                continue
            exists = db.query(domain.FundAssetUniverse).filter(
                domain.FundAssetUniverse.fund_pk_id == fund.pk_id,
                domain.FundAssetUniverse.asset_pk_id == asset.pk_id,
            ).first()
            if not exists:
                max_w = float(100.0 / max(1, len(cfg["assets"]))) * 2.5
                db.add(domain.FundAssetUniverse(
                    fund_pk_id=fund.pk_id,
                    asset_pk_id=asset.pk_id,
                    min_weight_pct=0.0,
                    max_weight_pct=min(100.0, round(max_w, 2)),
                ))

        # Strategy universe (attach all known strategies, enabled across trending regimes)
        for strat in active_strategies:
            exists = db.query(domain.FundStrategyUniverse).filter(
                domain.FundStrategyUniverse.fund_pk_id == fund.pk_id,
                domain.FundStrategyUniverse.strategy_pk_id == strat.pk_id,
            ).first()
            if not exists:
                db.add(domain.FundStrategyUniverse(
                    fund_pk_id=fund.pk_id,
                    strategy_pk_id=strat.pk_id,
                    enabled_regimes=["BULL", "SIDEWAYS", "BEAR"],
                ))
    db.commit()
    logger.info("Funds seeded: %d", db.query(domain.Fund).count())


def seed_treasury_pools(db):
    """Ensure all institutional treasury pools exist (including LNX_INDEX)."""
    defaults = [
        ("RESERVE", "Reserve Pool", 20.0, 1_000_000.0),
        ("YIELD", "Yield Generation Pool", 40.0, 0.0),
        ("GROWTH", "Ecosystem Growth Pool", 15.0, 250_000.0),
        ("OPERATIONS", "Platform Operations", 10.0, 100_000.0),
        ("INSURANCE", "Risk Insurance Fund", 5.0, 500_000.0),
        ("LNX_INDEX", "LNX Index Pool", 10.0, 0.0),
    ]
    for pool_id, name, target_pct, balance in defaults:
        pool = db.query(domain.TreasuryPool).filter(domain.TreasuryPool.id == pool_id).first()
        if not pool:
            db.add(domain.TreasuryPool(
                id=pool_id, name=name, target_allocation_pct=target_pct, balance=balance, is_active=True,
            ))
    db.commit()
    logger.info("Treasury pools ready: %d", db.query(domain.TreasuryPool).count())


def ensure_global_settings(db, enable_autonomous: bool):
    gs = db.query(domain.GlobalSettings).filter(domain.GlobalSettings.id == "default").first()
    if not gs:
        gs = domain.GlobalSettings(id="default")
        db.add(gs)
    if enable_autonomous:
        gs.autonomous_v2_enabled = True
    db.commit()
    logger.info("GlobalSettings ready (autonomous_v2_enabled=%s).", gs.autonomous_v2_enabled)


def seed_phase4(enable_autonomous: bool = False):
    db = SessionLocal()
    try:
        seed_db(db)  # ensure base mandates exist
        assets_by_symbol = seed_assets(db)
        seed_funds(db, assets_by_symbol)
        seed_treasury_pools(db)
        ensure_global_settings(db, enable_autonomous)
        logger.info("Phase 4 seed complete.")
    except Exception as e:
        logger.error("Phase 4 seed failed: %s", e)
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--enable-autonomous", action="store_true",
                        help="Enable the autonomous_v2 manager feature flag.")
    args = parser.parse_args()
    seed_phase4(enable_autonomous=args.enable_autonomous)
