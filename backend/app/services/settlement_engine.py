"""Weekly settlement engine for auto-managed fund portfolios.

Implements the guaranteed-target, solvency-capped model:
- Client NAV grows by the fund's fixed weekly target when treasury pools can cover shortfalls.
- Profit above target is routed to treasury pools (split across YIELD/GROWTH/RESERVE/OPERATIONS/LNX_INDEX).
- If pools are exhausted, settlement falls back to pass-through (uncovered shortfall logged).
"""
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any

from sqlalchemy.orm import Session, joinedload

from app.core.database import SessionLocal
from app.models import domain
from app.services import market_data_service
from app.services.settlement_constants import (
    DEFAULT_FUND_WEEKLY_TARGETS,
    PROFIT_ROUTING_SPLIT,
    TOPUP_POOL_ORDER,
)
from app.services.audit_service import create_audit_log

logger = logging.getLogger("nexa.settlement_engine")


def _iso_week_key(dt: datetime) -> str:
    iso = dt.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def _week_bounds(ref: datetime | None = None) -> Tuple[datetime, datetime, str]:
    """Return (period_start, period_end, iso_week_key) for the week containing ref."""
    ref = ref or datetime.utcnow()
    # Monday 00:00 UTC of current ISO week
    start = ref.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=ref.weekday())
    end = start + timedelta(days=7)
    return start, end, _iso_week_key(start)


def _marked_equity(db: Session, portfolio: domain.Portfolio) -> float:
    """Portfolio equity marked to latest prices for open positions."""
    cash = portfolio.total_equity or 0.0
    open_trades = [t for t in portfolio.trades if t.status == "OPEN"]
    if not open_trades:
        return cash

    # total_equity already reflects cash after buys; add unrealized on open positions
    unrealized = 0.0
    for t in open_trades:
        price = market_data_service.latest_close(db, t.symbol)
        if not price and t.asset_pk_id:
            asset = db.query(domain.Asset).filter(domain.Asset.pk_id == t.asset_pk_id).first()
            if asset:
                price = market_data_service.get_live_price(asset)
        if not price:
            price = t.entry_price or 0.0
        if t.side == "BUY":
            unrealized += (price - (t.entry_price or 0)) * (t.quantity or 0)
        else:
            unrealized += ((t.entry_price or 0) - price) * (t.quantity or 0)
    return cash + unrealized


def _get_pool(db: Session, pool_id: str) -> Optional[domain.TreasuryPool]:
    return db.query(domain.TreasuryPool).filter(domain.TreasuryPool.id == pool_id).first()


def _route_excess(db: Session, amount: float, portfolio_id: str, settlement_pk: int) -> Dict[str, float]:
    """Credit treasury pools with excess profit; returns {pool_id: amount}."""
    if amount <= 0:
        return {}
    routed: Dict[str, float] = {}
    for pool_id, pct in PROFIT_ROUTING_SPLIT.items():
        share = round(amount * (pct / 100.0), 2)
        if share <= 0:
            continue
        pool = _get_pool(db, pool_id)
        if not pool:
            logger.warning("Treasury pool %s missing; skipping routing share $%.2f", pool_id, share)
            continue
        pool.balance += share
        db.add(domain.TreasuryTransaction(
            pool_pk_id=pool.pk_id,
            amount=share,
            transaction_type="PROFIT_ROUTING",
            reference_id=portfolio_id,
            settlement_pk_id=settlement_pk,
            description=f"Excess profit routed from portfolio {portfolio_id} ({pct}%).",
        ))
        routed[pool_id] = share
    return routed


def _topup_shortfall(db: Session, amount: float, portfolio_id: str, settlement_pk: int) -> Tuple[float, Dict[str, float]]:
    """Debit treasury pools to cover client shortfall; returns (total_topup, {pool_id: amount})."""
    if amount <= 0:
        return 0.0, {}
    remaining = amount
    debited: Dict[str, float] = {}
    for pool_id in TOPUP_POOL_ORDER:
        if remaining <= 0.01:
            break
        pool = _get_pool(db, pool_id)
        if not pool or pool.balance <= 0:
            continue
        draw = min(pool.balance, remaining)
        pool.balance -= draw
        db.add(domain.TreasuryTransaction(
            pool_pk_id=pool.pk_id,
            amount=-draw,
            transaction_type="CLIENT_TOPUP",
            reference_id=portfolio_id,
            settlement_pk_id=settlement_pk,
            description=f"Client yield top-up from {pool_id} for portfolio {portfolio_id}.",
        ))
        debited[pool_id] = draw
        remaining -= draw
    return amount - remaining, debited


class SettlementEngine:
    def __init__(self, db: Session):
        self.db = db

    def _target_weekly_pct(self, portfolio: domain.Portfolio) -> float:
        if portfolio.fund and portfolio.fund.target_weekly_return_pct is not None:
            return float(portfolio.fund.target_weekly_return_pct)
        fund_id = portfolio.fund.id if portfolio.fund else (portfolio.mandate_id or "BALANCE")
        return DEFAULT_FUND_WEEKLY_TARGETS.get(fund_id, 1.0)

    def settle_portfolio(self, portfolio: domain.Portfolio, period_start: datetime | None = None,
                         period_end: datetime | None = None, force: bool = False) -> Optional[domain.ClientSettlement]:
        if not portfolio.auto_managed:
            return None

        p_start, p_end, week_key = _week_bounds(period_end or datetime.utcnow())
        if period_start:
            p_start = period_start
        if period_end:
            p_end = period_end

        existing = self.db.query(domain.ClientSettlement).filter(
            domain.ClientSettlement.portfolio_id == portfolio.pk_id,
            domain.ClientSettlement.iso_week_key == week_key,
        ).first()
        if existing and not force:
            return existing

        # Opening equity: last settlement closing or principal/total_equity at period start
        if portfolio.last_settled_at:
            prev = (
                self.db.query(domain.ClientSettlement)
                .filter(domain.ClientSettlement.portfolio_id == portfolio.pk_id)
                .order_by(domain.ClientSettlement.created_at.desc())
                .first()
            )
            opening = prev.closing_marked_equity if prev else (portfolio.principal or portfolio.total_equity)
        else:
            opening = portfolio.principal or portfolio.total_equity or 0.0

        marked = _marked_equity(self.db, portfolio)
        period_pnl = marked - opening
        target_pct = self._target_weekly_pct(portfolio)
        target_gain = opening * (target_pct / 100.0)
        client_entitlement = target_gain

        excess_routed = 0.0
        shortfall_topup = 0.0
        uncovered = 0.0
        status = "SETTLED"
        pool_breakdown: Dict[str, Any] = {}

        if period_pnl > target_gain + 0.01:
            excess = period_pnl - target_gain
            # Create settlement row first to get pk_id for FK
            settlement = domain.ClientSettlement(
                id=f"stl_{uuid.uuid4().hex[:12]}",
                portfolio_id=portfolio.pk_id,
                period_start=p_start,
                period_end=p_end,
                iso_week_key=week_key,
                opening_equity=round(opening, 2),
                closing_marked_equity=round(marked, 2),
                period_pnl=round(period_pnl, 2),
                target_return_pct=target_pct,
                client_entitlement=round(client_entitlement, 2),
                excess_routed=0.0,
                shortfall_topup=0.0,
                uncovered=0.0,
                status="PENDING",
            )
            self.db.add(settlement)
            self.db.flush()

            routed = _route_excess(self.db, excess, portfolio.id, settlement.pk_id)
            excess_routed = sum(routed.values())
            pool_breakdown["routed"] = routed
            new_equity = opening + target_gain
            settlement.excess_routed = round(excess_routed, 2)
            settlement.status = "SETTLED"
            settlement.breakdown = pool_breakdown

        elif period_pnl < target_gain - 0.01:
            shortfall = target_gain - period_pnl
            settlement = domain.ClientSettlement(
                id=f"stl_{uuid.uuid4().hex[:12]}",
                portfolio_id=portfolio.pk_id,
                period_start=p_start,
                period_end=p_end,
                iso_week_key=week_key,
                opening_equity=round(opening, 2),
                closing_marked_equity=round(marked, 2),
                period_pnl=round(period_pnl, 2),
                target_return_pct=target_pct,
                client_entitlement=round(client_entitlement, 2),
                status="PENDING",
            )
            self.db.add(settlement)
            self.db.flush()

            topup, debited = _topup_shortfall(self.db, shortfall, portfolio.id, settlement.pk_id)
            shortfall_topup = topup
            uncovered = max(0.0, shortfall - topup)
            pool_breakdown["topup"] = debited
            if uncovered > 0.01:
                status = "PARTIAL" if topup > 0 else "PASSTHROUGH"
                new_equity = opening + period_pnl + topup
            else:
                status = "SETTLED"
                new_equity = opening + target_gain
            settlement.shortfall_topup = round(shortfall_topup, 2)
            settlement.uncovered = round(uncovered, 2)
            settlement.status = status
            settlement.breakdown = pool_breakdown

        else:
            new_equity = opening + target_gain
            settlement = domain.ClientSettlement(
                id=f"stl_{uuid.uuid4().hex[:12]}",
                portfolio_id=portfolio.pk_id,
                period_start=p_start,
                period_end=p_end,
                iso_week_key=week_key,
                opening_equity=round(opening, 2),
                closing_marked_equity=round(marked, 2),
                period_pnl=round(period_pnl, 2),
                target_return_pct=target_pct,
                client_entitlement=round(client_entitlement, 2),
                excess_routed=0.0,
                shortfall_topup=0.0,
                uncovered=0.0,
                status="SETTLED",
                breakdown={},
            )
            self.db.add(settlement)

        portfolio.total_equity = round(new_equity, 2)
        portfolio.last_settled_at = datetime.utcnow()
        self.db.add(domain.EquityCurve(portfolio_id=portfolio.pk_id, equity=portfolio.total_equity))

        create_audit_log(
            self.db,
            action_type="CLIENT_SETTLEMENT",
            description=f"Weekly settlement for {portfolio.id}: target {target_pct}%, status {status}.",
            metadata_json={
                "portfolio_id": portfolio.id,
                "week": week_key,
                "period_pnl": round(period_pnl, 2),
                "excess_routed": round(excess_routed, 2),
                "shortfall_topup": round(shortfall_topup, 2),
                "uncovered": round(uncovered, 2),
                "new_equity": round(new_equity, 2),
            },
        )
        self.db.commit()
        self.db.refresh(settlement)
        logger.info(
            "Settled %s (%s): pnl=%.2f target=%.2f excess=%.2f topup=%.2f status=%s",
            portfolio.id, week_key, period_pnl, target_gain, excess_routed, shortfall_topup, status,
        )
        return settlement

    def run_weekly_settlement(self, force: bool = False) -> int:
        portfolios = (
            self.db.query(domain.Portfolio)
            .filter(domain.Portfolio.auto_managed == True)
            .options(joinedload(domain.Portfolio.fund))
            .all()
        )
        count = 0
        for p in portfolios:
            try:
                if self.settle_portfolio(p, force=force):
                    count += 1
            except Exception as e:
                logger.error("Settlement failed for %s: %s", p.id, e, exc_info=True)
                self.db.rollback()
        return count


def run_weekly_settlement(force: bool = False):
    """Scheduled job entrypoint."""
    db = SessionLocal()
    try:
        engine = SettlementEngine(db)
        n = engine.run_weekly_settlement(force=force)
        logger.info("Weekly settlement complete: %d portfolios.", n)
        # Recompute LNX after settlement (if engine exists)
        try:
            from app.engines.lnx_index import run_lnx_snapshot
            run_lnx_snapshot()
        except ImportError:
            pass
    except Exception as e:
        logger.error("Weekly settlement job failed: %s", e, exc_info=True)
        db.rollback()
    finally:
        db.close()
