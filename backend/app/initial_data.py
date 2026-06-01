import logging
from sqlalchemy.orm import Session

from app.models import domain
from app.core.security import get_password_hash

logger = logging.getLogger(__name__)

DEFAULT_MANDATES = [
    {"id": "PRESERVE", "name": "Capital Preservation", "max_leverage": 1.0, "max_drawdown_pct": 5.0, "daily_loss_limit_pct": 2.0, "kill_switch_active": False},
    {"id": "BALANCE", "name": "Balanced Growth", "max_leverage": 3.0, "max_drawdown_pct": 10.0, "daily_loss_limit_pct": 4.0, "kill_switch_active": False},
    {"id": "AGGRESSIVE", "name": "Aggressive Alpha", "max_leverage": 5.0, "max_drawdown_pct": 20.0, "daily_loss_limit_pct": 8.0, "kill_switch_active": False},
]

DEFAULT_USER_EMAIL = "user@example.com"
DEFAULT_USER_PASSWORD = "password"
DEFAULT_PORTFOLIO_ID = "port_sim_01"

def seed_db(db: Session) -> None:
    """
    Populates the database with initial data if it's empty.
    """
    # Check if mandates exist
    if db.query(domain.Mandate).first() is None:
        logger.info("Creating default risk mandates...")
        for mandate_data in DEFAULT_MANDATES:
            db_mandate = domain.Mandate(**mandate_data)
            db.add(db_mandate)
        db.commit()
        logger.info("Default risk mandates created.")

    # Check if default user exists
    user = db.query(domain.User).filter(domain.User.email == DEFAULT_USER_EMAIL).first()
    if not user:
        logger.info("Creating default user...")
        hashed_password = get_password_hash(DEFAULT_USER_PASSWORD)
        user = domain.User(email=DEFAULT_USER_EMAIL, hashed_password=hashed_password, is_active=True)
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info("Default user created.")

    # Check if default portfolio exists for the user
    portfolio = db.query(domain.Portfolio).filter(domain.Portfolio.id == DEFAULT_PORTFOLIO_ID).first()
    if not portfolio:
        logger.info("Creating default portfolio for user...")
        portfolio = domain.Portfolio(
            id=DEFAULT_PORTFOLIO_ID, user_id=user.id, mandate_id="BALANCE",
            total_equity=100000.0, available_margin=100000.0
        )
        db.add(portfolio)
        db.commit()
        logger.info("Default portfolio created.")