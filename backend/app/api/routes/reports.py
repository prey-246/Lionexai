from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.core.database import get_db
from app.models.domain import Report, Portfolio, Trade, RiskEvent
from datetime import datetime, timedelta
from typing import Optional
import json

router = APIRouter()

class GenerateReportRequest(BaseModel):
    portfolio_id: str
    report_type: str  # WEEKLY, MONTHLY
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

class ReportMetrics(BaseModel):
    total_return_pct: float
    winning_trades: int
    losing_trades: int
    win_rate: float
    avg_trade_pnl: float
    best_trade: float
    worst_trade: float
    total_pnl: float

@router.post("/generate", summary="Generate a performance report")
def generate_report(request: GenerateReportRequest, db: Session = Depends(get_db)):
    portfolio = db.query(Portfolio).filter(Portfolio.id == request.portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    # Default date range: last week or month
    end_date = request.end_date or datetime.utcnow()
    if request.report_type == "WEEKLY":
        start_date = request.start_date or (end_date - timedelta(days=7))
    else:  # MONTHLY
        start_date = request.start_date or (end_date - timedelta(days=30))

    # Fetch trades in period
    trades = db.query(Trade).filter(
        Trade.portfolio_id == request.portfolio_id,
        Trade.created_at >= start_date,
        Trade.created_at <= end_date,
        Trade.status == "CLOSED"
    ).all()

    # Calculate metrics
    winning_trades = [t for t in trades if t.pnl > 0]
    losing_trades = [t for t in trades if t.pnl < 0]
    total_pnl = sum(t.pnl for t in trades)
    win_rate = len(winning_trades) / len(trades) * 100 if trades else 0

    best_trade = max([t.pnl for t in trades], default=0)
    worst_trade = min([t.pnl for t in trades], default=0)
    avg_trade_pnl = total_pnl / len(trades) if trades else 0

    # Calculate return
    total_return_pct = (total_pnl / portfolio.total_equity * 100) if portfolio.total_equity > 0 else 0

    # Fetch risk events
    risk_events = db.query(RiskEvent).filter(
        RiskEvent.portfolio_id == request.portfolio_id,
        RiskEvent.triggered_at >= start_date,
        RiskEvent.triggered_at <= end_date
    ).all()

    # Build report
    report = Report(
        portfolio_id=request.portfolio_id,
        report_type=request.report_type,
        period_start=start_date,
        period_end=end_date,
        performance_metrics={
            "total_return_pct": round(total_return_pct, 2),
            "total_pnl": round(total_pnl, 2),
            "winning_trades": len(winning_trades),
            "losing_trades": len(losing_trades),
            "win_rate": round(win_rate, 2),
            "best_trade": round(best_trade, 2),
            "worst_trade": round(worst_trade, 2),
            "avg_trade_pnl": round(avg_trade_pnl, 2)
        },
        risk_metrics={
            "max_drawdown_pct": portfolio.current_drawdown_pct,
            "risk_events": len(risk_events)
        },
        trades_summary={
            "total_trades": len(trades),
            "symbols_traded": list(set([t.symbol for t in trades]))
        }
    )

    db.add(report)
    db.commit()
    db.refresh(report)

    return {
        "id": report.id,
        "portfolio_id": report.portfolio_id,
        "report_type": report.report_type,
        "period": {
            "start": start_date,
            "end": end_date
        },
        "performance_metrics": report.performance_metrics,
        "risk_metrics": report.risk_metrics,
        "trades_summary": report.trades_summary
    }

@router.get("/{portfolio_id}", summary="Get reports for portfolio")
def get_portfolio_reports(
    portfolio_id: str,
    report_type: Optional[str] = None,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    query = db.query(Report).filter(Report.portfolio_id == portfolio_id)
    if report_type:
        query = query.filter(Report.report_type == report_type)

    reports = query.order_by(desc(Report.created_at)).limit(limit).all()
    return reports

@router.get("/report/{report_id}", summary="Get specific report")
def get_report(report_id: str, db: Session = Depends(get_db)):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report
