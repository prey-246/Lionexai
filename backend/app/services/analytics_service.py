"""Platform analytics: strategy performance, portfolio/strategy comparison."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import domain
from app.services.validation_constants import PAPER_TRADE_SOURCE


def _closed_trades_query(db: Session, trade_source: str | None = None):
    query = db.query(domain.Trade).filter(domain.Trade.status == "CLOSED", domain.Trade.pnl.isnot(None))
    if trade_source:
        query = query.filter(domain.Trade.trade_source == trade_source)
    return query


def get_strategy_analytics(db: Session, trade_source: str | None = PAPER_TRADE_SOURCE) -> list[dict[str, Any]]:
    rows = (
        db.query(
            domain.Trade.strategy_name,
            func.count(domain.Trade.id),
            func.sum(domain.Trade.pnl),
            func.avg(domain.Trade.pnl),
        )
        .filter(
            domain.Trade.status == "CLOSED",
            domain.Trade.pnl.isnot(None),
            domain.Trade.strategy_name.isnot(None),
            domain.Trade.strategy_name != "",
        )
    )
    if trade_source:
        rows = rows.filter(domain.Trade.trade_source == trade_source)

    results = []
    for name, total, total_pnl, avg_pnl in rows.group_by(domain.Trade.strategy_name).all():
        wins = (
            db.query(func.count(domain.Trade.id))
            .filter(
                domain.Trade.strategy_name == name,
                domain.Trade.status == "CLOSED",
                domain.Trade.pnl > 0,
                *([domain.Trade.trade_source == trade_source] if trade_source else []),
            )
            .scalar()
            or 0
        )
        total = int(total or 0)
        results.append({
            "strategy_name": name,
            "total_trades": total,
            "winning_trades": wins,
            "losing_trades": total - wins,
            "win_rate_pct": round(wins / total * 100, 2) if total else 0.0,
            "total_pnl": round(float(total_pnl or 0), 2),
            "avg_pnl": round(float(avg_pnl or 0), 2),
        })
    return sorted(results, key=lambda r: r["total_pnl"], reverse=True)


def _portfolio_stats(db: Session, portfolio: domain.Portfolio) -> dict[str, Any]:
    trades = db.query(domain.Trade).filter(
        domain.Trade.portfolio_id == portfolio.pk_id,
        domain.Trade.status == "CLOSED",
        domain.Trade.pnl.isnot(None),
    ).all()
    total = len(trades)
    wins = sum(1 for t in trades if t.pnl and t.pnl > 0)
    total_pnl = sum(t.pnl for t in trades if t.pnl is not None)
    return {
        "portfolio_id": portfolio.id,
        "total_equity": round(portfolio.total_equity, 2),
        "total_trades": total,
        "winning_trades": wins,
        "losing_trades": total - wins,
        "win_rate_pct": round(wins / total * 100, 2) if total else 0.0,
        "total_pnl": round(total_pnl, 2),
        "current_drawdown_pct": round(portfolio.current_drawdown_pct, 2),
    }


def compare_portfolios(db: Session, portfolio_ids: list[str]) -> list[dict[str, Any]]:
    results = []
    for portfolio_id in portfolio_ids:
        portfolio = db.query(domain.Portfolio).filter(domain.Portfolio.id == portfolio_id).first()
        if not portfolio:
            continue
        stats = _portfolio_stats(db, portfolio)
        curves = (
            db.query(domain.EquityCurve)
            .filter(domain.EquityCurve.portfolio_id == portfolio.pk_id)
            .order_by(domain.EquityCurve.timestamp.asc())
            .limit(60)
            .all()
        )
        stats["equity_curve"] = [
            {"timestamp": c.timestamp.isoformat(), "equity": float(c.equity or 0)}
            for c in curves
        ]
        results.append(stats)
    return results


def compare_strategies(db: Session, strategy_names: list[str], trade_source: str | None = PAPER_TRADE_SOURCE) -> list[dict[str, Any]]:
    all_analytics = {a["strategy_name"]: a for a in get_strategy_analytics(db, trade_source)}
    results = []
    for name in strategy_names:
        if name in all_analytics:
            results.append(all_analytics[name])
        else:
            results.append({
                "strategy_name": name,
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate_pct": 0.0,
                "total_pnl": 0.0,
                "avg_pnl": 0.0,
            })
    return results


def search_trades(
    db: Session,
    *,
    portfolio_id: str | None = None,
    symbol: str | None = None,
    strategy_name: str | None = None,
    exchange: str | None = None,
    trade_source: str | None = None,
    status: str | None = None,
    side: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    search: str | None = None,
    skip: int = 0,
    limit: int = 50,
    user_id: str | None = None,
    is_privileged: bool = False,
) -> tuple[list[dict[str, Any]], int]:
    query = db.query(domain.Trade, domain.Portfolio.id).join(
        domain.Portfolio, domain.Portfolio.pk_id == domain.Trade.portfolio_id
    )

    if not is_privileged and user_id:
        query = query.filter(domain.Portfolio.user_id == user_id)
    if portfolio_id:
        query = query.filter(domain.Portfolio.id == portfolio_id)
    if symbol:
        query = query.filter(domain.Trade.symbol.ilike(f"%{symbol}%"))
    if strategy_name:
        query = query.filter(domain.Trade.strategy_name.ilike(f"%{strategy_name}%"))
    if exchange:
        query = query.filter(domain.Trade.exchange == exchange.lower())
    if trade_source:
        query = query.filter(domain.Trade.trade_source == trade_source.upper())
    if status:
        query = query.filter(domain.Trade.status == status.upper())
    if side:
        query = query.filter(domain.Trade.side == side.upper())
    if start_date:
        query = query.filter(domain.Trade.created_at >= start_date)
    if end_date:
        query = query.filter(domain.Trade.created_at <= end_date)
    if search:
        like = f"%{search}%"
        query = query.filter(
            (domain.Trade.symbol.ilike(like))
            | (domain.Trade.strategy_name.ilike(like))
            | (domain.Trade.id.ilike(like))
            | (domain.Portfolio.id.ilike(like))
        )

    total = query.count()
    rows = query.order_by(domain.Trade.created_at.desc()).offset(skip).limit(limit).all()

    trades = []
    for trade, pid in rows:
        trades.append({
            "id": trade.id,
            "portfolio_id": pid,
            "symbol": trade.symbol,
            "side": trade.side,
            "quantity": trade.quantity,
            "entry_price": trade.entry_price,
            "exit_price": trade.exit_price,
            "status": trade.status,
            "pnl": trade.pnl,
            "exchange": trade.exchange,
            "execution_latency_ms": trade.execution_latency_ms,
            "strategy_name": trade.strategy_name,
            "rejection_reason": trade.rejection_reason,
            "trade_source": trade.trade_source,
            "created_at": trade.created_at,
            "closed_at": trade.closed_at,
        })
    return trades, total
