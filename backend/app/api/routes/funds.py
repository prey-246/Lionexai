import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.models import schemas, domain
from app.api.deps import get_current_user
from app.services.audit_service import create_audit_log
from app.engines.allocation_engine import AllocationEngine
from app.services.fund_performance_service import (
    compute_fund_actuals,
    format_target_return_label,
    compute_institutional_analytics,
)
from app.services.validated_fund_service import compute_fund_display_metrics
from app.engines.macro_intelligence import MacroIntelligenceEngine

router = APIRouter()


def _to_fund_response(fund: domain.Fund, db: Session) -> schemas.FundResponse:
    universe = []
    for fau in fund.asset_universe:
        if fau.asset:
            universe.append(schemas.FundAssetUniverseItem(
                symbol=fau.asset.symbol,
                display_name=fau.asset.display_name,
                asset_class=fau.asset.asset_class,
                min_weight_pct=fau.min_weight_pct,
                max_weight_pct=fau.max_weight_pct,
            ))
    display = compute_fund_display_metrics(db, fund, include_demo=False)
    label = fund.target_return_label
    if fund.target_weekly_return_pct is not None:
        label = format_target_return_label(
            fund.target_weekly_return_pct,
            fund.target_monthly_return_pct,
        )
    return schemas.FundResponse(
        id=fund.id,
        name=fund.name,
        description=fund.description,
        mandate_id=fund.mandate.id if fund.mandate else None,
        risk_label=fund.risk_label,
        target_return_label=label,
        target_weekly_return_pct=fund.target_weekly_return_pct,
        target_monthly_return_pct=fund.target_monthly_return_pct,
        actual_weekly_return_pct=display["actual_weekly_return_pct"],
        actual_monthly_return_pct=display["actual_monthly_return_pct"],
        actual_total_return_pct=display["actual_total_return_pct"],
        total_aum=display["total_aum"],
        portfolio_count=display["portfolio_count"],
        data_provenance=display["data_provenance"],
        allocation_policy=fund.allocation_policy,
        is_active=fund.is_active,
        asset_universe=universe,
    )


@router.get("/", response_model=List[schemas.FundResponse])
def list_funds(
    db: Session = Depends(get_db),
    current_user: domain.User = Depends(get_current_user),
):
    funds = (
        db.query(domain.Fund)
        .filter(domain.Fund.is_active == True)
        .options(joinedload(domain.Fund.asset_universe).joinedload(domain.FundAssetUniverse.asset),
                 joinedload(domain.Fund.mandate))
        .order_by(domain.Fund.pk_id)
        .all()
    )
    return [_to_fund_response(f, db) for f in funds]


@router.get("/{fund_id}", response_model=schemas.FundResponse)
def get_fund(
    fund_id: str,
    db: Session = Depends(get_db),
    current_user: domain.User = Depends(get_current_user),
):
    fund = (
        db.query(domain.Fund)
        .filter(domain.Fund.id == fund_id)
        .options(joinedload(domain.Fund.asset_universe).joinedload(domain.FundAssetUniverse.asset),
                 joinedload(domain.Fund.mandate))
        .first()
    )
    if not fund:
        raise HTTPException(status_code=404, detail="Fund not found.")
    return _to_fund_response(fund, db)


@router.get("/{fund_id}/institutional")
def get_fund_institutional_analytics(
    fund_id: str,
    db: Session = Depends(get_db),
    current_user: domain.User = Depends(get_current_user),
):
    fund = db.query(domain.Fund).filter(domain.Fund.id == fund_id).first()
    if not fund:
        raise HTTPException(status_code=404, detail="Fund not found.")
    from app.engines.global_risk_engine import GlobalRiskEngine
    analytics = compute_institutional_analytics(db, fund)
    analytics["risk_score"] = GlobalRiskEngine(db).assess().global_risk_score
    return analytics


@router.post("/{fund_id}/invest", response_model=schemas.PortfolioResponse, status_code=status.HTTP_201_CREATED)
def invest_in_fund(
    fund_id: str,
    body: schemas.FundInvestRequest,
    db: Session = Depends(get_db),
    current_user: domain.User = Depends(get_current_user),
):
    """Client picks a Fund/mandate and deposits capital. Creates an auto-managed
    portfolio and an initial AI allocation. This replaces manual strategy assignment
    for clients."""
    fund = db.query(domain.Fund).filter(domain.Fund.id == fund_id, domain.Fund.is_active == True).first()
    if not fund:
        raise HTTPException(status_code=404, detail="Fund not found or inactive.")
    if not fund.mandate_pk_id:
        raise HTTPException(status_code=400, detail="Fund has no mandate configured.")

    portfolio_id = body.portfolio_id or f"AIF-{fund.id}-{uuid.uuid4().hex[:5].upper()}"
    if db.query(domain.Portfolio).filter(domain.Portfolio.id == portfolio_id).first():
        raise HTTPException(status_code=400, detail="Portfolio with this ID already exists.")

    portfolio = domain.Portfolio(
        id=portfolio_id,
        user_id=current_user.id,
        mandate_pk_id=fund.mandate_pk_id,
        fund_pk_id=fund.pk_id,
        auto_managed=True,
        total_equity=body.amount,
        available_margin=body.amount,
        principal=body.amount,
    )
    db.add(portfolio)
    db.flush()

    db.add(domain.EquityCurve(portfolio_id=portfolio.pk_id, equity=portfolio.total_equity))
    create_audit_log(
        db, action_type="FUND_INVEST",
        description=f"{current_user.email} invested ${body.amount:,.2f} into {fund.name} ({fund.id}).",
        metadata_json={"portfolio_id": portfolio_id, "fund": fund.id, "amount": body.amount},
    )
    db.commit()
    db.refresh(portfolio)

    # Produce an initial target allocation immediately so the client sees their plan.
    try:
        global_state = MacroIntelligenceEngine(db).latest()
        AllocationEngine(db).rebalance_portfolio(portfolio, trigger="INITIAL", global_state=global_state)
        db.refresh(portfolio)
    except Exception:
        db.rollback()  # allocation can be retried by the scheduler; investment still stands

    return portfolio
