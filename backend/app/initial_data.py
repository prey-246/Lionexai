from sqlalchemy.orm import Session
from app.models import domain

def seed_db(db: Session):
    """
    Seeds the database with standardized risk mandates.
    This function is idempotent and will not create duplicates.
    """
    mandates_to_seed = [
        {
            "id": "PRESERVE",
            "name": "Capital Preservation",
            "max_leverage": 1.0,
            "max_drawdown_pct": 5.0,
            "daily_loss_limit_pct": 2.0,
            "allowed_assets": ["BTC/USDT", "ETH/USDT"],
        },
        {
            "id": "BALANCE",
            "name": "Balanced Growth",
            "max_leverage": 3.0,
            "max_drawdown_pct": 10.0,
            "daily_loss_limit_pct": 4.0,
            "allowed_assets": ["BTC/USDT", "ETH/USDT", "SOL/USDT"],
        },
        {
            "id": "ALPHA",
            "name": "Aggressive Growth",
            "max_leverage": 10.0,
            "max_drawdown_pct": 25.0,
            "daily_loss_limit_pct": 10.0,
            "allowed_assets": ["ALL"],
        },
    ]

    for mandate_data in mandates_to_seed:
        # Check if any version of this mandate ID already exists
        exists = db.query(domain.Mandate).filter(domain.Mandate.id == mandate_data["id"]).first()
        if not exists:
            new_mandate = domain.Mandate(**mandate_data, version=1, is_active=True)
            db.add(new_mandate)
    
    db.commit()
