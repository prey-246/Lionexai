from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import domain, schemas
from app.api.deps import get_current_user
from app.engines.lnx_index import LNXIndexEngine, _treasury_nav, _aum, _reserve_ratio

router = APIRouter()


def _enrich(snap: domain.LNXIndexSnapshot, db: Session) -> schemas.LNXIndexResponse:
    week_ago = datetime.utcnow() - timedelta(days=7)
    month_ago = datetime.utcnow() - timedelta(days=30)
    past_week = (
        db.query(domain.LNXIndexSnapshot)
        .filter(domain.LNXIndexSnapshot.computed_at <= week_ago)
        .order_by(domain.LNXIndexSnapshot.computed_at.desc())
        .first()
    )
    past_month = (
        db.query(domain.LNXIndexSnapshot)
        .filter(domain.LNXIndexSnapshot.computed_at <= month_ago)
        .order_by(domain.LNXIndexSnapshot.computed_at.desc())
        .first()
    )
    w_chg = None
    m_chg = None
    if past_week:
        w_chg = round((snap.composite_index / past_week.composite_index - 1.0) * 100.0, 4) if past_week.composite_index else None
    if past_month:
        m_chg = round((snap.composite_index / past_month.composite_index - 1.0) * 100.0, 4) if past_month.composite_index else None
    tnav = _treasury_nav(db)
    aum = _aum(db)
    rr = _reserve_ratio(db, tnav)
    return schemas.LNXIndexResponse(
        nav=snap.nav,
        treasury_health=snap.treasury_health,
        strategy_performance=snap.strategy_performance,
        execution_quality=snap.execution_quality,
        aum_growth=snap.aum_growth,
        composite_index=snap.composite_index,
        computed_at=snap.computed_at,
        weekly_change_pct=w_chg,
        monthly_change_pct=m_chg,
        treasury_nav=round(tnav, 2),
        aum=round(aum, 2),
        reserve_ratio=round(rr, 2),
    )


@router.get("/index", response_model=Optional[schemas.LNXIndexResponse])
def get_lnx_index(db: Session = Depends(get_db), current_user: domain.User = Depends(get_current_user)):
    snap = LNXIndexEngine(db).latest()
    if not snap:
        snap = LNXIndexEngine(db).compute(store=True)
    return _enrich(snap, db)


@router.get("/history", response_model=List[schemas.LNXIndexResponse])
def get_lnx_history(limit: int = 90, db: Session = Depends(get_db), current_user: domain.User = Depends(get_current_user)):
    rows = LNXIndexEngine(db).history(limit=limit)
    return [
        schemas.LNXIndexResponse(
            nav=r.nav,
            treasury_health=r.treasury_health,
            strategy_performance=r.strategy_performance,
            execution_quality=r.execution_quality,
            aum_growth=r.aum_growth,
            composite_index=r.composite_index,
            computed_at=r.computed_at,
        )
        for r in reversed(rows)
    ]
