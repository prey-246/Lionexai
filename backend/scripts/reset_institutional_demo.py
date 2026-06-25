"""
Institutional demo environment reset and re-seed.

Purges demo portfolios, trades, settlements, validation snapshots, and non-essential
users while preserving schema, migrations, admin accounts, and Phase 4 foundation data.
Re-seeds LNX-PRESERVE/BALANCED/ALPHA portfolios with realistic autonomous activity.

Usage:
  python scripts/reset_institutional_demo.py --confirm
  python scripts/reset_institutional_demo.py --confirm --enable-autonomous
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
import uuid
import random
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from passlib.context import CryptContext
from sqlalchemy import text

from app.core.database import SessionLocal
from app.models import domain
from app.initial_data import seed_db
from app.services.audit_service import create_audit_log, collapse_infrastructure_reconnect_logs
from app.services.settlement_constants import PROFIT_ROUTING_SPLIT, DEFAULT_FUND_WEEKLY_TARGETS
from app.services.validation_service import update_validation_snapshots_job
from app.engines.lnx_index import LNXIndexEngine
from scripts.seed_phase4 import seed_phase4

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("reset_institutional_demo")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

PRESERVED_USER_EMAILS = {
    "admin@google.com",
    "operator1@google.com",
    "risk1@google.com",
    "client1@google.com",
    "client2@google.com",
    "client3@google.com",
}

# fund_id, portfolio_id, principal, win_rate_target, client_index
PORTFOLIO_SPECS = [
    ("PRESERVE", "LNX-PRESERVE-001", 500_000, 0.66, 0),
    ("PRESERVE", "LNX-PRESERVE-002", 350_000, 0.67, 1),
    ("PRESERVE", "LNX-PRESERVE-003", 250_000, 0.65, 2),
    ("BALANCE", "LNX-BALANCED-001", 400_000, 0.62, 0),
    ("BALANCE", "LNX-BALANCED-002", 300_000, 0.61, 1),
    ("BALANCE", "LNX-BALANCED-003", 200_000, 0.60, 2),
    ("ALPHA", "LNX-ALPHA-001", 200_000, 0.58, 0),
    ("ALPHA", "LNX-ALPHA-002", 150_000, 0.57, 1),
    ("ALPHA", "LNX-ALPHA-003", 100_000, 0.56, 2),
]

WEEKS_OF_HISTORY = 13
TRADES_PER_WEEK = 6
SYMBOL_PRICES = {
    "BTC/USDT": 95000, "ETH/USDT": 3400, "SOL/USDT": 180,
    "XAUUSD": 2650, "XAGUSD": 31, "SPX": 5200, "EURUSD": 1.08,
}


def _iso_week_key(dt: datetime) -> str:
    iso = dt.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def purge_demo_data(db) -> None:
    """Remove demo transactional data; preserve mandates, assets, funds, admin users."""
    logger.info("Purging demo transactional data...")
    tables_in_order = [
        "treasury_transactions",
        "client_settlements",
        "rebalance_events",
        "portfolio_allocations",
        "equity_curves",
        "risk_events",
        "reports",
        "trades",
        "validation_snapshot_history",
        "validation_snapshots",
        "lnx_index_snapshots",
        "audit_logs",
    ]
    for table in tables_in_order:
        db.execute(text(f"DELETE FROM {table}"))
    db.execute(text("DELETE FROM portfolios"))
    db.query(domain.User).filter(domain.User.email.notin_(PRESERVED_USER_EMAILS)).delete(synchronize_session=False)
    db.commit()
    logger.info("Purge complete.")


def _ensure_users(db):
    specs = [
        ("admin@google.com", "admin"),
        ("operator1@google.com", "operator"),
        ("risk1@google.com", "risk_manager"),
        ("client1@google.com", "client"),
        ("client2@google.com", "client"),
        ("client3@google.com", "client"),
    ]
    users = {}
    for email, role in specs:
        user = db.query(domain.User).filter(domain.User.email == email).first()
        if not user:
            user = domain.User(
                id=f"usr_{uuid.uuid4().hex[:12]}",
                email=email,
                hashed_password=pwd_context.hash("password123"),
                is_active=True,
                role_tier=role,
            )
            db.add(user)
        users[email] = user
    db.commit()
    clients = [users[f"client{i}@google.com"] for i in (1, 2, 3)]
    return clients


def _reset_treasury_pools(db):
    defaults = {
        "RESERVE": 1_000_000.0,
        "YIELD": 250_000.0,
        "GROWTH": 400_000.0,
        "OPERATIONS": 150_000.0,
        "INSURANCE": 500_000.0,
        "LNX_INDEX": 75_000.0,
    }
    for pool_id, balance in defaults.items():
        pool = db.query(domain.TreasuryPool).filter(domain.TreasuryPool.id == pool_id).first()
        if pool:
            pool.balance = balance


def _create_portfolios(db, clients):
    portfolios = []
    funds = {f.id: f for f in db.query(domain.Fund).all()}
    mandates = {m.id: m for m in db.query(domain.Mandate).all()}
    for fund_id, pid, principal, win_rate, client_idx in PORTFOLIO_SPECS:
        fund = funds.get(fund_id)
        mandate = mandates.get(fund_id)
        if not fund or not mandate:
            logger.warning("Skipping %s — fund/mandate missing", pid)
            continue
        p = domain.Portfolio(
            id=pid,
            user_id=clients[client_idx].id,
            mandate_pk_id=mandate.pk_id,
            fund_pk_id=fund.pk_id,
            auto_managed=True,
            principal=principal,
            total_equity=principal,
            available_margin=principal * 0.85,
            current_drawdown_pct=round(random.uniform(0.5, 2.5), 2),
            created_at=datetime.utcnow() - timedelta(days=WEEKS_OF_HISTORY * 7),
        )
        db.add(p)
        portfolios.append((p, fund, principal, win_rate))
    db.commit()
    for p, *_ in portfolios:
        db.refresh(p)
    return portfolios


def _seed_allocations(db, portfolio, fund):
    assets = (
        db.query(domain.Asset)
        .join(domain.FundAssetUniverse, domain.FundAssetUniverse.asset_pk_id == domain.Asset.pk_id)
        .filter(domain.FundAssetUniverse.fund_pk_id == fund.pk_id)
        .all()
    )
    if not assets:
        return
    weight = round(100.0 / len(assets), 2)
    for asset in assets:
        db.add(domain.PortfolioAllocation(
            portfolio_id=portfolio.pk_id,
            asset_pk_id=asset.pk_id,
            target_weight_pct=weight,
            current_weight_pct=weight * random.uniform(0.92, 1.05),
        ))
    db.add(domain.RebalanceEvent(
        id=f"reb_{uuid.uuid4().hex[:12]}",
        portfolio_id=portfolio.pk_id,
        trigger="INITIAL",
        regime="SIDEWAYS",
        global_risk_score=42.0,
        decisions={"method": fund.allocation_policy.get("method") if fund.allocation_policy else "inverse_vol"},
        created_at=portfolio.created_at + timedelta(days=1),
    ))
    db.add(domain.RebalanceEvent(
        id=f"reb_{uuid.uuid4().hex[:12]}",
        portfolio_id=portfolio.pk_id,
        trigger="SCHEDULED",
        regime="BULL",
        global_risk_score=38.0,
        decisions={"note": "Weekly rebalance"},
        created_at=datetime.utcnow() - timedelta(days=14),
    ))


def _seed_trades_and_equity(db, portfolio, fund, win_rate: float, symbols: list[str]):
    weekly_pct = fund.target_weekly_return_pct or DEFAULT_FUND_WEEKLY_TARGETS.get(fund.id, 1.0)
    equity = portfolio.principal
    now = datetime.utcnow()
    curve_points = [(portfolio.created_at, equity)]

    for week in range(WEEKS_OF_HISTORY):
        week_start = now - timedelta(weeks=WEEKS_OF_HISTORY - week)
        week_pnl_target = equity * (weekly_pct / 100.0) * random.uniform(1.05, 1.35)
        week_pnl = 0.0
        for t in range(TRADES_PER_WEEK):
            sym = symbols[t % len(symbols)]
            price = SYMBOL_PRICES.get(sym, 100)
            qty = round(random.uniform(0.01, 0.8), 4) if "USD" in sym and "/" in sym else round(random.uniform(0.5, 5), 2)
            is_win = random.random() < win_rate
            pnl = round(random.uniform(80, 450) if is_win else -random.uniform(40, 220), 2)
            if t == TRADES_PER_WEEK - 1:
                pnl = round(week_pnl_target - week_pnl, 2)
            week_pnl += pnl
            ts = week_start + timedelta(days=t % 6, hours=random.randint(8, 20))
            db.add(domain.Trade(
                id=f"trd_{uuid.uuid4().hex[:12]}",
                portfolio_id=portfolio.pk_id,
                symbol=sym,
                side="BUY" if t % 2 == 0 else "SELL",
                quantity=qty,
                entry_price=price,
                exit_price=price * (1.01 if pnl > 0 else 0.99) if t % 2 else None,
                status="CLOSED" if t % 2 else "OPEN",
                pnl=pnl if t % 2 else None,
                exchange="simulated",
                execution_latency_ms=round(random.uniform(45, 180), 1),
                strategy_name=f"AUTO:{fund.id}",
                trade_source="AUTONOMOUS",
                created_at=ts,
                closed_at=ts + timedelta(hours=1) if t % 2 else None,
            ))
        equity = round(equity + week_pnl_target, 2)
        curve_points.append((week_start + timedelta(days=7), equity))

    portfolio.total_equity = equity
    portfolio.available_margin = equity * 0.85
    for ts, eq in curve_points:
        db.add(domain.EquityCurve(portfolio_id=portfolio.pk_id, equity=eq, timestamp=ts))


def _seed_settlements(db, portfolio, fund):
    weekly_pct = fund.target_weekly_return_pct or DEFAULT_FUND_WEEKLY_TARGETS.get(fund.id, 1.0)
    opening = portfolio.principal
    now = datetime.utcnow()

    for week in range(WEEKS_OF_HISTORY):
        period_end = now - timedelta(weeks=WEEKS_OF_HISTORY - week - 1)
        period_start = period_end - timedelta(days=7)
        week_key = _iso_week_key(period_start)
        target_gain = opening * (weekly_pct / 100.0)
        period_pnl = target_gain * random.uniform(1.08, 1.45)
        excess = period_pnl - target_gain
        closing = opening + target_gain

        settlement = domain.ClientSettlement(
            id=f"stl_{uuid.uuid4().hex[:12]}",
            portfolio_id=portfolio.pk_id,
            period_start=period_start,
            period_end=period_end,
            iso_week_key=week_key,
            opening_equity=round(opening, 2),
            closing_marked_equity=round(closing, 2),
            period_pnl=round(period_pnl, 2),
            target_return_pct=weekly_pct,
            client_entitlement=round(target_gain, 2),
            excess_routed=0.0,
            shortfall_topup=0.0,
            uncovered=0.0,
            status="SETTLED",
            created_at=period_end,
        )
        db.add(settlement)
        db.flush()

        routed = {}
        for pool_id, pct in PROFIT_ROUTING_SPLIT.items():
            share = round(excess * (pct / 100.0), 2)
            if share <= 0:
                continue
            pool = db.query(domain.TreasuryPool).filter(domain.TreasuryPool.id == pool_id).first()
            if pool:
                pool.balance += share
                db.add(domain.TreasuryTransaction(
                    id=f"tx_{uuid.uuid4().hex[:12]}",
                    pool_pk_id=pool.pk_id,
                    amount=share,
                    transaction_type="PROFIT_ROUTING",
                    reference_id=portfolio.id,
                    settlement_pk_id=settlement.pk_id,
                    description=f"Excess profit routed from {portfolio.id} ({pct}%).",
                    timestamp=period_end,
                ))
                routed[pool_id] = share

        settlement.excess_routed = round(sum(routed.values()), 2)
        settlement.breakdown = {"routed": routed}
        opening = closing

    portfolio.last_settled_at = now


def _seed_audit_logs(db, portfolios):
    samples = [
        ("WEEKLY_SETTLEMENT", "Settlement", "Weekly client settlement completed."),
        ("PROFIT_ROUTING", "Treasury", "Excess profit routed to ecosystem pools."),
        ("REBALANCE_SCHEDULED", "Rebalance", "Allocation engine rebalance executed."),
        ("ALLOCATION_UPDATED", "Allocation", "Target weights refreshed from fund universe."),
        ("AUTONOMOUS_TRADE_EXECUTED", "Trading", "Autonomous multi-asset trade filled."),
        ("RISK_CHECK_PASSED", "Risk", "Pre-trade risk validation passed."),
        ("INFRASTRUCTURE_HEALTH_SUMMARY", "Infrastructure", "Exchange connectivity healthy."),
    ]
    for i, (action, category, desc) in enumerate(samples):
        pf = portfolios[i % len(portfolios)][0]
        create_audit_log(
            db,
            action_type=action,
            description=f"{desc} Portfolio {pf.id}.",
            metadata_json={"portfolio": pf.id, "category": category, "demo": True},
        )


def _seed_lnx_history(db, days: int = 90):
    engine = LNXIndexEngine(db)
    for d in range(days, 0, -3):
        ts = datetime.utcnow() - timedelta(days=d)
        snap = engine.compute(store=True)
        snap.computed_at = ts
    db.commit()


def reset_institutional_demo(enable_autonomous: bool = False):
    db = SessionLocal()
    try:
        purge_demo_data(db)
        seed_db(db)
        seed_phase4(enable_autonomous=enable_autonomous)
        db = SessionLocal()

        clients = _ensure_users(db)
        _reset_treasury_pools(db)
        portfolios = _create_portfolios(db, clients)

        for portfolio, fund, principal, win_rate in portfolios:
            universe = (
                db.query(domain.Asset)
                .join(domain.FundAssetUniverse, domain.FundAssetUniverse.asset_pk_id == domain.Asset.pk_id)
                .filter(domain.FundAssetUniverse.fund_pk_id == fund.pk_id)
                .all()
            )
            symbols = [a.symbol for a in universe] or ["BTC/USDT", "ETH/USDT"]
            _seed_allocations(db, portfolio, fund)
            _seed_trades_and_equity(db, portfolio, fund, win_rate, symbols)
            _seed_settlements(db, portfolio, fund)

        _seed_audit_logs(db, portfolios)
        collapsed = collapse_infrastructure_reconnect_logs(db)
        _seed_lnx_history(db)
        db.commit()

        update_validation_snapshots_job()

        logger.info(
            "Institutional demo ready: %d portfolios, %d trades, %d settlements, %d audit logs collapsed.",
            len(portfolios),
            db.query(domain.Trade).count(),
            db.query(domain.ClientSettlement).count(),
            collapsed,
        )
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reset and re-seed institutional demo environment")
    parser.add_argument("--confirm", action="store_true", help="Required to execute destructive purge")
    parser.add_argument("--enable-autonomous", action="store_true", help="Enable autonomous_v2 after seed")
    args = parser.parse_args()
    if not args.confirm:
        print("Refusing to run without --confirm (this deletes demo portfolios, trades, and snapshots).")
        sys.exit(1)
    reset_institutional_demo(enable_autonomous=args.enable_autonomous)
