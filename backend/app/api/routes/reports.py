from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta
import uuid

from app.core.database import get_db
from app.models import schemas, domain
from app.api.deps import get_current_user
from app.api.portfolio_access import portfolio_for_user
from app.services.audit_service import create_audit_log
from app.services.pdf_service import generate_pdf_from_template

router = APIRouter()

@router.post("/generate", response_model=schemas.Report)
def generate_report(
    report_in: schemas.ReportGenerate,
    db: Session = Depends(get_db),
    current_user: domain.User = Depends(get_current_user)
):
    """Generate a new performance report for a portfolio."""
    portfolio = portfolio_for_user(db, report_in.portfolio_id, current_user)
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    end_date = report_in.end_date or datetime.utcnow()
    if report_in.report_type == 'WEEKLY':
        start_date = end_date - timedelta(days=7)
    elif report_in.report_type == 'MONTHLY':
        start_date = end_date - timedelta(days=30)
    elif report_in.report_type == 'CUSTOM' and report_in.start_date:
        start_date = report_in.start_date
    else:
        start_date = end_date - timedelta(days=30)

    trades = db.query(domain.Trade).filter(
        domain.Trade.portfolio_id == portfolio.pk_id,
        domain.Trade.status == "CLOSED",
        domain.Trade.closed_at >= start_date,
        domain.Trade.closed_at <= end_date
    ).all()

    total_trades = len(trades)
    if total_trades == 0:
        performance_metrics = {"total_pnl": 0, "win_rate_pct": 0, "winning_trades": 0, "losing_trades": 0}
    else:
        pnls = [t.pnl for t in trades if t.pnl is not None]
        winning_trades = len([p for p in pnls if p > 0])
        losing_trades = len([p for p in pnls if p < 0])
        initial_equity_for_period = portfolio.total_equity - sum(pnls)
        performance_metrics = {
            "total_pnl": round(sum(pnls), 2),
            "win_rate_pct": round((winning_trades / total_trades) * 100, 2),
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "total_return_pct": round((sum(pnls) / initial_equity_for_period) * 100, 2) if initial_equity_for_period > 0 else 0,
            "best_trade": round(max(pnls), 2) if pnls else 0,
            "worst_trade": round(min(pnls), 2) if pnls else 0,
        }

    new_report = domain.Report(
        id=f"report_{uuid.uuid4().hex[:12]}",
        portfolio_id=portfolio.pk_id,
        report_type=report_in.report_type,
        period_start=start_date,
        period_end=end_date,
        performance_metrics=performance_metrics
    )
    db.add(new_report)

    create_audit_log(
        db,
        action_type="REPORT_GENERATE",
        description=f"User '{current_user.email}' generated a '{new_report.report_type}' report for portfolio '{portfolio.id}'.",
        metadata_json={"report_id": new_report.id, "portfolio_id": portfolio.id, "user_id": current_user.id}
    )
    db.commit()
    db.refresh(new_report)

    return new_report

@router.get("/{report_id}/download")
def download_report(
    report_id: str,
    db: Session = Depends(get_db),
    current_user: domain.User = Depends(get_current_user)
):
    """Download a generated report as a PDF."""
    report = db.query(domain.Report).filter(domain.Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    portfolio = db.query(domain.Portfolio).filter(domain.Portfolio.pk_id == report.portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    if current_user.role_tier == "client" and portfolio.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    pdf_bytes = generate_pdf_from_template(
        "report.html",
        {
            "report": report,
            "portfolio": portfolio,
            "user": current_user,
            "date_generated": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        },
    )

    headers = {
        'Content-Disposition': f'attachment; filename="NEXA_{portfolio.id}_{report.report_type}.pdf"'
    }
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)

@router.get("/{portfolio_id}", response_model=List[schemas.Report])
def get_reports(
    portfolio_id: str,
    report_type: str | None = None,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: domain.User = Depends(get_current_user)
):
    """List generated reports for a portfolio."""
    portfolio = portfolio_for_user(db, portfolio_id, current_user)
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    query = db.query(domain.Report).filter(domain.Report.portfolio_id == portfolio.pk_id)

    if report_type:
        query = query.filter(domain.Report.report_type == report_type)

    reports = query.order_by(domain.Report.created_at.desc()).limit(limit).all()
    return reports
