"""
Comprehensive demo environment seeder for institutional demonstrations.

Targets:
  - 10+ portfolios
  - 5+ strategies
  - 100+ trades
  - 250+ audit logs
  - 25+ treasury events
  - 50+ news articles
  - 50+ risk events

Usage:
  python scripts/seed_demo_environment.py
"""
import os
import sys
import uuid
import random
import logging
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from passlib.context import CryptContext
from app.core.database import SessionLocal
from app.models import domain
from app.initial_data import seed_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SYMBOLS = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
STRATEGY_TYPES = ["ma_crossover", "rsi_mean_reversion"]
EXCHANGES = ["binance", "bybit"]


def seed_demo_environment():
    db = SessionLocal()
    try:
        seed_db(db)
        logger.info("Mandates seeded.")

        users = _ensure_users(db)
        mandates = db.query(domain.Mandate).filter(domain.Mandate.is_active == True).all()
        if not mandates:
            logger.error("No mandates found.")
            return

        portfolios = _seed_portfolios(db, users, mandates)
        strategies = _seed_strategies(db, portfolios)
        trades = _seed_trades(db, portfolios)
        _seed_audit_logs(db, portfolios, strategies)
        _seed_risk_events(db, portfolios)
        _seed_news(db)
        _seed_treasury(db)

        db.commit()
        logger.info(
            "Demo environment ready: %d portfolios, %d strategies, %d trades, "
            "%d audit logs, %d risk events, %d news articles.",
            len(portfolios),
            len(strategies),
            trades,
            db.query(domain.AuditLog).count(),
            db.query(domain.RiskEvent).count(),
            db.query(domain.MarketNewsArticle).count(),
        )
    except Exception as e:
        logger.error(f"Demo seed failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def _ensure_users(db):
    specs = [
        ("admin@lionex.ai", "admin"),
        ("operator1@lionex.ai", "operator"),
        ("operator2@lionex.ai", "operator"),
        ("risk1@lionex.ai", "risk_manager"),
        ("risk2@lionex.ai", "risk_manager"),
        ("client1@lionex.ai", "client"),
        ("client2@lionex.ai", "client"),
        ("client3@lionex.ai", "client"),
    ]
    users = []
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
        users.append(user)
    db.commit()
    return users


def _seed_portfolios(db, users, mandates):
    clients = [u for u in users if u.role_tier == "client"]
    existing = db.query(domain.Portfolio).count()
    portfolios = list(db.query(domain.Portfolio).all())
    target = max(0, 12 - existing)

    equities = [25000, 50000, 75000, 100000, 150000, 200000, 350000, 500000]
    for i in range(target):
        client = clients[i % len(clients)]
        mandate = mandates[i % len(mandates)]
        p = domain.Portfolio(
            id=f"PORT-{uuid.uuid4().hex[:4].upper()}",
            user_id=client.id,
            mandate_pk_id=mandate.pk_id,
            total_equity=equities[i % len(equities)],
            available_margin=equities[i % len(equities)] * 0.9,
            current_drawdown_pct=round(random.uniform(0, 3), 2),
        )
        db.add(p)
        portfolios.append(p)
    db.commit()
    return portfolios


def _seed_strategies(db, portfolios):
    existing = db.query(domain.Strategy).count()
    strategies = list(db.query(domain.Strategy).all())
    names = [
        ("Lion Alpha Momentum", "ma_crossover", "ALPHA"),
        ("Lion Balance RSI", "rsi_mean_reversion", "BALANCE"),
        ("Lion Preserve Steady", "ma_crossover", "PRESERVE"),
        ("BTC Trend Follower", "ma_crossover", "ALPHA"),
        ("ETH Mean Reversion", "rsi_mean_reversion", "BALANCE"),
        ("Multi-Asset Sentinel", "rsi_mean_reversion", "ALPHA"),
    ]
    for i, (name, stype, _) in enumerate(names):
        if existing + i >= 6 and db.query(domain.Strategy).filter(domain.Strategy.name == name).first():
            continue
        if db.query(domain.Strategy).filter(domain.Strategy.name == name).first():
            continue
        portfolio = portfolios[i % len(portfolios)] if portfolios else None
        s = domain.Strategy(
            id=f"strat_{uuid.uuid4().hex[:8]}",
            name=name,
            description=f"Demo strategy: {name}",
            parameters={
                "strategy_type": stype,
                "assigned_portfolio_id": portfolio.id if portfolio else None,
                "execution_exchange": EXCHANGES[i % len(EXCHANGES)],
                "fast_period": 10,
                "slow_period": 30,
            },
            is_active=i < 3,
        )
        db.add(s)
        strategies.append(s)
    db.commit()
    return strategies


def _seed_trades(db, portfolios):
    existing = db.query(domain.Trade).count()
    needed = max(0, 120 - existing)
    count = 0
    for i in range(needed):
        portfolio = portfolios[i % len(portfolios)]
        symbol = SYMBOLS[i % len(SYMBOLS)]
        side = "BUY" if i % 2 == 0 else "SELL"
        price = 65000 if "BTC" in symbol else (3500 if "ETH" in symbol else 150)
        qty = round(random.uniform(0.01, 0.5), 4)
        pnl = round(random.uniform(-500, 1200), 2) if side == "SELL" else 0
        created = datetime.utcnow() - timedelta(days=random.randint(0, 30), hours=random.randint(0, 23))
        db.add(domain.Trade(
            id=f"trd_{uuid.uuid4().hex[:12]}",
            portfolio_id=portfolio.pk_id,
            symbol=symbol,
            side=side,
            quantity=qty,
            entry_price=price,
            exit_price=price * 1.02 if side == "SELL" else None,
            status="CLOSED" if side == "SELL" else "OPEN",
            pnl=pnl if side == "SELL" else None,
            created_at=created,
            closed_at=created + timedelta(hours=2) if side == "SELL" else None,
        ))
        count += 1
    db.commit()
    return existing + count


def _seed_audit_logs(db, portfolios, strategies):
    existing = db.query(domain.AuditLog).count()
    needed = max(0, 280 - existing)
    action_types = [
        "AUTONOMOUS_TRADE_EXECUTED_BINANCE",
        "AUTONOMOUS_TRADE_EXECUTED_BYBIT",
        "ORDER_FILLED",
        "ORDER_REJECTED",
        "RISK_REJECTION",
        "ORDER_CANCELLED",
        "EXCHANGE_RECONNECTED",
        "TRADE_EXECUTED",
        "STRATEGY_UPDATE",
        "REPORT_GENERATE",
    ]
    for i in range(needed):
        portfolio = portfolios[i % len(portfolios)]
        strategy = strategies[i % len(strategies)] if strategies else None
        action = action_types[i % len(action_types)]
        ts = datetime.utcnow() - timedelta(days=i % 3, hours=i % 24)
        db.add(domain.AuditLog(
            id=f"aud_{uuid.uuid4().hex[:12]}",
            action_type=action,
            description=f"Demo audit event #{i + 1}: {action}",
            metadata_json={
                "portfolio": portfolio.id,
                "exchange": EXCHANGES[i % len(EXCHANGES)],
                "symbol": SYMBOLS[i % len(SYMBOLS)],
                "side": "BUY" if i % 2 == 0 else "SELL",
                "latency_ms": round(random.uniform(80, 450), 2),
                "strategy": strategy.name if strategy else None,
            },
            timestamp=ts,
        ))
    db.commit()


def _seed_risk_events(db, portfolios):
    existing = db.query(domain.RiskEvent).count()
    needed = max(0, 55 - existing)
    types = ["RISK_REJECTION", "MAX_DRAWDOWN_BREACH", "LEVERAGE_EXCEEDED", "DAILY_LOSS_BREACH", "AI_SENTIMENT_BLOCK"]
    for i in range(needed):
        portfolio = portfolios[i % len(portfolios)]
        db.add(domain.RiskEvent(
            id=f"re_{uuid.uuid4().hex[:12]}",
            portfolio_id=portfolio.pk_id,
            event_type=types[i % len(types)],
            severity="WARNING" if i % 3 else "CRITICAL",
            description=f"Demo risk event: {types[i % len(types)]}",
            details={"demo": True, "symbol": SYMBOLS[i % len(SYMBOLS)]},
            triggered_at=datetime.utcnow() - timedelta(days=i % 14),
        ))
    db.commit()


def _seed_news(db):
    existing = db.query(domain.MarketNewsArticle).count()
    needed = max(0, 55 - existing)
    headlines = [
        "Bitcoin consolidates above key support level",
        "Ethereum network activity reaches quarterly high",
        "Institutional flows into digital assets accelerate",
        "Macro data signals cautious risk appetite",
        "Solana ecosystem sees renewed developer interest",
    ]
    for i in range(needed):
        db.add(domain.MarketNewsArticle(
            id=f"news_{uuid.uuid4().hex[:10]}",
            title=headlines[i % len(headlines)],
            source="CoinDesk Demo Feed",
            url=f"https://demo.lionex.ai/news/{i}",
            content=f"Demo market intelligence article #{i + 1}. Illustrative content for platform demonstration.",
            published_at=datetime.utcnow() - timedelta(hours=i * 3),
        ))
    db.commit()


def _seed_treasury(db):
    existing = db.query(domain.TreasuryTransaction).count()
    needed = max(0, 30 - existing)
    pools = db.query(domain.TreasuryPool).all()
    if len(pools) < 2:
        return
    for i in range(needed):
        pool = pools[i % len(pools)]
        db.add(domain.TreasuryTransaction(
            id=f"tx_{uuid.uuid4().hex[:12]}",
            pool_pk_id=pool.pk_id,
            amount=round(random.uniform(1000, 25000), 2),
            transaction_type="DEMO_REBALANCING",
            description=f"Demo treasury event #{i + 1}",
            timestamp=datetime.utcnow() - timedelta(days=i % 20),
        ))
    db.commit()


if __name__ == "__main__":
    seed_demo_environment()
