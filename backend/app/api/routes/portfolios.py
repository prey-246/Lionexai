from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.models.domain import Portfolio
from app.models.schemas import Portfolio as PortfolioSchema

router = APIRouter()

@router.get("/portfolios", response_model=List[PortfolioSchema], tags=["Portfolios"])
def get_all_portfolios(db: Session = Depends(get_db)):
    portfolios = db.query(Portfolio).all()
    return portfolios

@router.get("/portfolios/{portfolio_id}", response_model=PortfolioSchema, tags=["Portfolios"])
def get_portfolio_by_id(portfolio_id: str, db: Session = Depends(get_db)):
    portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return portfolio