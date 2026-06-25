"""Portfolio NAV and allocation weight accounting (single source of truth)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import domain
from app.services import market_data_service


def mark_price(db: Session, trade: domain.Trade) -> float:
    if trade.exit_price and trade.status == "CLOSED":
        return float(trade.exit_price)
    if trade.entry_price:
        # Prefer stored bars — avoid blocking on external APIs during read paths
        cached = market_data_service.latest_close(db, trade.symbol)
        if cached:
            return float(cached)
        try:
            live = market_data_service.get_live_price_for_symbol(db, trade.symbol)
            if live:
                return float(live)
        except Exception:
            pass
        return float(trade.entry_price)
    return 0.0


def open_buy_exposure(db: Session, portfolio: domain.Portfolio, symbol: str | None = None) -> float:
    q = (
        db.query(domain.Trade)
        .filter(
            domain.Trade.portfolio_id == portfolio.pk_id,
            domain.Trade.status == "OPEN",
            domain.Trade.side == "BUY",
        )
    )
    if symbol:
        q = q.filter(domain.Trade.symbol == symbol)
    total = 0.0
    for t in q.all():
        qty = t.quantity or 0.0
        total += qty * mark_price(db, t)
    return total


def portfolio_nav(db: Session, portfolio: domain.Portfolio) -> float:
    """Cash (available margin) + marked open long positions."""
    cash = float(portfolio.available_margin or 0.0)
    positions = open_buy_exposure(db, portfolio)
    nav = cash + positions
    if nav <= 0 and portfolio.total_equity:
        return float(portfolio.total_equity)
    return max(nav, 0.0)


def current_weight_pct(db: Session, portfolio: domain.Portfolio, symbol: str) -> float:
    nav = portfolio_nav(db, portfolio)
    if nav <= 0:
        return 0.0
    exposure = open_buy_exposure(db, portfolio, symbol)
    return round(exposure / nav * 100.0, 4)


def allocation_summary(db: Session, portfolio: domain.Portfolio, targets: list[domain.PortfolioAllocation]) -> dict:
    """Sum of target weights, sum of current weights, cash implied."""
    nav = portfolio_nav(db, portfolio)
    current_by_symbol: dict[str, float] = {}
    for row in targets:
        sym = row.asset.symbol if row.asset else "?"
        current_by_symbol[sym] = current_weight_pct(db, portfolio, sym)

    target_sum = round(sum(r.target_weight_pct or 0 for r in targets), 4)
    current_sum = round(sum(current_by_symbol.values()), 4)
    cash_implied = round(max(0.0, 100.0 - current_sum), 4)
    return {
        "nav": round(nav, 2),
        "target_weight_sum_pct": target_sum,
        "current_weight_sum_pct": current_sum,
        "cash_weight_pct": cash_implied,
        "current_by_symbol": current_by_symbol,
    }
