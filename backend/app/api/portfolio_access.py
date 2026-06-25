"""Shared portfolio access helpers for API routes."""

from sqlalchemy.orm import Session

from app.models import domain

STAFF_ROLES = frozenset({"admin", "operator", "risk_manager"})


def portfolio_for_user(db: Session, portfolio_id: str, user: domain.User) -> domain.Portfolio | None:
    """Clients see only their portfolios; staff can access any portfolio by id."""
    q = db.query(domain.Portfolio).filter(domain.Portfolio.id == portfolio_id)
    if user.role_tier not in STAFF_ROLES:
        q = q.filter(domain.Portfolio.user_id == user.id)
    return q.first()
