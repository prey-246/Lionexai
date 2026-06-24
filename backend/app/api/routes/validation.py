import logging
from datetime import datetime, timedelta, timezone, date
from fastapi import APIRouter, Depends, Response
from sqlalchemy import func
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Dict, Any

from app.core.database import get_db
from app.models import domain
from app.api.deps import require_role
from app.services.pdf_service import generate_pdf_from_template
from app.services.validation_constants import EXECUTED_ACTIONS, REJECTED_ACTIONS, PAPER_TRADE_SOURCE
from app.services.validation_service import (
    update_validation_snapshots_job,
    compute_validation_for_date_range,
    query_validation_history,
    query_metric_timeseries,
    archive_snapshots_to_history,
)
from app.services.validation_report_service import (
    build_validation_report_context,
    validation_pdf_filename,
)

logger = logging.getLogger(__name__)
router = APIRouter()

class DayStat(BaseModel):
    day: str
    trades_executed: int
    success_rate: float
    risk_rejections: int

class AggregatedResults(BaseModel):
    total_orders: int
    filled_orders: int
    rejected_orders: int
    average_latency: float
    best_portfolio: str | None
    worst_portfolio: str | None

class ValidationSummary(BaseModel):
    daily_stats: List[DayStat]
    aggregated: AggregatedResults

@router.get("/summary", response_model=ValidationSummary, dependencies=[Depends(require_role(["admin", "operator", "risk_manager"]))])
def get_validation_summary(db: Session = Depends(get_db)):
    now = datetime.utcnow()
    daily_stats = []

    for i in range(3):
        day_start = (now - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)

        filled = db.query(func.count(domain.AuditLog.id)).filter(
            domain.AuditLog.action_type.in_(EXECUTED_ACTIONS),
            domain.AuditLog.timestamp.between(day_start, day_end),
            domain.AuditLog.metadata_json.op('->>')('exchange').in_(['binance', 'bybit']),
        ).scalar() or 0

        rejected = db.query(func.count(domain.AuditLog.id)).filter(
            domain.AuditLog.action_type.in_(REJECTED_ACTIONS),
            domain.AuditLog.timestamp.between(day_start, day_end),
            domain.AuditLog.metadata_json.op('->>')('exchange').in_(['binance', 'bybit']),
        ).scalar() or 0

        total = filled + rejected
        success_rate = (filled / total * 100) if total > 0 else 100.0

        daily_stats.append(DayStat(
            day=f"Day {i+1}",
            trades_executed=filled,
            success_rate=round(success_rate, 2),
            risk_rejections=rejected
        ))

    three_days_ago = now - timedelta(days=3)
    paper_audit = db.query(domain.AuditLog).filter(
        domain.AuditLog.timestamp >= three_days_ago,
        domain.AuditLog.metadata_json.op('->>')('exchange').in_(['binance', 'bybit']),
    )
    total_filled = paper_audit.filter(domain.AuditLog.action_type.in_(EXECUTED_ACTIONS)).count()
    total_rejected = paper_audit.filter(domain.AuditLog.action_type.in_(REJECTED_ACTIONS)).count()
    
    latency_logs = paper_audit.filter(
        domain.AuditLog.action_type.in_(EXECUTED_ACTIONS),
        domain.AuditLog.metadata_json.op('->>')('latency_ms').isnot(None),
    ).with_entities(domain.AuditLog.metadata_json).all()
    latencies = [log[0]['latency_ms'] for log in latency_logs if log[0] and log[0].get('latency_ms') is not None]
    avg_latency = round(sum(latencies) / len(latencies), 2) if latencies else 0.0

    # Simplified PnL calculation for best/worst portfolio
    trades = db.query(domain.Trade.portfolio_id, domain.Trade.pnl).filter(
        domain.Trade.trade_source == PAPER_TRADE_SOURCE,
        domain.Trade.created_at >= three_days_ago,
        domain.Trade.pnl.isnot(None),
    ).all()
    pnl_by_portfolio = {}
    for trade in trades:
        pnl_by_portfolio[trade.portfolio_id] = pnl_by_portfolio.get(trade.portfolio_id, 0) + trade.pnl
    
    best_pk = max(pnl_by_portfolio, key=pnl_by_portfolio.get) if pnl_by_portfolio else None
    worst_pk = min(pnl_by_portfolio, key=pnl_by_portfolio.get) if pnl_by_portfolio else None

    portfolio_rows = (
        db.query(domain.Portfolio.pk_id, domain.Portfolio.id)
        .filter(domain.Portfolio.pk_id.in_(list(pnl_by_portfolio.keys())))
        .all()
        if pnl_by_portfolio
        else []
    )
    portfolio_id_map = {pk: portfolio_id for pk, portfolio_id in portfolio_rows}

    best_portfolio = portfolio_id_map.get(best_pk) if best_pk is not None else None
    worst_portfolio = portfolio_id_map.get(worst_pk) if worst_pk is not None else None

    aggregated = AggregatedResults(
        total_orders=total_filled + total_rejected,
        filled_orders=total_filled,
        rejected_orders=total_rejected,
        average_latency=avg_latency,
        best_portfolio=best_portfolio,
        worst_portfolio=worst_portfolio
    )

    return ValidationSummary(daily_stats=daily_stats, aggregated=aggregated)

def _render_validation_pdf(db: Session, period: str) -> tuple[bytes, str]:
    context = build_validation_report_context(db, period=period)
    pdf_bytes = generate_pdf_from_template("validation_report.html", context)
    filename = validation_pdf_filename(context.get("period_code", period))
    return pdf_bytes, filename


@router.get("/report/pdf", dependencies=[Depends(require_role(["admin", "operator", "risk_manager"]))])
def get_validation_report_pdf(period: str = "30D", db: Session = Depends(get_db)):
    """Institutional validation PDF. period: TODAY, 7D, 14D, 30D, ALL."""
    pdf_bytes, filename = _render_validation_pdf(db, period)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


class ExchangeDistribution(BaseModel):
    binance: int = 0
    bybit: int = 0
    binance_pct: float = 0.0
    bybit_pct: float = 0.0


class ValidationSnapshotResponse(BaseModel):
    snapshot_key: str
    snapshot_type: str
    period: str
    scope_id: str | None = None
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate_pct: float
    total_pnl: float
    profit_factor: float | None
    sharpe_ratio: float | None
    max_drawdown_pct: float
    avg_return_pct: float
    largest_win: float
    largest_loss: float
    avg_latency_ms: float
    fill_rate_pct: float
    total_orders: int = 0
    filled_orders: int = 0
    rejected_orders: int = 0
    best_portfolio: str | None = None
    worst_portfolio: str | None = None
    best_strategy: str | None = None
    worst_strategy: str | None = None
    exchange_distribution: ExchangeDistribution | None = None
    chart_data: Dict[str, Any] | None
    updated_at: datetime

    class Config:
        from_attributes = True


def _snapshot_to_response(snapshot: domain.ValidationSnapshot) -> ValidationSnapshotResponse:
    # Use Pydantic's model_validate (from_orm in v1) to directly map the ORM object
    # to the response model. This is cleaner and less error-prone.
    # The `from_attributes=True` in the model's Config enables this.
    return ValidationSnapshotResponse.model_validate(snapshot)

@router.post("/snapshots/refresh", dependencies=[Depends(require_role(["admin", "operator", "risk_manager"]))])
def refresh_validation_snapshots(db: Session = Depends(get_db)):
    """Force immediate recalculation of all validation snapshots."""
    update_validation_snapshots_job()
    return {"status": "ok", "message": "Validation snapshots refreshed."}


@router.get("/snapshots", response_model=List[ValidationSnapshotResponse], dependencies=[Depends(require_role(["admin", "operator", "risk_manager"]))])
def get_validation_snapshots(
    period: str | None = None,
    snapshot_type: str | None = None,
    scope_id: str | None = None,
    db: Session = Depends(get_db)
):
    """
    Retrieve pre-calculated validation snapshots.
    Filter by period (7D, 14D, 30D, ALL), type (GLOBAL, PORTFOLIO, STRATEGY), or scope_id.
    """
    count = db.query(domain.ValidationSnapshot).count()
    if count == 0:
        update_validation_snapshots_job()

    query = db.query(domain.ValidationSnapshot)

    if period:
        query = query.filter(domain.ValidationSnapshot.period == period.upper())

    if snapshot_type:
        query = query.filter(domain.ValidationSnapshot.snapshot_type == snapshot_type.upper())

    if scope_id:
        query = query.filter(domain.ValidationSnapshot.scope_id == scope_id)

    snapshots = query.order_by(domain.ValidationSnapshot.snapshot_key).all()
    return [_snapshot_to_response(s) for s in snapshots]


class ValidationHistoryResponse(BaseModel):
    archive_date: date
    snapshot_key: str
    snapshot_type: str
    period: str
    scope_id: str | None = None
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate_pct: float
    total_pnl: float
    profit_factor: float | None
    sharpe_ratio: float | None
    max_drawdown_pct: float
    avg_return_pct: float
    largest_win: float
    largest_loss: float
    avg_latency_ms: float
    fill_rate_pct: float
    archived_at: datetime

    class Config:
        from_attributes = True


class MetricTimeseriesPoint(BaseModel):
    date: str
    time: int
    value: float | None


class MetricTimeseriesResponse(BaseModel):
    snapshot_key: str
    metric: str
    series: List[MetricTimeseriesPoint]


def _history_to_response(row: domain.ValidationSnapshotHistory) -> ValidationHistoryResponse:
    return ValidationHistoryResponse(
        archive_date=row.archive_date,
        snapshot_key=row.snapshot_key,
        snapshot_type=row.snapshot_type,
        period=row.period,
        scope_id=row.scope_id,
        total_trades=row.total_trades,
        winning_trades=row.winning_trades,
        losing_trades=row.losing_trades,
        win_rate_pct=row.win_rate_pct,
        total_pnl=row.total_pnl,
        profit_factor=row.profit_factor,
        sharpe_ratio=row.sharpe_ratio,
        max_drawdown_pct=row.max_drawdown_pct,
        avg_return_pct=row.avg_return_pct,
        largest_win=row.largest_win,
        largest_loss=row.largest_loss,
        avg_latency_ms=row.avg_latency_ms,
        fill_rate_pct=row.fill_rate_pct,
        archived_at=row.archived_at,
    )


def _computed_to_response(data: dict[str, Any]) -> ValidationSnapshotResponse:
    exchange_raw = data.get("exchange_distribution") or {}
    return ValidationSnapshotResponse(
        snapshot_key=data["snapshot_key"],
        snapshot_type=data["snapshot_type"],
        period=data["period"],
        scope_id=data.get("scope_id"),
        total_trades=data["total_trades"],
        winning_trades=data["winning_trades"],
        losing_trades=data["losing_trades"],
        win_rate_pct=data["win_rate_pct"],
        total_pnl=data["total_pnl"],
        profit_factor=data.get("profit_factor"),
        sharpe_ratio=data.get("sharpe_ratio"),
        max_drawdown_pct=data["max_drawdown_pct"],
        avg_return_pct=data["avg_return_pct"],
        largest_win=data["largest_win"],
        largest_loss=data["largest_loss"],
        avg_latency_ms=data["avg_latency_ms"],
        fill_rate_pct=data["fill_rate_pct"],
        total_orders=data.get("total_orders", 0),
        filled_orders=data.get("filled_orders", 0),
        rejected_orders=data.get("rejected_orders", 0),
        best_portfolio=data.get("best_portfolio"),
        worst_portfolio=data.get("worst_portfolio"),
        best_strategy=data.get("best_strategy"),
        worst_strategy=data.get("worst_strategy"),
        exchange_distribution=ExchangeDistribution(**exchange_raw) if exchange_raw else None,
        chart_data=data.get("chart_data") or None,
        updated_at=datetime.utcnow(),
    )


@router.get("/snapshots/range", response_model=ValidationSnapshotResponse, dependencies=[Depends(require_role(["admin", "operator", "risk_manager"]))])
def get_validation_snapshot_for_range(
    start_date: datetime,
    end_date: datetime,
    portfolio_id: str | None = None,
    strategy: str | None = None,
    db: Session = Depends(get_db),
):
    """Compute validation metrics for a custom start/end date window."""
    if end_date <= start_date:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="end_date must be after start_date")
    try:
        data = compute_validation_for_date_range(db, start_date, end_date, portfolio_id, strategy)
    except ValueError as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=str(e))
    return _computed_to_response(data)


@router.get("/history", response_model=List[ValidationHistoryResponse], dependencies=[Depends(require_role(["admin", "operator", "risk_manager"]))])
def get_validation_history(
    snapshot_key: str | None = None,
    snapshot_type: str | None = None,
    scope_id: str | None = None,
    period: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """Query append-only daily validation snapshot archives."""
    rows = query_validation_history(
        db,
        snapshot_key=snapshot_key,
        snapshot_type=snapshot_type,
        scope_id=scope_id,
        period=period,
        start_date=start_date,
        end_date=end_date,
        limit=min(limit, 500),
    )
    return [_history_to_response(r) for r in rows]


@router.get("/history/metrics", response_model=MetricTimeseriesResponse, dependencies=[Depends(require_role(["admin", "operator", "risk_manager"]))])
def get_validation_metric_timeseries(
    snapshot_key: str,
    metric: str = "win_rate_pct",
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
):
    """Rolling metric time-series from daily archives (win rate, drawdown, PnL, etc.)."""
    from fastapi import HTTPException
    try:
        series = query_metric_timeseries(db, snapshot_key, metric, start_date, end_date)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return MetricTimeseriesResponse(
        snapshot_key=snapshot_key,
        metric=metric,
        series=[MetricTimeseriesPoint(**point) for point in series],
    )


@router.post("/history/archive", dependencies=[Depends(require_role(["admin", "operator", "risk_manager"]))])
def force_archive_validation_snapshots(db: Session = Depends(get_db)):
    """Force archive of current snapshots into daily history."""
    count = archive_snapshots_to_history(db)
    return {"status": "ok", "archived": count}


class SimulationParams(BaseModel):
    deposit: float
    monthly_contribution: float
    months: int
    scenario: str
    fund_type: str

@router.post("/reports/generate-simulation", dependencies=[Depends(require_role(["client", "admin"]))])
def generate_simulation_report(params: SimulationParams):
    weekly_rates = {
        'CONSERVATIVE': 0.005,
        'BALANCED': 0.010,
        'AGGRESSIVE': 0.015,
    }
    weekly_rate = weekly_rates.get(params.scenario, 0.01)
    total_weeks = params.months * 4
    
    current_capital = params.deposit
    total_contributions = 0
    growth_table = []

    for i in range(1, total_weeks + 1):
        if i > 1 and (i - 1) % 4 == 0:
            current_capital += params.monthly_contribution
            total_contributions += params.monthly_contribution
        
        current_capital *= (1 + weekly_rate)

        if i % 4 == 0: # End of month
            month = i // 4
            growth_table.append({
                "month": month,
                "capital": round(current_capital, 2)
            })

    final_capital = growth_table[-1]['capital'] if growth_table else params.deposit
    total_yield = final_capital - params.deposit - total_contributions

    context = {
        "report_date": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "params": params.dict(),
        "growth_table": [
            {"month": row["month"], "capital": f"{row['capital']:,.2f}"}
            for row in growth_table
        ],
        "final_capital": f"{final_capital:,.2f}",
        "total_yield": f"{total_yield:,.2f}",
        "total_contributions": f"{total_contributions:,.2f}",
        "deposit": f"{params.deposit:,.2f}",
        "monthly_contribution": f"{params.monthly_contribution:,.2f}",
    }
    pdf_bytes = generate_pdf_from_template("simulation_report.html", context)
    return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=growth_simulation_report.pdf"})