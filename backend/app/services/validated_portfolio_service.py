"""Validated institutional portfolio helpers — separate from demo paper ledger."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models import domain
from app.services.validated_fund_service import get_latest_validated_fund_run

VALIDATED_SUFFIX = "-VALIDATED"

FUND_ID_BY_PORTFOLIO = {
    "LNX-PRESERVE-VALIDATED": "PRESERVE",
    "LNX-BALANCE-VALIDATED": "BALANCE",
    "LNX-ALPHA-VALIDATED": "ALPHA",
}


def is_validated_portfolio(portfolio: domain.Portfolio | str) -> bool:
    pid = portfolio if isinstance(portfolio, str) else portfolio.id
    return pid.endswith(VALIDATED_SUFFIX)


def fund_id_from_validated_portfolio(portfolio_id: str) -> str | None:
    return FUND_ID_BY_PORTFOLIO.get(portfolio_id) or (
        portfolio_id.replace("LNX-", "").replace(VALIDATED_SUFFIX, "").upper()
        if is_validated_portfolio(portfolio_id)
        else None
    )


def validated_portfolio_stats(db: Session, portfolio: domain.Portfolio) -> dict[str, Any]:
    fund_id = fund_id_from_validated_portfolio(portfolio.id)
    run = get_latest_validated_fund_run(db, fund_id) if fund_id else None
    metrics = (run.metrics or {}) if run else {}

    principal = float(portfolio.principal or run.initial_capital if run else 1_000_000)
    equity = float(portfolio.total_equity or metrics.get("final_equity") or principal)
    total_pnl = round(equity - principal, 2)

    rebalance_count = int(metrics.get("rebalance_count") or len(run.rebalance_log or []) if run else 0)
    win_rate = float(metrics.get("win_rate_pct") or 0.0)
    winning = round(rebalance_count * win_rate / 100) if rebalance_count else 0
    losing = max(0, rebalance_count - winning)

    return {
        "total_trades": rebalance_count,
        "winning_trades": winning,
        "losing_trades": losing,
        "win_rate_pct": round(win_rate, 2),
        "total_pnl": total_pnl,
        "avg_pnl_per_trade": round(total_pnl / rebalance_count, 2) if rebalance_count else 0.0,
        "best_trade_pnl": 0.0,
        "worst_trade_pnl": 0.0,
        "data_provenance": "VALIDATED_HISTORICAL",
    }


def validated_allocation_weight(row: domain.PortfolioAllocation) -> float:
    """Target weights represent validated holdings when no live open positions exist."""
    target = float(row.target_weight_pct or 0)
    current = float(row.current_weight_pct or 0)
    return current if current > 0 else target
