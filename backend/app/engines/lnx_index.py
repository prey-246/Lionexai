"""LNX Ecosystem Performance Index engine.

Computes a composite health index from treasury NAV, AUM growth, trading performance,
reserve strength, and execution quality. Persists snapshots to `lnx_index_snapshots`.
"""
import logging
from datetime import datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models import domain

logger = logging.getLogger("nexa.lnx_index")

LNX_SUPPLY = 100_000_000.0


def _treasury_nav(db: Session) -> float:
    return float(db.query(func.sum(domain.TreasuryPool.balance)).scalar() or 0.0)


def _reserve_ratio(db: Session, nav: float) -> float:
    reserve = db.query(domain.TreasuryPool).filter(domain.TreasuryPool.id == "RESERVE").first()
    if not nav or not reserve:
        return 0.0
    return min(100.0, (reserve.balance / nav) * 100.0)


def _aum(db: Session) -> float:
    return float(
        db.query(func.sum(domain.Portfolio.total_equity))
        .filter(domain.Portfolio.auto_managed == True)
        .scalar() or 0.0
    )


def _trading_profit_30d(db: Session) -> float:
    cutoff = datetime.utcnow() - timedelta(days=30)
    return float(
        db.query(func.sum(domain.Trade.pnl))
        .filter(domain.Trade.status == "CLOSED", domain.Trade.closed_at >= cutoff)
        .scalar() or 0.0
    )


def _execution_quality(db: Session) -> float:
    """Fill rate proxy from recent autonomous trades (0-100)."""
    cutoff = datetime.utcnow() - timedelta(days=7)
    total = db.query(func.count(domain.Trade.pk_id)).filter(
        domain.Trade.trade_source == "AUTONOMOUS",
        domain.Trade.created_at >= cutoff,
    ).scalar() or 0
    if total == 0:
        return 75.0
    filled = db.query(func.count(domain.Trade.pk_id)).filter(
        domain.Trade.trade_source == "AUTONOMOUS",
        domain.Trade.created_at >= cutoff,
        domain.Trade.status.in_(("OPEN", "CLOSED")),
    ).scalar() or 0
    return min(100.0, (filled / total) * 100.0)


def _aum_growth_pct(db: Session) -> float:
    week_ago = datetime.utcnow() - timedelta(days=7)
    old = (
        db.query(domain.LNXIndexSnapshot)
        .filter(domain.LNXIndexSnapshot.computed_at <= week_ago)
        .order_by(domain.LNXIndexSnapshot.computed_at.desc())
        .first()
    )
    current_aum = _aum(db)
    if not old or old.aum_growth <= 0:
        return 0.0
    return round((current_aum / old.aum_growth - 1.0) * 100.0, 4) if old.aum_growth else 0.0


class LNXIndexEngine:
    def __init__(self, db: Session):
        self.db = db

    def compute(self, store: bool = True) -> domain.LNXIndexSnapshot:
        nav_total = _treasury_nav(self.db)
        reserve_ratio = _reserve_ratio(self.db, nav_total)
        aum = _aum(self.db)
        profit_30d = _trading_profit_30d(self.db)
        exec_q = _execution_quality(self.db)
        aum_growth_pct = _aum_growth_pct(self.db)

        # Component scores 0-100
        treasury_health = min(100.0, reserve_ratio * 2.0)
        strategy_performance = min(100.0, max(0.0, 50.0 + profit_30d / max(aum, 1) * 500.0))
        execution_quality = exec_q
        aum_growth_score = min(100.0, max(0.0, 50.0 + aum_growth_pct))

        composite = round(
            0.30 * treasury_health
            + 0.25 * strategy_performance
            + 0.20 * execution_quality
            + 0.15 * aum_growth_score
            + 0.10 * min(100.0, nav_total / 1_000_000.0 * 10.0),
            4,
        )

        nav_per_token = nav_total / LNX_SUPPLY if LNX_SUPPLY else 0.0

        snap = domain.LNXIndexSnapshot(
            nav=round(nav_per_token, 8),
            treasury_health=round(treasury_health, 4),
            strategy_performance=round(strategy_performance, 4),
            execution_quality=round(execution_quality, 4),
            aum_growth=round(aum, 2),
            composite_index=composite,
        )
        if store:
            self.db.add(snap)
            self.db.commit()
            self.db.refresh(snap)
        return snap

    def latest(self) -> domain.LNXIndexSnapshot | None:
        return (
            self.db.query(domain.LNXIndexSnapshot)
            .order_by(domain.LNXIndexSnapshot.computed_at.desc())
            .first()
        )

    def history(self, limit: int = 90) -> list:
        return (
            self.db.query(domain.LNXIndexSnapshot)
            .order_by(domain.LNXIndexSnapshot.computed_at.desc())
            .limit(limit)
            .all()
        )


def _change_pct(current: float, past: float | None) -> float | None:
    if past is None or past == 0:
        return None
    return round((current / past - 1.0) * 100.0, 4)


def run_lnx_snapshot():
    db = SessionLocal()
    try:
        engine = LNXIndexEngine(db)
        snap = engine.compute(store=True)
        logger.info("LNX snapshot: composite=%.2f nav=%.8f", snap.composite_index, snap.nav)
    except Exception as e:
        logger.error("LNX snapshot failed: %s", e, exc_info=True)
        db.rollback()
    finally:
        db.close()
