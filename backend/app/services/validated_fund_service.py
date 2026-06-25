"""Serve validated historical fund metrics — demo ledger excluded from display metrics."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models import domain


def get_latest_validated_fund_run(db: Session, fund_id: str) -> domain.ValidatedFundRun | None:
    """Prefer SELECTED_BEST promoted run, then highest rank_score, then latest."""
    selected = (
        db.query(domain.ValidatedFundRun)
        .filter(
            domain.ValidatedFundRun.fund_id == fund_id.upper(),
            domain.ValidatedFundRun.validation_type == "SELECTED_BEST",
            domain.ValidatedFundRun.provenance == "VALIDATED_HISTORICAL",
        )
        .order_by(domain.ValidatedFundRun.created_at.desc())
        .first()
    )
    if selected and selected.metrics and not selected.metrics.get("error"):
        return selected

    ranked = (
        db.query(domain.ValidatedFundRun)
        .filter(
            domain.ValidatedFundRun.fund_id == fund_id.upper(),
            domain.ValidatedFundRun.provenance == "VALIDATED_HISTORICAL",
        )
        .order_by(domain.ValidatedFundRun.rank_score.desc().nullslast(), domain.ValidatedFundRun.created_at.desc())
        .first()
    )
    if ranked and ranked.metrics and not ranked.metrics.get("error"):
        return ranked

    return (
        db.query(domain.ValidatedFundRun)
        .filter(
            domain.ValidatedFundRun.fund_id == fund_id.upper(),
            domain.ValidatedFundRun.provenance == "VALIDATED_HISTORICAL",
        )
        .order_by(domain.ValidatedFundRun.created_at.desc())
        .first()
    )


def validated_fund_metrics(db: Session, fund_id: str) -> dict[str, Any] | None:
    """Latest institutional metrics from historical backtest, or None if not run yet."""
    row = get_latest_validated_fund_run(db, fund_id)
    if not row or not row.metrics or row.metrics.get("error"):
        return None
    m = row.metrics
    return {
        "run_id": row.id,
        "fund_id": row.fund_id,
        "validation_type": row.validation_type,
        "period_start": row.period_start,
        "period_end": row.period_end,
        "initial_capital": row.initial_capital,
        "total_return_pct": m.get("total_return_pct"),
        "cagr_pct": m.get("cagr_pct"),
        "annualized_return_pct": m.get("annualized_return_pct"),
        "weekly_return_pct": m.get("weekly_return_pct"),
        "monthly_return_pct": m.get("monthly_return_pct"),
        "avg_weekly_return_pct": m.get("avg_weekly_return_pct"),
        "avg_monthly_return_pct": m.get("avg_monthly_return_pct"),
        "sharpe_ratio": m.get("sharpe_ratio"),
        "sortino_ratio": m.get("sortino_ratio"),
        "calmar_ratio": m.get("calmar_ratio"),
        "max_drawdown_pct": m.get("max_drawdown_pct"),
        "volatility_pct": m.get("volatility_pct"),
        "win_rate_pct": m.get("win_rate_pct"),
        "profit_factor": m.get("profit_factor"),
        "yield_delivery_pct": m.get("yield_delivery_pct"),
        "final_equity": m.get("final_equity"),
        "simulation_days": m.get("simulation_days"),
        "rebalance_count": m.get("rebalance_count"),
        "symbols_used": m.get("symbols_used"),
        "meets_target_monthly": m.get("meets_target_monthly"),
        "alpha_20pct_supported": m.get("alpha_20pct_supported"),
        "data_coverage": row.data_coverage,
        "equity_curve": row.equity_curve,
        "experiment_config": row.experiment_config if hasattr(row, "experiment_config") else {},
        "rank_score": row.rank_score if hasattr(row, "rank_score") else None,
        "allocation_policy": row.allocation_policy_snapshot,
        "data_provenance": "VALIDATED_HISTORICAL",
    }


def compute_fund_display_metrics(
    db: Session,
    fund: domain.Fund,
    include_demo: bool = False,
) -> dict[str, Any]:
    """Primary fund performance for UI — validated historical only unless include_demo=True."""
    validated = validated_fund_metrics(db, fund.id)

    portfolios = (
        db.query(domain.Portfolio)
        .filter(domain.Portfolio.fund_pk_id == fund.pk_id, domain.Portfolio.auto_managed == True)
        .all()
    )
    total_aum = sum(p.total_equity or 0.0 for p in portfolios)

    if validated:
        return {
            "portfolio_count": len(portfolios),
            "total_aum": round(total_aum, 2),
            "client_count": len({p.user_id for p in portfolios}),
            "actual_total_return_pct": validated.get("total_return_pct"),
            "actual_weekly_return_pct": validated.get("avg_weekly_return_pct"),
            "actual_monthly_return_pct": validated.get("avg_monthly_return_pct"),
            "data_provenance": "VALIDATED_HISTORICAL",
            "validated": validated,
            "demo": _demo_fund_actuals(db, portfolios) if include_demo else None,
        }

    return {
        "portfolio_count": len(portfolios),
        "total_aum": round(total_aum, 2),
        "client_count": len({p.user_id for p in portfolios}),
        "actual_total_return_pct": None,
        "actual_weekly_return_pct": None,
        "actual_monthly_return_pct": None,
        "data_provenance": "UNVALIDATED",
        "validated": None,
        "demo": _demo_fund_actuals(db, portfolios) if include_demo else None,
        "message": "Run historical fund backtest: POST /api/validated/fund/run-all",
    }


def _demo_fund_actuals(db: Session, portfolios: list[domain.Portfolio]) -> dict[str, Any]:
    """Demo ledger metrics — admin-only, never shown as primary performance."""
    from app.services.fund_performance_service import compute_fund_actuals, detect_fund_provenance

    demo_portfolios = [p for p in portfolios if not p.id.endswith("-VALIDATED")]
    if not demo_portfolios:
        return {}
    fund_pk = demo_portfolios[0].fund_pk_id
    fund = db.query(domain.Fund).filter(domain.Fund.pk_id == fund_pk).first()
    if not fund:
        return {}
    actuals = compute_fund_actuals(db, fund, exclude_validated=True)
    actuals["data_provenance"] = detect_fund_provenance(db, demo_portfolios)
    actuals["portfolio_count"] = len(demo_portfolios)
    actuals["total_aum"] = round(sum(p.total_equity or 0 for p in demo_portfolios), 2)
    actuals["client_count"] = len({p.user_id for p in demo_portfolios})
    return actuals
