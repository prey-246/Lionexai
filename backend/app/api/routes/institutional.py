"""Phase 6 — Institutional production readiness APIs."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel

from app.api.deps import get_current_user, require_role
from app.core.database import get_db
from app.models import domain
from app.analytics.performance_engine import PerformanceEngine
from app.services.live_validation_engine import update_live_validation_snapshots
from app.services.treasury_verification_engine import TreasuryVerificationEngine
from app.services.lnx_attribution_engine import LNXAttributionEngine
from app.services.execution_lifecycle_service import trace_trade, recent_events
from app.services.asset_classification import seed_extended_assets, classify_asset, risk_constraints_for_portfolio
from app.services.alpha_evidence_service import AlphaEvidenceService
from app.services.institutional_report_service import InstitutionalReportService
from app.services.providers.fred_provider import fetch_macro_snapshot
from sqlalchemy.orm import Session

router = APIRouter()


class AlphaEvidenceBody(BaseModel):
    fund_id: str = "ALPHA"
    target_monthly_pct: float = 20.0


class FundReportBody(BaseModel):
    fund_id: str = "PRESERVE"


@router.get("/performance/fund/{fund_id}")
def fund_analytics_v2(fund_id: str, db: Session = Depends(get_db), current_user: domain.User = Depends(get_current_user)):
    fund = db.query(domain.Fund).filter(domain.Fund.id == fund_id.upper()).first()
    if not fund:
        raise HTTPException(404, "Fund not found")
    engine = PerformanceEngine(db)
    analytics = engine.fund_analytics(fund)
    curve = engine.aggregate_fund_equity_curve(fund)
    return {
        **analytics,
        "performance_curve": curve,
        "target_vs_realized_vs_validated": {
            "target_monthly_pct": fund.target_monthly_return_pct,
            "target_weekly_pct": fund.target_weekly_return_pct,
            "realized_monthly_pct": analytics.get("realized_monthly_return_pct"),
            "realized_weekly_pct": analytics.get("realized_weekly_return_pct"),
            "validated_monthly_pct": analytics.get("validated_monthly_return_pct"),
        },
    }


@router.get("/live-validation/snapshots")
def list_live_validation(period: Optional[str] = None, db: Session = Depends(get_db), current_user: domain.User = Depends(get_current_user)):
    q = db.query(domain.LiveValidationSnapshot).order_by(domain.LiveValidationSnapshot.computed_at.desc())
    if period:
        q = q.filter(domain.LiveValidationSnapshot.period == period.upper())
    return [
        {"id": r.id, "period": r.period, "scope": r.scope, "scope_id": r.scope_id,
         "metrics": r.metrics, "provenance": r.provenance, "computed_at": r.computed_at}
        for r in q.limit(30).all()
    ]


@router.post("/live-validation/refresh", dependencies=[Depends(require_role(["admin", "operator"]))])
def refresh_live_validation(db: Session = Depends(get_db)):
    return {"updated": update_live_validation_snapshots(db)}


@router.get("/treasury/verify")
def verify_treasury(persist: bool = False, db: Session = Depends(get_db), current_user: domain.User = Depends(get_current_user)):
    engine = TreasuryVerificationEngine(db)
    result = engine.verify()
    row = engine.persist_run(result) if persist else None
    out = result.to_dict()
    if row:
        out["run_id"] = row.id
    return out


@router.get("/treasury/verification-runs", dependencies=[Depends(require_role(["admin", "operator", "risk_manager"]))])
def list_treasury_verifications(limit: int = 20, db: Session = Depends(get_db)):
    rows = db.query(domain.TreasuryVerificationRun).order_by(domain.TreasuryVerificationRun.created_at.desc()).limit(limit).all()
    return [{"id": r.id, "solvency_score": r.solvency_score, "status": r.status, "issues": r.issues, "created_at": r.created_at} for r in rows]


@router.get("/lnx/attribution")
def lnx_attribution(db: Session = Depends(get_db), current_user: domain.User = Depends(get_current_user)):
    engine = LNXAttributionEngine(db)
    return engine.compute_attribution(store=True)


@router.get("/lnx/attribution/history")
def lnx_attribution_history(limit: int = 30, db: Session = Depends(get_db), current_user: domain.User = Depends(get_current_user)):
    return LNXAttributionEngine(db).history(limit)


@router.get("/execution/trace/{trade_id}", dependencies=[Depends(require_role(["admin", "operator", "risk_manager"]))])
def execution_trace(trade_id: str, db: Session = Depends(get_db)):
    return trace_trade(db, trade_id)


@router.get("/execution/events", dependencies=[Depends(require_role(["admin", "operator", "risk_manager"]))])
def execution_events(stage: Optional[str] = None, limit: int = 100, db: Session = Depends(get_db)):
    return recent_events(db, limit, stage)


@router.post("/assets/seed-extended", dependencies=[Depends(require_role(["admin", "operator"]))])
def seed_assets(db: Session = Depends(get_db)):
    return {"added": seed_extended_assets(db)}


@router.get("/assets/{symbol}/classification")
def asset_classification(symbol: str, db: Session = Depends(get_db), current_user: domain.User = Depends(get_current_user)):
    asset = db.query(domain.Asset).filter(domain.Asset.symbol == symbol.upper()).first()
    if not asset:
        raise HTTPException(404, "Asset not found")
    return classify_asset(asset)


@router.get("/portfolios/{portfolio_id}/risk-constraints")
def portfolio_risk_constraints(portfolio_id: str, db: Session = Depends(get_db), current_user: domain.User = Depends(get_current_user)):
    p = db.query(domain.Portfolio).filter(domain.Portfolio.id == portfolio_id).first()
    if not p:
        raise HTTPException(404, "Portfolio not found")
    return risk_constraints_for_portfolio(db, p)


@router.get("/macro/snapshot")
def macro_snapshot(db: Session = Depends(get_db), current_user: domain.User = Depends(get_current_user)):
    snap = fetch_macro_snapshot()
    if snap.get("data_available"):
        import uuid
        db.add(domain.MacroDataSnapshot(
            id=f"macro_{uuid.uuid4().hex[:12]}",
            source="FRED",
            series_data=snap.get("series", {}),
            risk_drivers={"yield_curve_inverted": snap.get("yield_curve_inverted")},
        ))
        db.commit()
    return snap


@router.post("/alpha/evidence/full", dependencies=[Depends(require_role(["admin", "operator", "risk_manager"]))])
def alpha_evidence_full(body: AlphaEvidenceBody, db: Session = Depends(get_db)):
    return AlphaEvidenceService(db).evaluate(body.target_monthly_pct, body.fund_id)


@router.post("/reports/monthly-fund", dependencies=[Depends(require_role(["admin", "operator", "risk_manager"]))])
def generate_monthly_report(body: FundReportBody, db: Session = Depends(get_db)):
    return InstitutionalReportService(db).generate_monthly_fund_report(body.fund_id)


@router.get("/reports/institutional")
def list_institutional_reports(fund_id: Optional[str] = None, limit: int = 20, db: Session = Depends(get_db), current_user: domain.User = Depends(get_current_user)):
    return InstitutionalReportService(db).list_reports(fund_id, limit)


@router.get("/reports/institutional/{report_id}")
def get_institutional_report(report_id: str, db: Session = Depends(get_db), current_user: domain.User = Depends(get_current_user)):
    report = InstitutionalReportService(db).get_report(report_id)
    if not report:
        raise HTTPException(404, "Report not found")
    return report


@router.get("/reports/institutional/{report_id}/export/json")
def export_report_json(report_id: str, db: Session = Depends(get_db), current_user: domain.User = Depends(get_current_user)):
    svc = InstitutionalReportService(db)
    report = svc.get_report(report_id)
    if not report:
        raise HTTPException(404, "Report not found")
    return Response(content=svc.export_json(report), media_type="application/json")


@router.get("/reports/institutional/{report_id}/export/csv")
def export_report_csv(report_id: str, db: Session = Depends(get_db), current_user: domain.User = Depends(get_current_user)):
    svc = InstitutionalReportService(db)
    report = svc.get_report(report_id)
    if not report:
        raise HTTPException(404, "Report not found")
    return Response(content=svc.export_csv(report), media_type="text/csv")
