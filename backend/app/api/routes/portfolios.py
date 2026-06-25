from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from app.core.database import get_db
from app.models import schemas, domain
from app.api.deps import get_current_user, require_role
from app.services.portfolio_nav import current_weight_pct
from app.services.validated_portfolio_service import (
    is_validated_portfolio,
    validated_portfolio_stats,
    validated_allocation_weight,
)
from app.services.audit_service import create_audit_log

router = APIRouter()

def _enrich_settlement(row: domain.ClientSettlement) -> schemas.ClientSettlementResponse:
    bd = row.breakdown or {}
    routed = bd.get("routed") or {}
    lnx = float(routed.get("LNX_INDEX") or 0)
    return schemas.ClientSettlementResponse(
        id=row.id,
        portfolio_id=row.portfolio_id,
        period_start=row.period_start,
        period_end=row.period_end,
        iso_week_key=row.iso_week_key,
        opening_equity=row.opening_equity,
        closing_marked_equity=row.closing_marked_equity,
        period_pnl=row.period_pnl,
        target_return_pct=row.target_return_pct,
        client_entitlement=row.client_entitlement,
        excess_routed=row.excess_routed,
        shortfall_topup=row.shortfall_topup,
        uncovered=row.uncovered,
        status=row.status,
        breakdown=row.breakdown,
        created_at=row.created_at,
        starting_nav=row.opening_equity,
        trading_pnl=row.period_pnl,
        target_yield=row.client_entitlement,
        treasury_routed=row.excess_routed,
        shortfall_topups=row.shortfall_topup,
        lnx_contribution=round(lnx, 2),
    )

@router.post("/", response_model=schemas.PortfolioResponse, status_code=status.HTTP_201_CREATED)
def create_portfolio(
    portfolio_in: schemas.PortfolioCreate,
    db: Session = Depends(get_db),
    current_user: domain.User = Depends(get_current_user)
):
    """
    Create a new portfolio for the current user.
    """
    db_portfolio = db.query(domain.Portfolio).filter(domain.Portfolio.id == portfolio_in.id).first()
    if db_portfolio:
        raise HTTPException(status_code=400, detail="Portfolio with this ID already exists")

    mandate = db.query(domain.Mandate).filter(domain.Mandate.pk_id == portfolio_in.mandate_pk_id).first()
    if not mandate:
        raise HTTPException(status_code=404, detail="Mandate not found")

    new_portfolio = domain.Portfolio(
        id=portfolio_in.id,
        user_id=current_user.id,
        mandate_pk_id=portfolio_in.mandate_pk_id,
        total_equity=portfolio_in.total_equity,
        available_margin=portfolio_in.total_equity,
    )
    db.add(new_portfolio)
    db.flush() # Ensure the new_portfolio.pk_id is generated
    
    # Save the initial equity curve point
    initial_curve = domain.EquityCurve(
        portfolio_id=new_portfolio.pk_id,
        equity=new_portfolio.total_equity
    )
    db.add(initial_curve)
    
    create_audit_log(
        db,
        action_type="PORTFOLIO_CREATE",
        description=f"User '{current_user.email}' created portfolio '{new_portfolio.id}'.",
        metadata_json={"portfolio_id": new_portfolio.id, "user_id": current_user.id}
    )
    
    db.commit()
    # Eagerly load relationships for the response
    db.refresh(new_portfolio)
    return new_portfolio

@router.get("", response_model=List[schemas.PortfolioResponse], include_in_schema=False)
def list_portfolios_no_slash(
    db: Session = Depends(get_db),
    current_user: domain.User = Depends(get_current_user),
):
    return list_portfolios(db=db, current_user=current_user)


@router.get("/", response_model=List[schemas.PortfolioResponse])
def list_portfolios(
    db: Session = Depends(get_db),
    current_user: domain.User = Depends(get_current_user)
):
    """
    List all portfolios for the current user, including their full risk context.
    """
    query = db.query(domain.Portfolio)
    if current_user.role_tier == "client":
        query = query.filter(domain.Portfolio.user_id == current_user.id)
        
    portfolios = query.options(
        # Eager load relationships to prevent N+1 query problem
        joinedload(domain.Portfolio.mandate),
        joinedload(domain.Portfolio.trades)
    ).order_by(domain.Portfolio.id).all()
    return portfolios

@router.get("/summary", response_model=schemas.PortfolioSummary)
def get_portfolio_summary(
    db: Session = Depends(get_db),
    current_user: domain.User = Depends(get_current_user)
):
    """
    Get a summary of all portfolios for the current user.
    """
    query = db.query(domain.Portfolio)
    if current_user.role_tier == "client":
        query = query.filter(domain.Portfolio.user_id == current_user.id)
        
    portfolios = query.all()
    
    if not portfolios:
        return schemas.PortfolioSummary(
            portfolio_count=0, total_equity=0, total_pnl=0, overall_win_rate_pct=0
        )

    total_equity = sum(p.total_equity for p in portfolios)
    
    portfolio_pk_ids = [p.pk_id for p in portfolios]
    total_pnl = db.query(func.sum(domain.Trade.pnl)).filter(
        domain.Trade.portfolio_id.in_(portfolio_pk_ids), domain.Trade.status == 'CLOSED'
    ).scalar() or 0

    total_trades = db.query(func.count(domain.Trade.id)).filter(
        domain.Trade.portfolio_id.in_(portfolio_pk_ids), domain.Trade.status == 'CLOSED'
    ).scalar() or 0

    winning_trades = db.query(func.count(domain.Trade.id)).filter(
        domain.Trade.portfolio_id.in_(portfolio_pk_ids), domain.Trade.status == 'CLOSED', domain.Trade.pnl > 0
    ).scalar() or 0

    win_rate = round((winning_trades / total_trades * 100), 2) if total_trades > 0 else 0.0
    
    # Calculate Best and Worst Portfolios by PNL
    portfolio_pnls = {p.pk_id: 0.0 for p in portfolios}
    pnl_by_portfolio = db.query(
        domain.Trade.portfolio_id, func.sum(domain.Trade.pnl)
    ).filter(
        domain.Trade.portfolio_id.in_(portfolio_pk_ids), 
        domain.Trade.status == 'CLOSED'
    ).group_by(domain.Trade.portfolio_id).all()

    for pk_id, pnl in pnl_by_portfolio:
        if pnl is not None:
            portfolio_pnls[pk_id] = pnl

    best_pk = max(portfolio_pnls, key=portfolio_pnls.get) if portfolio_pnls else None
    worst_pk = min(portfolio_pnls, key=portfolio_pnls.get) if portfolio_pnls else None
    pk_to_id = {p.pk_id: p.id for p in portfolios}

    return schemas.PortfolioSummary(
        portfolio_count=len(portfolios),
        total_equity=total_equity,
        total_pnl=total_pnl,
        overall_win_rate_pct=win_rate,
        best_performing_id=pk_to_id.get(best_pk) if best_pk else None,
        worst_performing_id=pk_to_id.get(worst_pk) if worst_pk else None
    )

@router.get("/{portfolio_id}", response_model=schemas.PortfolioResponse)
def get_portfolio(
    portfolio_id: str,
    db: Session = Depends(get_db),
    current_user: domain.User = Depends(get_current_user)
):
    """
    Get a single portfolio by ID, including its full risk context.
    """
    query = db.query(domain.Portfolio).filter(domain.Portfolio.id == portfolio_id)
    if current_user.role_tier == "client":
        query = query.filter(domain.Portfolio.user_id == current_user.id)
        
    portfolio = query.options(
        # Eager load relationships to prevent N+1 query problem
        joinedload(domain.Portfolio.mandate),
        joinedload(domain.Portfolio.trades)
    ).first()

    if not portfolio:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")
    
    return portfolio

@router.delete("/{portfolio_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_portfolio(
    portfolio_id: str,
    db: Session = Depends(get_db),
    current_user: domain.User = Depends(get_current_user)
):
    """
    Delete a portfolio.
    """
    query = db.query(domain.Portfolio).filter(domain.Portfolio.id == portfolio_id)
    if current_user.role_tier == "client":
        query = query.filter(domain.Portfolio.user_id == current_user.id)
        
    portfolio = query.first()

    if not portfolio:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")

    create_audit_log(
        db,
        action_type="PORTFOLIO_DELETE",
        description=f"User '{current_user.email}' deleted portfolio '{portfolio.id}'.",
        metadata_json={"portfolio_id": portfolio.id, "user_id": current_user.id}
    )

    db.delete(portfolio)
    db.commit()
    return

@router.get("/{portfolio_id}/stats", response_model=schemas.PortfolioStats)
def get_portfolio_stats(portfolio_id: str, db: Session = Depends(get_db), current_user: domain.User = Depends(get_current_user)):
    query = db.query(domain.Portfolio).filter(domain.Portfolio.id == portfolio_id)
    if current_user.role_tier == "client":
        query = query.filter(domain.Portfolio.user_id == current_user.id)
    portfolio = query.first()
    if not portfolio: raise HTTPException(status_code=404, detail="Portfolio not found")

    if is_validated_portfolio(portfolio):
        return schemas.PortfolioStats(**validated_portfolio_stats(db, portfolio))

    trades = db.query(domain.Trade).filter(domain.Trade.portfolio_id == portfolio.pk_id, domain.Trade.status == 'CLOSED').all()
    
    total_trades = len(trades)
    winning_trades = len([t for t in trades if t.pnl and t.pnl > 0])
    losing_trades = len([t for t in trades if t.pnl and t.pnl < 0])
    total_pnl = sum(t.pnl for t in trades if t.pnl is not None)
    
    win_rate = round((winning_trades / total_trades * 100), 2) if total_trades > 0 else 0.0
    avg_pnl = round((total_pnl / total_trades), 2) if total_trades > 0 else 0.0
    pnl_values = [t.pnl for t in trades if t.pnl is not None]
    best_trade = max(pnl_values, default=0.0)
    worst_trade = min(pnl_values, default=0.0)

    return schemas.PortfolioStats(
        total_trades=total_trades, winning_trades=winning_trades, losing_trades=losing_trades,
        win_rate_pct=win_rate, total_pnl=total_pnl, avg_pnl_per_trade=avg_pnl,
        best_trade_pnl=best_trade, worst_trade_pnl=worst_trade
    )

@router.get("/{portfolio_id}/trades", response_model=List[schemas.Trade])
def get_portfolio_trades(portfolio_id: str, status: str = None, db: Session = Depends(get_db), current_user: domain.User = Depends(get_current_user)):
    query = db.query(domain.Portfolio).filter(domain.Portfolio.id == portfolio_id)
    if current_user.role_tier == "client":
        query = query.filter(domain.Portfolio.user_id == current_user.id)
    portfolio = query.first()
    if not portfolio: raise HTTPException(status_code=404, detail="Portfolio not found")

    query = db.query(domain.Trade).filter(domain.Trade.portfolio_id == portfolio.pk_id)
    if status: query = query.filter(domain.Trade.status == status)
    elif is_validated_portfolio(portfolio):
        query = query.filter(domain.Trade.trade_source == "VALIDATED_HISTORICAL")
    return query.order_by(domain.Trade.created_at.desc()).limit(50).all()

@router.get("/{portfolio_id}/risk-events", response_model=List[schemas.RiskEvent])
def get_portfolio_risk_events(portfolio_id: str, limit: int = 50, db: Session = Depends(get_db), current_user: domain.User = Depends(get_current_user)):
    query = db.query(domain.Portfolio).filter(domain.Portfolio.id == portfolio_id)
    if current_user.role_tier == "client":
        query = query.filter(domain.Portfolio.user_id == current_user.id)
    portfolio = query.first()
    if not portfolio: raise HTTPException(status_code=404, detail="Portfolio not found")
    
    return db.query(domain.RiskEvent).filter(domain.RiskEvent.portfolio_id == portfolio.pk_id).order_by(domain.RiskEvent.triggered_at.desc()).limit(limit).all()

@router.get("/{portfolio_id}/equity-curve")
def get_portfolio_equity_curve(portfolio_id: str, limit: int = 100, db: Session = Depends(get_db), current_user: domain.User = Depends(get_current_user)):
    query = db.query(domain.Portfolio).filter(domain.Portfolio.id == portfolio_id)
    if current_user.role_tier == "client":
        query = query.filter(domain.Portfolio.user_id == current_user.id)
    portfolio = query.first()
    if not portfolio: raise HTTPException(status_code=404, detail="Portfolio not found")

    curves = db.query(domain.EquityCurve).filter(domain.EquityCurve.portfolio_id == portfolio.pk_id).order_by(domain.EquityCurve.timestamp.asc())
    if not is_validated_portfolio(portfolio):
        curves = curves.limit(limit)
    curves = curves.all()
    
    # AUTO-HEAL: If the portfolio is missing historical curve data, automatically generate a baseline
    if not curves:
        baseline = domain.EquityCurve(portfolio_id=portfolio.pk_id, equity=portfolio.total_equity)
        db.add(baseline)
        db.commit()
        db.refresh(baseline)
        curves = [baseline]
        
    return [{"timestamp": c.timestamp, "equity": float(c.equity or 0.0), "drawdown_pct": 0.0} for c in curves]


@router.get("/{portfolio_id}/allocations", response_model=List[schemas.AllocationItem])
def get_portfolio_allocations(portfolio_id: str, db: Session = Depends(get_db), current_user: domain.User = Depends(get_current_user)):
    """Target vs actual weights for an auto-managed portfolio (Phase 4 transparency)."""
    query = db.query(domain.Portfolio).filter(domain.Portfolio.id == portfolio_id)
    if current_user.role_tier == "client":
        query = query.filter(domain.Portfolio.user_id == current_user.id)
    portfolio = query.first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    rows = db.query(domain.PortfolioAllocation).options(
        joinedload(domain.PortfolioAllocation.asset)
    ).filter(
        domain.PortfolioAllocation.portfolio_id == portfolio.pk_id
    ).all()
    if not rows:
        return []

    # Use persisted weights for fast reads; optional live recompute only when bars exist
    out = []
    validated = is_validated_portfolio(portfolio)
    for a in rows:
        sym = a.asset.symbol if a.asset else "?"
        if validated:
            live_weight = validated_allocation_weight(a)
        else:
            live_weight = a.current_weight_pct
            if live_weight is None or live_weight == 0:
                live_weight = current_weight_pct(db, portfolio, sym)
        out.append(schemas.AllocationItem(
            symbol=sym,
            display_name=a.asset.display_name if a.asset else None,
            asset_class=a.asset.asset_class if a.asset else None,
            target_weight_pct=a.target_weight_pct,
            current_weight_pct=live_weight,
            updated_at=a.updated_at,
        ))
    out.sort(key=lambda x: x.target_weight_pct, reverse=True)
    return out


@router.get("/{portfolio_id}/rebalances", response_model=List[schemas.RebalanceEventResponse])
def get_portfolio_rebalances(portfolio_id: str, limit: int = 20, db: Session = Depends(get_db), current_user: domain.User = Depends(get_current_user)):
    """Recent allocation/rebalance decisions for an auto-managed portfolio."""
    query = db.query(domain.Portfolio).filter(domain.Portfolio.id == portfolio_id)
    if current_user.role_tier == "client":
        query = query.filter(domain.Portfolio.user_id == current_user.id)
    portfolio = query.first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    rows = db.query(domain.RebalanceEvent).filter(
        domain.RebalanceEvent.portfolio_id == portfolio.pk_id
    ).order_by(domain.RebalanceEvent.created_at.desc()).limit(limit * 5 if is_validated_portfolio(portfolio) else limit).all()
    if is_validated_portfolio(portfolio):
        return _dedupe_rebalances(rows, limit)
    return rows


def _dedupe_rebalances(rows: list[domain.RebalanceEvent], max_items: int) -> list[domain.RebalanceEvent]:
    seen: set[str] = set()
    out: list[domain.RebalanceEvent] = []
    for row in rows:
        day = row.created_at.date().isoformat() if row.created_at else row.id
        key = f"{day}:{row.regime}:{row.trigger}"
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
        if len(out) >= max_items:
            break
    return out


@router.get("/{portfolio_id}/settlements", response_model=List[schemas.ClientSettlementResponse])
def get_portfolio_settlements(portfolio_id: str, limit: int = 20, db: Session = Depends(get_db), current_user: domain.User = Depends(get_current_user)):
    """Weekly settlement history: client entitlement, excess routed to treasury, top-ups."""
    query = db.query(domain.Portfolio).filter(domain.Portfolio.id == portfolio_id)
    if current_user.role_tier == "client":
        query = query.filter(domain.Portfolio.user_id == current_user.id)
    portfolio = query.first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    rows = db.query(domain.ClientSettlement).filter(
        domain.ClientSettlement.portfolio_id == portfolio.pk_id
    ).order_by(domain.ClientSettlement.created_at.desc()).limit(limit).all()
    return [_enrich_settlement(r) for r in rows]