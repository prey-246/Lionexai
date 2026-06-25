from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel

from app.core.database import get_db
from app.models import domain
from app.api.deps import get_current_user, require_role
from app.services.audit_service import create_audit_log
from scripts.yield_sweep import perform_yield_sweep

# Local Pydantic Schemas for Treasury
class TreasuryPoolResponse(BaseModel):
    pk_id: int
    id: str
    name: str
    balance: float
    target_allocation_pct: float
    is_active: bool
    updated_at: datetime
    class Config:
        from_attributes = True

class TreasuryTransactionResponse(BaseModel):
    pk_id: int
    id: str
    pool_pk_id: int
    amount: float
    transaction_type: str
    reference_id: Optional[str] = None
    description: Optional[str] = None
    timestamp: datetime
    class Config:
        from_attributes = True

class TransferRequest(BaseModel):
    source_pool_id: str
    target_pool_id: str
    amount: float
    description: str


class TreasuryPoolAnalytics(BaseModel):
    pool_id: str
    name: str
    balance: float
    target_allocation_pct: float
    contributions: float
    withdrawals: float
    net_flow: float
    transaction_count: int

    class Config:
        from_attributes = True


router = APIRouter()

@router.post("/seed", response_model=List[TreasuryPoolResponse], dependencies=[Depends(require_role(["admin"]))])
def seed_treasury(db: Session = Depends(get_db), current_user: domain.User = Depends(get_current_user)):
    """Initializes the default institutional treasury pools."""
    defaults = [
        {"id": "RESERVE", "name": "Reserve Pool", "target_allocation_pct": 20.0, "balance": 1000000.0},
        {"id": "YIELD", "name": "Yield Generation Pool", "target_allocation_pct": 40.0, "balance": 0.0},
        {"id": "GROWTH", "name": "Ecosystem Growth Pool", "target_allocation_pct": 15.0, "balance": 250000.0},
        {"id": "OPERATIONS", "name": "Platform Operations", "target_allocation_pct": 10.0, "balance": 100000.0},
        {"id": "INSURANCE", "name": "Risk Insurance Fund", "target_allocation_pct": 5.0, "balance": 500000.0},
        {"id": "LNX_INDEX", "name": "LNX Index Pool", "target_allocation_pct": 10.0, "balance": 0.0},
    ]
    pools = []
    for d in defaults:
        pool = db.query(domain.TreasuryPool).filter(domain.TreasuryPool.id == d["id"]).first()
        if not pool:
            pool = domain.TreasuryPool(**d)
            db.add(pool)
        pools.append(pool)
    
    create_audit_log(db, action_type="TREASURY_SEEDED", description=f"Treasury seeded by {current_user.email}", metadata_json={"user_id": current_user.id})
    db.commit()
    for p in pools: db.refresh(p)
    return pools

@router.get("/pools/summary", dependencies=[Depends(require_role(["admin", "operator", "risk_manager", "client"]))])
def get_pools_summary(db: Session = Depends(get_db), current_user: domain.User = Depends(get_current_user)):
    """Read-only pool balances for client-facing pages (LNX, dashboard)."""
    pools = db.query(domain.TreasuryPool).order_by(domain.TreasuryPool.id).all()
    nav = sum(p.balance or 0 for p in pools)
    return {
        "total_nav": round(nav, 2),
        "pools": [
            {"id": p.id, "name": p.name, "balance": round(p.balance or 0, 2), "target_allocation_pct": p.target_allocation_pct}
            for p in pools
        ],
    }


@router.get("/pools", response_model=List[TreasuryPoolResponse], dependencies=[Depends(require_role(["admin", "operator", "risk_manager"]))])
def get_pools(db: Session = Depends(get_db), current_user: domain.User = Depends(get_current_user)):
    """Fetches all active treasury pools and their balances."""
    return db.query(domain.TreasuryPool).order_by(domain.TreasuryPool.target_allocation_pct.desc()).all()

@router.get("/pools/analytics", response_model=List[TreasuryPoolAnalytics], dependencies=[Depends(require_role(["admin", "operator", "risk_manager"]))])
def get_pool_analytics(db: Session = Depends(get_db), current_user: domain.User = Depends(get_current_user)):
    """Per-pool balance, contributions, withdrawals, and net flow from ledger."""
    pools = db.query(domain.TreasuryPool).order_by(domain.TreasuryPool.id).all()
    results = []
    for pool in pools:
        txs = db.query(domain.TreasuryTransaction).filter(domain.TreasuryTransaction.pool_pk_id == pool.pk_id).all()
        contributions = sum(t.amount for t in txs if t.amount > 0)
        withdrawals = sum(abs(t.amount) for t in txs if t.amount < 0)
        results.append(TreasuryPoolAnalytics(
            pool_id=pool.id,
            name=pool.name,
            balance=pool.balance,
            target_allocation_pct=pool.target_allocation_pct,
            contributions=round(contributions, 2),
            withdrawals=round(withdrawals, 2),
            net_flow=round(contributions - withdrawals, 2),
            transaction_count=len(txs),
        ))
    return results


@router.get("/transactions", response_model=List[TreasuryTransactionResponse], dependencies=[Depends(require_role(["admin", "operator", "risk_manager"]))])
def get_transactions(limit: int = 50, db: Session = Depends(get_db), current_user: domain.User = Depends(get_current_user)):
    """Fetches the immutable ledger of capital flowing in and out of the ecosystem."""
    return db.query(domain.TreasuryTransaction).order_by(domain.TreasuryTransaction.timestamp.desc()).limit(limit).all()

@router.post("/transfer", dependencies=[Depends(require_role(["admin"]))])
def transfer_capital(req: TransferRequest, db: Session = Depends(get_db), current_user: domain.User = Depends(get_current_user)):
    """Transfers capital between two Treasury pools and records the transactions."""
    if req.amount <= 0:
        raise HTTPException(status_code=400, detail="Transfer amount must be positive.")
    if req.source_pool_id == req.target_pool_id:
        raise HTTPException(status_code=400, detail="Source and target pools must be different.")
        
    source = db.query(domain.TreasuryPool).filter(domain.TreasuryPool.id == req.source_pool_id).first()
    target = db.query(domain.TreasuryPool).filter(domain.TreasuryPool.id == req.target_pool_id).first()
    
    if not source or not target:
        raise HTTPException(status_code=404, detail="One or both treasury pools not found.")
    if source.balance < req.amount:
        raise HTTPException(status_code=400, detail=f"Insufficient balance in {source.name}.")
        
    source.balance -= req.amount
    target.balance += req.amount
    
    tx_out = domain.TreasuryTransaction(pool_pk_id=source.pk_id, amount=-req.amount, transaction_type="INTERNAL_TRANSFER", description=f"Transfer to {target.id}: {req.description}")
    tx_in = domain.TreasuryTransaction(pool_pk_id=target.pk_id, amount=req.amount, transaction_type="INTERNAL_TRANSFER", description=f"Transfer from {source.id}: {req.description}")
    
    db.add_all([tx_out, tx_in])
    create_audit_log(db, action_type="TREASURY_TRANSFER", description=f"Admin {current_user.email} transferred ${req.amount:,.2f} from {source.id} to {target.id}.", metadata_json={"source": source.id, "target": target.id, "amount": req.amount, "user_id": current_user.id})
    db.commit()
    return {"status": "success", "message": "Transfer completed successfully."}

@router.post("/sweep", dependencies=[Depends(require_role(["admin"]))])
def trigger_yield_sweep(db: Session = Depends(get_db), current_user: domain.User = Depends(get_current_user)):
    """Manually triggers the yield sweep process (legacy non-auto-managed portfolios)."""
    swept_amount = perform_yield_sweep(db=db, user_id=current_user.id)
    if swept_amount > 0:
        return {"status": "success", "message": f"Successfully swept ${swept_amount:,.2f} to YIELD pool."}
    return {"status": "success", "message": "No new yield to sweep at this time."}


@router.get("/routing", dependencies=[Depends(require_role(["admin", "operator", "risk_manager", "client"]))])
def get_profit_routing_ledger(limit: int = 100, db: Session = Depends(get_db)):
    """Profit-routing and client top-up transactions from weekly settlements."""
    types = ("PROFIT_ROUTING", "CLIENT_TOPUP")
    rows = (
        db.query(domain.TreasuryTransaction, domain.TreasuryPool.id)
        .join(domain.TreasuryPool, domain.TreasuryPool.pk_id == domain.TreasuryTransaction.pool_pk_id)
        .filter(domain.TreasuryTransaction.transaction_type.in_(types))
        .order_by(domain.TreasuryTransaction.timestamp.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": tx.id,
            "pool_id": pool_id,
            "pool_pk_id": tx.pool_pk_id,
            "amount": tx.amount,
            "transaction_type": tx.transaction_type,
            "reference_id": tx.reference_id,
            "description": tx.description,
            "timestamp": tx.timestamp.isoformat(),
        }
        for tx, pool_id in rows
    ]