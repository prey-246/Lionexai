"""Phase 5 — Validated performance APIs (historical / paper / research)."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_role
from app.core.database import get_db
from app.models import domain
from app.validation.real_strategy_validation import RealStrategyValidator
from app.services.allocation_integrity_monitor import run_integrity_scan
from app.services.paper_trading_validation_service import update_paper_validation_snapshots
from app.engines.global_risk_engine import GlobalRiskEngine

router = APIRouter()


def _normalize_strategy_run_metrics(validation_type: str, metrics: dict | None) -> dict:
    """Ensure list API returns displayable fields for all validation types."""
    m = dict(metrics or {})
    vt = (validation_type or "BACKTEST").upper()

    # Strip overflow artifacts from pre-fix runs
    sharpe = m.get("sharpe_ratio")
    if sharpe is not None and abs(float(sharpe)) > 1000:
        m["sharpe_ratio"] = 0.0

    if vt == "WALK_FORWARD":
        fe = float(m.get("final_equity") or 100_000)
        m.setdefault("total_return_pct", round((fe / 100_000 - 1) * 100, 2))
        m.setdefault("cagr_pct", m.get("total_return_pct"))
        oos = m.get("avg_oos_return_pct")
        if oos is not None:
            m.setdefault("avg_monthly_return_pct", round(float(oos) / 3.0, 2))
    elif vt == "MONTE_CARLO":
        m.setdefault("avg_monthly_return_pct", m.get("avg_monthly_return_pct"))
        m.setdefault("cagr_pct", m.get("cagr_pct"))

    return m


class StrategyValidationRequest(BaseModel):
    symbol: str
    strategy_key: str
    validation_type: str = "BACKTEST"  # BACKTEST, WALK_FORWARD, MONTE_CARLO
    initial_capital: float = Field(100_000, gt=0)
    persist: bool = True


class AlphaEvidenceRequest(BaseModel):
    fund_id: str = "ALPHA"
    target_monthly_pct: float = 20.0


class FundBacktestRequest(BaseModel):
    fund_id: str = "PRESERVE"
    initial_capital: float = Field(1_000_000, gt=0)
    bar_limit: int = Field(2000, ge=60, le=5000)
    persist: bool = True


class FundBacktestAllRequest(BaseModel):
    initial_capital: float = Field(1_000_000, gt=0)
    bar_limit: int = Field(2000, ge=60, le=5000)
    persist: bool = True


@router.post("/strategy/run", dependencies=[Depends(require_role(["admin", "operator", "risk_manager"]))])
def run_strategy_validation(body: StrategyValidationRequest, db: Session = Depends(get_db)):
    validator = RealStrategyValidator(db)
    try:
        if body.validation_type == "WALK_FORWARD":
            result = validator.run_walk_forward(body.symbol, body.strategy_key, initial_capital=body.initial_capital)
        elif body.validation_type == "MONTE_CARLO":
            result = validator.run_monte_carlo(body.symbol, body.strategy_key, initial_capital=body.initial_capital)
        else:
            result = validator.run_single_asset_backtest(
                body.symbol, body.strategy_key, initial_capital=body.initial_capital,
            )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    row = validator.persist_run(result) if body.persist else None
    return {"result": result.to_dict(), "persisted_id": row.id if row else None}


@router.get("/strategy/runs", dependencies=[Depends(require_role(["admin", "operator", "risk_manager"]))])
def list_validated_runs(
    strategy_key: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    q = db.query(domain.ValidatedStrategyRun).order_by(domain.ValidatedStrategyRun.created_at.desc())
    if strategy_key:
        q = q.filter(domain.ValidatedStrategyRun.strategy_key == strategy_key.upper())
    rows = q.limit(limit).all()
    return [
        {
            "id": r.id,
            "strategy_key": r.strategy_key,
            "symbol": r.symbol,
            "validation_type": r.validation_type,
            "metrics": _normalize_strategy_run_metrics(r.validation_type, r.metrics),
            "provenance": r.provenance,
            "period_start": r.period_start,
            "period_end": r.period_end,
            "created_at": r.created_at,
        }
        for r in rows
    ]


@router.post("/alpha/evidence", dependencies=[Depends(require_role(["admin", "operator", "risk_manager"]))])
def alpha_monthly_evidence(body: AlphaEvidenceRequest, db: Session = Depends(get_db)):
    """Objective framework: can Alpha achieve founder monthly target?"""
    from app.services.alpha_evidence_service import AlphaEvidenceService
    try:
        return AlphaEvidenceService(db).evaluate(body.target_monthly_pct, body.fund_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/paper/snapshots", dependencies=[Depends(require_role(["admin", "operator", "risk_manager"]))])
def get_paper_validation_snapshots(period: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(domain.PaperTradingValidationSnapshot).order_by(
        domain.PaperTradingValidationSnapshot.computed_at.desc()
    )
    if period:
        q = q.filter(domain.PaperTradingValidationSnapshot.period == period.upper())
    return [
        {"id": r.id, "period": r.period, "scope": r.scope, "metrics": r.metrics, "provenance": r.provenance, "computed_at": r.computed_at}
        for r in q.limit(20).all()
    ]


@router.post("/paper/refresh", dependencies=[Depends(require_role(["admin", "operator"]))])
def refresh_paper_validation(db: Session = Depends(get_db)):
    count = update_paper_validation_snapshots(db)
    return {"updated_periods": count}


@router.get("/global-risk")
def get_global_risk_assessment(db: Session = Depends(get_db), current_user: domain.User = Depends(get_current_user)):
    return GlobalRiskEngine(db).assess().to_dict()


@router.post("/fund/run", dependencies=[Depends(require_role(["admin", "operator", "risk_manager"]))])
def run_fund_backtest(body: FundBacktestRequest, db: Session = Depends(get_db)):
    """Historical fund backtest on market_bars using allocation-engine logic."""
    from app.validation.historical_fund_simulator import HistoricalFundSimulator

    sim = HistoricalFundSimulator(db)
    try:
        result = sim.run_fund_backtest(body.fund_id, body.initial_capital, body.bar_limit)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    row = sim.persist_run(result) if body.persist else None
    return {"result": result.to_dict(), "persisted_id": row.id if row else None}


@router.post("/fund/run-all", dependencies=[Depends(require_role(["admin", "operator", "risk_manager"]))])
def run_all_fund_backtests(body: FundBacktestAllRequest, db: Session = Depends(get_db)):
    from app.validation.historical_fund_simulator import HistoricalFundSimulator

    results = HistoricalFundSimulator(db).run_all_funds(
        body.initial_capital, body.bar_limit, persist=body.persist,
    )
    return {"results": [r.to_dict() for r in results]}


@router.get("/fund/runs")
def list_validated_fund_runs(
    fund_id: Optional[str] = None,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: domain.User = Depends(get_current_user),
):
    q = db.query(domain.ValidatedFundRun).order_by(domain.ValidatedFundRun.created_at.desc())
    if fund_id:
        q = q.filter(domain.ValidatedFundRun.fund_id == fund_id.upper())
    return [
        {
            "id": r.id,
            "fund_id": r.fund_id,
            "validation_type": r.validation_type,
            "metrics": r.metrics,
            "provenance": r.provenance,
            "period_start": r.period_start,
            "period_end": r.period_end,
            "data_coverage": r.data_coverage,
            "created_at": r.created_at,
        }
        for r in q.limit(limit).all()
    ]


@router.get("/fund/latest/{fund_id}")
def get_latest_fund_backtest(
    fund_id: str,
    include_demo: bool = False,
    db: Session = Depends(get_db),
    current_user: domain.User = Depends(get_current_user),
):
    from app.services.validated_fund_service import validated_fund_metrics, compute_fund_display_metrics

    fund = db.query(domain.Fund).filter(domain.Fund.id == fund_id.upper()).first()
    if not fund:
        raise HTTPException(status_code=404, detail="Fund not found")
    metrics = validated_fund_metrics(db, fund_id)
    if not metrics:
        raise HTTPException(
            status_code=404,
            detail=f"No validated historical backtest for {fund_id}. Run POST /api/validated/optimization/run",
        )
    if include_demo and current_user.role_tier in ("admin", "operator"):
        display = compute_fund_display_metrics(db, fund, include_demo=True)
        metrics["demo_comparison"] = display.get("demo")
    return metrics


class OptimizationRunRequest(BaseModel):
    phase: str = "all"
    fund_id: str | None = None
    bar_limit: int = Field(2000, ge=756, le=5000)
    persist: bool = True
    regenerate: bool = True


@router.post("/optimization/run", dependencies=[Depends(require_role(["admin", "operator"]))])
def run_optimization_program(body: OptimizationRunRequest, db: Session = Depends(get_db)):
    from app.validation.alpha_optimization_engine import AlphaOptimizationEngine
    from app.validation.validated_institutional_regenerator import ValidatedInstitutionalRegenerator

    engine = AlphaOptimizationEngine(db, bar_limit=body.bar_limit)
    if body.phase == "verify":
        return engine.verify_history_depth()
    if body.phase == "strategy-matrix":
        return {"results": engine.run_strategy_matrix(persist=body.persist)}
    if body.phase == "asset-analysis":
        return engine.analyze_asset_universe()
    if body.phase == "grid":
        fid = (body.fund_id or "ALPHA").upper()
        return {"fund_id": fid, "experiments": engine.run_fund_grid(fid, persist=body.persist)}
    if body.phase == "select-best":
        fid = (body.fund_id or "ALPHA").upper()
        sel = engine.select_best_per_fund(fid)
        return {"fund_id": fid, "best_run_id": sel.best_run_id, "best_metrics": sel.best_metrics, "config": sel.best_config}

    result = engine.run_full_program(persist=body.persist)
    if body.regenerate and result.get("status") == "complete":
        result["regeneration"] = ValidatedInstitutionalRegenerator(db).regenerate_all()
    return result


@router.get("/optimization/experiments")
def list_optimization_experiments(
    fund_id: str | None = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: domain.User = Depends(get_current_user),
):
    q = (
        db.query(domain.ValidatedFundRun)
        .filter(domain.ValidatedFundRun.validation_type.like("OPTIMIZATION%"))
        .order_by(domain.ValidatedFundRun.rank_score.desc().nullslast())
    )
    if fund_id:
        q = q.filter(domain.ValidatedFundRun.fund_id == fund_id.upper())
    rows = q.limit(limit).all()
    return [
        {
            "id": r.id,
            "fund_id": r.fund_id,
            "validation_type": r.validation_type,
            "rank_score": r.rank_score,
            "metrics": r.metrics,
            "experiment_config": r.experiment_config,
            "created_at": r.created_at,
        }
        for r in rows
    ]


@router.post("/allocation/integrity-scan", dependencies=[Depends(require_role(["admin", "operator", "risk_manager"]))])
def allocation_integrity_scan(db: Session = Depends(get_db)):
    return run_integrity_scan(db)


@router.get("/allocation/alerts", dependencies=[Depends(require_role(["admin", "operator", "risk_manager"]))])
def list_allocation_alerts(resolved: bool = False, limit: int = 50, db: Session = Depends(get_db)):
    rows = (
        db.query(domain.AllocationIntegrityAlert)
        .filter(domain.AllocationIntegrityAlert.resolved == resolved)
        .order_by(domain.AllocationIntegrityAlert.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": r.id,
            "portfolio_id": r.portfolio_id,
            "alert_type": r.alert_type,
            "severity": r.severity,
            "message": r.message,
            "symbol": r.symbol,
            "metadata": r.metadata_json,
            "created_at": r.created_at,
        }
        for r in rows
    ]
