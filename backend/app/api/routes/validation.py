import logging
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, Response
from sqlalchemy import and_, func, or_, cast
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import JSONB
from pydantic import BaseModel
from typing import List, Dict

from app.core.database import get_db
from app.models import domain
from app.api.deps import require_role
from app.services.pdf_service import generate_pdf_from_template

logger = logging.getLogger(__name__)
router = APIRouter()

EXECUTED_ACTIONS = (
    "AUTONOMOUS_TRADE_EXECUTED_BINANCE",
    "AUTONOMOUS_TRADE_EXECUTED_BYBIT",
    "AUTONOMOUS_TRADE_EXECUTED_VIA_BINANCE",
    "AUTONOMOUS_TRADE_EXECUTED_VIA_BYBIT",
    "ORDER_FILLED",
)

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
            domain.AuditLog.timestamp.between(day_start, day_end)
        ).scalar() or 0

        rejected = db.query(func.count(domain.AuditLog.id)).filter(
            domain.AuditLog.action_type == "RISK_REJECTION",
            domain.AuditLog.timestamp.between(day_start, day_end)
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
    total_filled = db.query(func.count(domain.AuditLog.id)).filter(domain.AuditLog.action_type.in_(EXECUTED_ACTIONS), domain.AuditLog.timestamp >= three_days_ago).scalar() or 0
    total_rejected = db.query(func.count(domain.AuditLog.id)).filter(domain.AuditLog.action_type == "RISK_REJECTION", domain.AuditLog.timestamp >= three_days_ago).scalar() or 0
    
    latency_logs = db.query(domain.AuditLog.metadata_json).filter(
        domain.AuditLog.action_type.in_(EXECUTED_ACTIONS),
        domain.AuditLog.timestamp >= three_days_ago,
        domain.AuditLog.metadata_json.op('->>')('latency_ms').isnot(None)
    ).all()
    latencies = [log[0]['latency_ms'] for log in latency_logs if log[0] and log[0].get('latency_ms') is not None]
    avg_latency = round(sum(latencies) / len(latencies), 2) if latencies else 0.0

    # Simplified PnL calculation for best/worst portfolio
    trades = db.query(domain.Trade.portfolio_id, domain.Trade.pnl).filter(domain.Trade.created_at >= three_days_ago, domain.Trade.pnl.isnot(None)).all()
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

@router.get("/report/pdf", dependencies=[Depends(require_role(["admin", "operator", "risk_manager"]))])
def get_validation_report_pdf(db: Session = Depends(get_db)):
    summary_data = get_validation_summary(db)
    context = {
        "report_date": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "summary": summary_data.dict()
    }
    pdf_bytes = generate_pdf_from_template("validation_report.html", context)
    return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=nexa_validation_report.pdf"})


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