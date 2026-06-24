"""Build institutional validation PDF report context."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import numpy as np
from sqlalchemy.orm import Session

from app.models import domain
from app.services.chart_image_service import (
    generate_validation_chart_images,
    latency_histogram,
    pie_chart,
    pnl_histogram,
)
from app.services.validation_constants import EXECUTED_ACTIONS, PAPER_TRADE_SOURCE, REJECTED_ACTIONS
from app.services.validation_service import _paper_audit_query, _paper_trades_query, _period_start

PERIOD_LABELS = {
    "TODAY": "Daily (Today)",
    "7D": "Weekly (7-Day)",
    "14D": "14-Day Validation",
    "30D": "Monthly (30-Day)",
    "ALL": "All-Time Validation",
}

PERIOD_SPECS = {
    "TODAY": "today",
    "7D": 7,
    "14D": 14,
    "30D": 30,
    "ALL": None,
}


def _executive_assessment(snapshot: domain.ValidationSnapshot) -> str:
    if snapshot.total_trades == 0:
        return "Insufficient autonomous paper-trade history for the selected period. Continue running the validation engine to accumulate data."
    parts = []
    if snapshot.total_pnl >= 0:
        parts.append(f"Net positive P&L of ${snapshot.total_pnl:,.2f}")
    else:
        parts.append(f"Net drawdown of ${abs(snapshot.total_pnl):,.2f}")
    parts.append(f"win rate {snapshot.win_rate_pct:.1f}%")
    if snapshot.sharpe_ratio is not None:
        parts.append(f"Sharpe {snapshot.sharpe_ratio:.2f}")
    parts.append(f"max drawdown {snapshot.max_drawdown_pct:.1f}%")
    parts.append(f"fill rate {snapshot.fill_rate_pct:.1f}%")
    return ". ".join(parts) + "."


def _portfolio_performance(db: Session, closed_trades: list) -> list[dict[str, Any]]:
    pnl_by_portfolio: dict[int, dict[str, Any]] = {}
    for trade in closed_trades:
        if trade.pnl is None:
            continue
        row = pnl_by_portfolio.setdefault(
            trade.portfolio_id,
            {"trades": 0, "wins": 0, "losses": 0, "pnl": 0.0},
        )
        row["trades"] += 1
        row["pnl"] += trade.pnl
        if trade.pnl > 0:
            row["wins"] += 1
        elif trade.pnl < 0:
            row["losses"] += 1

    if not pnl_by_portfolio:
        return []

    portfolio_map = {
        pk: portfolio_id
        for pk, portfolio_id in db.query(domain.Portfolio.pk_id, domain.Portfolio.id)
        .filter(domain.Portfolio.pk_id.in_(list(pnl_by_portfolio.keys())))
        .all()
    }

    rows = []
    for pk, stats in pnl_by_portfolio.items():
        trades = stats["trades"]
        rows.append({
            "portfolio": portfolio_map.get(pk, str(pk)),
            "trades": trades,
            "wins": stats["wins"],
            "losses": stats["losses"],
            "win_rate_pct": round(stats["wins"] / trades * 100, 1) if trades else 0.0,
            "pnl": round(stats["pnl"], 2),
        })
    return sorted(rows, key=lambda r: r["pnl"], reverse=True)


def _strategy_performance(closed_trades: list) -> list[dict[str, Any]]:
    pnl_by_strategy: dict[str, dict[str, Any]] = {}
    for trade in closed_trades:
        if trade.pnl is None:
            continue
        name = trade.strategy_name or "Unassigned"
        row = pnl_by_strategy.setdefault(name, {"trades": 0, "wins": 0, "losses": 0, "pnl": 0.0})
        row["trades"] += 1
        row["pnl"] += trade.pnl
        if trade.pnl > 0:
            row["wins"] += 1
        elif trade.pnl < 0:
            row["losses"] += 1

    rows = []
    for name, stats in pnl_by_strategy.items():
        trades = stats["trades"]
        rows.append({
            "strategy": name,
            "trades": trades,
            "wins": stats["wins"],
            "losses": stats["losses"],
            "win_rate_pct": round(stats["wins"] / trades * 100, 1) if trades else 0.0,
            "pnl": round(stats["pnl"], 2),
        })
    return sorted(rows, key=lambda r: r["pnl"], reverse=True)


def _exchange_performance(closed_trades: list, exchange_meta: dict | None) -> list[dict[str, Any]]:
    pnl_by_exchange: dict[str, dict[str, Any]] = {}
    for trade in closed_trades:
        if trade.pnl is None:
            continue
        exchange = (trade.exchange or "unknown").lower()
        row = pnl_by_exchange.setdefault(exchange, {"trades": 0, "pnl": 0.0})
        row["trades"] += 1
        row["pnl"] += trade.pnl

    if exchange_meta:
        for key in ("binance", "bybit"):
            if key not in pnl_by_exchange:
                pnl_by_exchange[key] = {"trades": 0, "pnl": 0.0}

    rows = []
    for exchange, stats in sorted(pnl_by_exchange.items()):
        fill_count = 0
        if exchange_meta:
            fill_count = exchange_meta.get(exchange, 0)
        rows.append({
            "exchange": exchange.capitalize(),
            "fills": fill_count,
            "trades": stats["trades"],
            "pnl": round(stats["pnl"], 2),
            "share_pct": exchange_meta.get(f"{exchange}_pct", 0.0) if exchange_meta else 0.0,
        })
    return rows


def _top_symbols(closed_trades: list, limit: int = 10) -> list[dict[str, Any]]:
    by_symbol: dict[str, dict[str, Any]] = {}
    for trade in closed_trades:
        if trade.pnl is None:
            continue
        row = by_symbol.setdefault(trade.symbol, {"trades": 0, "pnl": 0.0, "wins": 0})
        row["trades"] += 1
        row["pnl"] += trade.pnl
        if trade.pnl > 0:
            row["wins"] += 1
    rows = [
        {
            "symbol": symbol,
            "trades": stats["trades"],
            "wins": stats["wins"],
            "pnl": round(stats["pnl"], 2),
        }
        for symbol, stats in by_symbol.items()
    ]
    return sorted(rows, key=lambda r: r["pnl"], reverse=True)[:limit]


def _top_trades(closed_trades: list, limit: int = 5) -> tuple[list[dict], list[dict]]:
    ranked = [
        {
            "symbol": t.symbol,
            "side": t.side,
            "pnl": round(t.pnl, 2),
            "strategy": t.strategy_name or "—",
            "exchange": (t.exchange or "—").capitalize(),
            "closed_at": t.closed_at.strftime("%Y-%m-%d %H:%M") if t.closed_at else "—",
        }
        for t in closed_trades
        if t.pnl is not None
    ]
    winners = sorted(ranked, key=lambda r: r["pnl"], reverse=True)[:limit]
    losers = sorted(ranked, key=lambda r: r["pnl"])[:limit]
    return winners, losers


def _trade_distribution(closed_trades: list) -> dict[str, Any]:
    buy = sum(1 for t in closed_trades if t.side == "BUY")
    sell = sum(1 for t in closed_trades if t.side == "SELL")
    wins = sum(1 for t in closed_trades if t.pnl is not None and t.pnl > 0)
    losses = sum(1 for t in closed_trades if t.pnl is not None and t.pnl < 0)
    flat = sum(1 for t in closed_trades if t.pnl is not None and t.pnl == 0)
    return {
        "buy_count": buy,
        "sell_count": sell,
        "winning_trades": wins,
        "losing_trades": losses,
        "flat_trades": flat,
        "total_closed": len(closed_trades),
    }


def _latency_analysis(db: Session, start_date: datetime | None, closed_trades: list) -> dict[str, Any]:
    audit_base = _paper_audit_query(db, start_date)
    latency_logs = audit_base.filter(
        domain.AuditLog.action_type.in_(EXECUTED_ACTIONS),
        domain.AuditLog.metadata_json.op("->>")("latency_ms").isnot(None),
    ).with_entities(domain.AuditLog.metadata_json).all()
    latencies = [
        float(log[0]["latency_ms"])
        for log in latency_logs
        if log[0] and log[0].get("latency_ms") is not None
    ]
    latencies.extend(
        float(t.execution_latency_ms)
        for t in closed_trades
        if t.execution_latency_ms is not None
    )

    if not latencies:
        return {
            "count": 0,
            "avg_ms": 0.0,
            "p50_ms": 0.0,
            "p95_ms": 0.0,
            "min_ms": 0.0,
            "max_ms": 0.0,
            "histogram": None,
        }

    arr = np.array(latencies)
    return {
        "count": len(latencies),
        "avg_ms": round(float(arr.mean()), 1),
        "p50_ms": round(float(np.percentile(arr, 50)), 1),
        "p95_ms": round(float(np.percentile(arr, 95)), 1),
        "min_ms": round(float(arr.min()), 1),
        "max_ms": round(float(arr.max()), 1),
        "histogram": latency_histogram(latencies),
    }


def _risk_events(db: Session, start_date: datetime | None, limit: int = 15) -> list[dict[str, Any]]:
    query = db.query(domain.RiskEvent).order_by(domain.RiskEvent.triggered_at.desc())
    if start_date:
        query = query.filter(domain.RiskEvent.triggered_at >= start_date)
    events = query.limit(limit).all()
    if not events:
        return []

    portfolio_map = {
        pk: portfolio_id
        for pk, portfolio_id in db.query(domain.Portfolio.pk_id, domain.Portfolio.id)
        .filter(domain.Portfolio.pk_id.in_({e.portfolio_id for e in events}))
        .all()
    }

    return [
        {
            "portfolio": portfolio_map.get(event.portfolio_id, str(event.portfolio_id)),
            "event_type": event.event_type,
            "severity": event.severity,
            "description": (event.description or "")[:120],
            "resolved": event.resolved,
            "triggered_at": event.triggered_at.strftime("%Y-%m-%d %H:%M"),
        }
        for event in events
    ]


def _system_health_summary(db: Session, start_date: datetime | None, snapshot: domain.ValidationSnapshot) -> dict[str, Any]:
    audit_base = _paper_audit_query(db, start_date)
    filled = audit_base.filter(domain.AuditLog.action_type.in_(EXECUTED_ACTIONS)).count()
    rejected = audit_base.filter(domain.AuditLog.action_type.in_(REJECTED_ACTIONS)).count()
    risk_rejections = audit_base.filter(domain.AuditLog.action_type == "RISK_REJECTION").count()
    order_rejected = audit_base.filter(domain.AuditLog.action_type == "ORDER_REJECTED").count()

    risk_logs = audit_base.filter(domain.AuditLog.action_type.in_(REJECTED_ACTIONS)).all()
    ai_rejections = sum(
        1 for log in risk_logs
        if "sentiment" in (log.description or "").lower() or "bearish" in (log.description or "").lower()
    )
    leverage_rejections = sum(1 for log in risk_logs if "leverage" in (log.description or "").lower())
    kill_switch_rejections = sum(1 for log in risk_logs if "kill switch" in (log.description or "").lower())

    exchange = snapshot.exchange_distribution or {}

    return {
        "total_orders": snapshot.total_orders,
        "filled_orders": filled,
        "rejected_orders": rejected,
        "fill_rate_pct": snapshot.fill_rate_pct,
        "risk_rejections": risk_rejections,
        "order_rejections": order_rejected,
        "ai_rejections": ai_rejections,
        "leverage_rejections": leverage_rejections,
        "kill_switch_rejections": kill_switch_rejections,
        "avg_latency_ms": snapshot.avg_latency_ms,
        "binance_fills": exchange.get("binance", 0),
        "bybit_fills": exchange.get("bybit", 0),
    }


def _snapshot_dict(snapshot: domain.ValidationSnapshot) -> dict[str, Any]:
    return { # type: ignore
        "total_pnl": snapshot.total_pnl,
        "win_rate_pct": snapshot.win_rate_pct,
        "profit_factor": snapshot.profit_factor,
        "sharpe_ratio": snapshot.sharpe_ratio,
        "max_drawdown_pct": snapshot.max_drawdown_pct,
        "avg_return_pct": snapshot.avg_return_pct,
        "total_trades": snapshot.total_trades,
        "winning_trades": snapshot.winning_trades,
        "losing_trades": snapshot.losing_trades,
        "largest_win": snapshot.largest_win,
        "largest_loss": snapshot.largest_loss,
        "avg_latency_ms": snapshot.avg_latency_ms,
        "fill_rate_pct": snapshot.fill_rate_pct,
        "updated_at": snapshot.updated_at.strftime("%Y-%m-%d %H:%M UTC") if snapshot.updated_at else "—",
        "best_portfolio": snapshot.best_portfolio,
        "worst_portfolio": snapshot.worst_portfolio,
        "best_strategy": snapshot.best_strategy,
        "worst_strategy": snapshot.worst_strategy,
    }


def build_legacy_context(db: Session) -> dict[str, Any]:
    """Fallback when no snapshot exists — uses 3-day legacy summary."""
    now = datetime.utcnow()
    daily_stats = []
    for i in range(3):
        day_start = (now - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        filled = db.query(domain.AuditLog).filter(
            domain.AuditLog.action_type.in_(EXECUTED_ACTIONS),
            domain.AuditLog.timestamp.between(day_start, day_end),
            domain.AuditLog.metadata_json.op("->>")("exchange").in_(["binance", "bybit"]),
        ).count()
        rejected = db.query(domain.AuditLog).filter(
            domain.AuditLog.action_type.in_(REJECTED_ACTIONS),
            domain.AuditLog.timestamp.between(day_start, day_end),
            domain.AuditLog.metadata_json.op("->>")("exchange").in_(["binance", "bybit"]),
        ).count()
        total = filled + rejected
        daily_stats.append({
            "day": f"Day {i + 1}",
            "trades_executed": filled,
            "success_rate": round(filled / total * 100, 2) if total else 100.0,
            "risk_rejections": rejected,
        })

    return {
        "report_date": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "period": "3-Day (Legacy Fallback)",
        "period_code": "LEGACY",
        "legacy": True,
        "daily_stats": daily_stats,
        "summary": None,
        "snapshot": None,
        "executive": {
            "assessment": "Snapshot data unavailable. Showing legacy 3-day execution summary. Refresh validation snapshots after autonomous paper trading begins.",
        },
        "charts": {},
        "portfolio_performance": [],
        "strategy_performance": [],
        "exchange_performance": [],
        "top_symbols": [],
        "top_winners": [],
        "top_losers": [],
        "trade_distribution": {},
        "latency": {"count": 0, "histogram": None},
        "risk_events": [],
        "system_health": {},
    }


def build_validation_report_context(db: Session, period: str = "30D") -> dict[str, Any]:
    period = period.upper()
    period_spec = PERIOD_SPECS.get(period, 30)
    period_label = PERIOD_LABELS.get(period, f"{period} Validation")

    snapshot = db.query(domain.ValidationSnapshot).filter(
        domain.ValidationSnapshot.snapshot_key == f"GLOBAL_{period}"
    ).first()

    if not snapshot:
        return build_legacy_context(db)

    start_date = _period_start(period_spec)
    closed_trades = _paper_trades_query(db, start_date, closed_only=True).all()
    chart_data = snapshot.chart_data or {}
    exchange_meta = snapshot.exchange_distribution or {}

    trade_pnls = [float(t.pnl) for t in closed_trades if t.pnl is not None]
    charts = generate_validation_chart_images(chart_data)
    charts["win_loss_distribution"] = pnl_histogram(trade_pnls)
    charts["exchange_pie"] = pie_chart(
        ["Binance", "Bybit"],
        [float(exchange_meta.get("binance", 0)), float(exchange_meta.get("bybit", 0))],
        "Fill Distribution by Exchange",
    )

    top_winners, top_losers = _top_trades(closed_trades)

    return {
        "report_date": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "period": period_label,
        "period_code": period,
        "legacy": False,
        "summary": None,
        "snapshot": _snapshot_dict(snapshot),
        "executive": {
            "headline_pnl": snapshot.total_pnl,
            "win_rate": snapshot.win_rate_pct,
            "sharpe": snapshot.sharpe_ratio,
            "max_drawdown": snapshot.max_drawdown_pct,
            "total_trades": snapshot.total_trades,
            "fill_rate": snapshot.fill_rate_pct,
            "profit_factor": snapshot.profit_factor,
            "assessment": _executive_assessment(snapshot),
        },
        "portfolio_performance": _portfolio_performance(db, closed_trades),
        "strategy_performance": _strategy_performance(closed_trades),
        "exchange_performance": _exchange_performance(closed_trades, exchange_meta),
        "top_symbols": _top_symbols(closed_trades),
        "top_winners": top_winners,
        "top_losers": top_losers,
        "trade_distribution": _trade_distribution(closed_trades),
        "latency": _latency_analysis(db, start_date, closed_trades),
        "risk_events": _risk_events(db, start_date),
        "system_health": _system_health_summary(db, start_date, snapshot),
        "charts": charts,
        "daily_stats": [],
    }


def validation_pdf_filename(period: str) -> str:
    period = period.upper()
    names = {
        "7D": "nexa_weekly_validation_report.pdf",
        "14D": "nexa_14_day_validation_report.pdf",
        "30D": "nexa_30_day_validation_report.pdf",
        "ALL": "nexa_all_time_validation_report.pdf",
        "TODAY": "nexa_daily_validation_report.pdf",
        "LEGACY": "nexa_legacy_validation_report.pdf",
    }
    return names.get(period, f"nexa_{period.lower()}_validation_report.pdf")
