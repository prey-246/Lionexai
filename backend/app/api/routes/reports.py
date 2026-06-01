from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
import uuid
from datetime import datetime, timedelta

from app.core.database import get_db
from app.services import audit_service
from app.api.deps import get_current_user
from app.models import domain, schemas

router = APIRouter()

@router.post("/generate", response_model=schemas.Report)
def generate_report(
    report_in: schemas.ReportGenerate,
    db: Session = Depends(get_db),
    current_user: domain.User = Depends(get_current_user)
):
    """
    Generate a performance report for a portfolio.
    """
    portfolio = db.query(domain.Portfolio).filter(
        domain.Portfolio.id == report_in.portfolio_id,
        domain.Portfolio.user_id == current_user.id
    ).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    # Determine date range
    end_date = report_in.end_date or datetime.utcnow()
    if report_in.report_type == "WEEKLY":
        start_date = report_in.start_date or (end_date - timedelta(days=7))
    elif report_in.report_type == "MONTHLY":
        start_date = report_in.start_date or (end_date - timedelta(days=30))
    else:
        raise HTTPException(status_code=400, detail="Invalid report type")

    # Query trades within the date range
    trades = db.query(domain.Trade).filter(
        domain.Trade.portfolio_id == portfolio.id,
        domain.Trade.status == "CLOSED",
        domain.Trade.closed_at >= start_date,
        domain.Trade.closed_at <= end_date
    ).all()
    
    total_trades = len(trades)
    winning_trades = len([t for t in trades if t.pnl > 0])
    total_pnl = sum(t.pnl for t in trades)
    
    performance_metrics = {
        "total_return_pct": round((total_pnl / portfolio.total_equity) * 100, 2) if portfolio.total_equity > 0 else 0,
        "win_rate": round((winning_trades / total_trades) * 100, 2) if total_trades > 0 else 0,
        "winning_trades": winning_trades,
        "total_trades": total_trades,
    }
    risk_metrics = {"max_drawdown_pct": 0.0} # Placeholder
    trades_summary = {"total_trades": total_trades}

    new_report = domain.Report(
        id=f"report_{uuid.uuid4().hex[:12]}",
        portfolio_id=portfolio.id,
        report_type=report_in.report_type,
        period_start=start_date,
        period_end=end_date,
        performance_metrics=performance_metrics,
        risk_metrics=risk_metrics,
        trades_summary=trades_summary,
    )
    db.add(new_report)
    db.commit()
    db.refresh(new_report)

    audit_service.create_audit_log(
        db,
        action_type="REPORT_GENERATED",
        description=f"User '{current_user.email}' generated a {report_in.report_type} report for portfolio '{report_in.portfolio_id}'.",
        metadata={
            "user_id": current_user.id,
            "user_email": current_user.email,
            "portfolio_id": report_in.portfolio_id,
            "report_id": new_report.id,
            "report_type": report_in.report_type
        }
    )
    
    return new_report

@router.get("/{portfolio_id}", response_model=List[schemas.Report])
def get_reports(
    portfolio_id: str,
    db: Session = Depends(get_db),
    current_user: domain.User = Depends(get_current_user)
):
    """
    Retrieve generated reports for a portfolio.
    """
    reports = db.query(domain.Report).filter(domain.Report.portfolio_id == portfolio_id).order_by(domain.Report.created_at.desc()).all()
    return reports