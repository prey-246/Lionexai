"""Aggregate realized returns across auto-managed portfolios per fund."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session, joinedload

from app.models import domain


def format_target_return_label(
    weekly_pct: float | None,
    monthly_pct: float | None = None,
) -> str | None:
    if weekly_pct is None:
        return None
    monthly = monthly_pct if monthly_pct is not None else round(weekly_pct * 4.33, 2)
    return f"{weekly_pct:g}% weekly · {monthly:g}% monthly"


def _period_return_pct(curves: list[domain.EquityCurve], days: int) -> float | None:
    if len(curves) < 2:
        return None
    last = curves[-1]
    if not last.equity or last.equity <= 0:
        return None
    cutoff = last.timestamp - timedelta(days=days)
    baseline = curves[0]
    for point in curves:
        if point.timestamp <= cutoff:
            baseline = point
        else:
            break
    if not baseline.equity or baseline.equity <= 0:
        return None
    return round(((last.equity - baseline.equity) / baseline.equity) * 100.0, 2)


def _portfolio_actuals(db: Session, portfolio: domain.Portfolio) -> dict[str, float | None]:
    curves = (
        db.query(domain.EquityCurve)
        .filter(domain.EquityCurve.portfolio_id == portfolio.pk_id)
        .order_by(domain.EquityCurve.timestamp.asc())
        .all()
    )
    principal = portfolio.principal or portfolio.total_equity or 0.0
    equity = portfolio.total_equity or 0.0
    total = None
    if principal > 0:
        total = round(((equity - principal) / principal) * 100.0, 2)
    return {
        "total_return_pct": total,
        "weekly_return_pct": _period_return_pct(curves, 7),
        "monthly_return_pct": _period_return_pct(curves, 30),
        "weight": equity if equity > 0 else 0.0,
    }


def _weighted_avg(values: list[tuple[float, float | None]]) -> float | None:
    pairs = [(w, v) for w, v in values if v is not None and w > 0]
    if not pairs:
        return None
    total_w = sum(w for w, _ in pairs)
    if total_w <= 0:
        return None
    return round(sum(w * v for w, v in pairs) / total_w, 2)


def compute_fund_actuals(db: Session, fund: domain.Fund) -> dict[str, Any]:
    portfolios = (
        db.query(domain.Portfolio)
        .filter(domain.Portfolio.fund_pk_id == fund.pk_id, domain.Portfolio.auto_managed == True)
        .all()
    )
    if not portfolios:
        return {
            "portfolio_count": 0,
            "total_aum": 0.0,
            "client_count": 0,
            "actual_total_return_pct": None,
            "actual_weekly_return_pct": None,
            "actual_monthly_return_pct": None,
            "data_provenance": "UNKNOWN",
        }

    total_aum = sum(p.total_equity or 0.0 for p in portfolios)
    total_principal = sum(p.principal or p.total_equity or 0.0 for p in portfolios)

    weekly_pairs: list[tuple[float, float | None]] = []
    monthly_pairs: list[tuple[float, float | None]] = []
    for portfolio in portfolios:
        metrics = _portfolio_actuals(db, portfolio)
        weekly_pairs.append((metrics["weight"], metrics["weekly_return_pct"]))
        monthly_pairs.append((metrics["weight"], metrics["monthly_return_pct"]))

    actual_total = None
    if total_principal > 0:
        actual_total = round(((total_aum - total_principal) / total_principal) * 100.0, 2)

    return {
        "portfolio_count": len(portfolios),
        "total_aum": round(total_aum, 2),
        "client_count": len({p.user_id for p in portfolios}),
        "actual_total_return_pct": actual_total,
        "actual_weekly_return_pct": _weighted_avg(weekly_pairs),
        "actual_monthly_return_pct": _weighted_avg(monthly_pairs),
        "data_provenance": detect_fund_provenance(db, portfolios),
    }


def detect_fund_provenance(db: Session, portfolios: list[domain.Portfolio]) -> str:
    """DEMO | PAPER_LIVE | MIXED — never label demo as validated."""
    if not portfolios:
        return "UNKNOWN"
    pks = [p.pk_id for p in portfolios]
    trades = db.query(domain.Trade).filter(domain.Trade.portfolio_id.in_(pks)).limit(500).all()
    if not trades:
        return "UNKNOWN"
    simulated = sum(1 for t in trades if (t.exchange or "").lower() == "simulated")
    ratio = simulated / len(trades)
    if ratio >= 0.95:
        return "DEMO"
    if ratio <= 0.05:
        return "PAPER_LIVE"
    return "MIXED"


def compute_institutional_analytics(db: Session, fund: domain.Fund) -> dict[str, Any]:
    """Rich fund dashboard — validated historical metrics primary; demo ledger optional."""
    from app.services.validated_fund_service import validated_fund_metrics, compute_fund_display_metrics

    display = compute_fund_display_metrics(db, fund, include_demo=False)
    validated = validated_fund_metrics(db, fund.id)

    portfolios = (
        db.query(domain.Portfolio)
        .filter(domain.Portfolio.fund_pk_id == fund.pk_id, domain.Portfolio.auto_managed == True)
        .all()
    )

    asset_weights: dict[str, float] = {}
    for p in portfolios:
        rows = (
            db.query(domain.PortfolioAllocation)
            .options(joinedload(domain.PortfolioAllocation.asset))
            .filter(domain.PortfolioAllocation.portfolio_id == p.pk_id)
            .all()
        )
        for r in rows:
            sym = r.asset.symbol if r.asset else "?"
            asset_weights[sym] = asset_weights.get(sym, 0) + (r.target_weight_pct or 0)
    if portfolios:
        asset_weights = {k: round(v / len(portfolios), 2) for k, v in asset_weights.items()}

    if validated:
        return {
            "fund_id": fund.id,
            "fund_name": fund.name,
            "portfolio_count": display["portfolio_count"],
            "client_count": display["client_count"],
            "total_aum": display["total_aum"],
            "target_weekly_return_pct": fund.target_weekly_return_pct,
            "target_monthly_return_pct": fund.target_monthly_return_pct,
            "data_provenance": "VALIDATED_HISTORICAL",
            "realized_total_return_pct": validated.get("total_return_pct"),
            "realized_weekly_return_pct": validated.get("avg_weekly_return_pct"),
            "realized_monthly_return_pct": validated.get("avg_monthly_return_pct"),
            "actual_total_return_pct": validated.get("total_return_pct"),
            "actual_weekly_return_pct": validated.get("avg_weekly_return_pct"),
            "actual_monthly_return_pct": validated.get("avg_monthly_return_pct"),
            "validated_monthly_return_pct": validated.get("avg_monthly_return_pct"),
            "cagr_pct": validated.get("cagr_pct"),
            "annualized_return_pct": validated.get("annualized_return_pct"),
            "sharpe_ratio": validated.get("sharpe_ratio"),
            "sortino_ratio": validated.get("sortino_ratio"),
            "max_drawdown_pct": validated.get("max_drawdown_pct"),
            "calmar_ratio": validated.get("calmar_ratio"),
            "volatility_pct": validated.get("volatility_pct"),
            "win_rate_pct": validated.get("win_rate_pct"),
            "profit_factor": validated.get("profit_factor"),
            "yield_delivery_pct": validated.get("yield_delivery_pct"),
            "treasury_contributions": None,
            "validated_historical": {
                "run_id": validated.get("run_id"),
                "period_start": validated.get("period_start"),
                "period_end": validated.get("period_end"),
                "simulation_days": validated.get("simulation_days"),
                "symbols_used": validated.get("symbols_used"),
                "provenance": "VALIDATED_HISTORICAL",
            },
            "performance_curve": validated.get("equity_curve") or [],
            "asset_allocation": asset_weights,
            "top_holdings": sorted(asset_weights.keys(), key=lambda x: asset_weights[x], reverse=True)[:5],
            "target_vs_realized_vs_validated": {
                "target_monthly_pct": fund.target_monthly_return_pct,
                "target_weekly_pct": fund.target_weekly_return_pct,
                "realized_monthly_pct": validated.get("avg_monthly_return_pct"),
                "validated_monthly_pct": validated.get("avg_monthly_return_pct"),
            },
            "data_coverage": validated.get("data_coverage"),
            "risk_score": None,
        }

    return {
        "fund_id": fund.id,
        "fund_name": fund.name,
        "portfolio_count": display["portfolio_count"],
        "client_count": display["client_count"],
        "total_aum": display["total_aum"],
        "target_weekly_return_pct": fund.target_weekly_return_pct,
        "target_monthly_return_pct": fund.target_monthly_return_pct,
        "data_provenance": "UNVALIDATED",
        "message": display.get("message"),
        "asset_allocation": asset_weights,
        "top_holdings": sorted(asset_weights.keys(), key=lambda x: asset_weights[x], reverse=True)[:5],
        "validated_historical": None,
        "performance_curve": [],
    }
