import os
import sys
import uuid
import logging
from passlib.context import CryptContext

# Setup path to allow importing the app module from the scripts directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.models.domain import User, Portfolio, Mandate

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password):
    return pwd_context.hash(password)

def seed_mock_data():
    """Seeds the database with mock users and portfolios for testing."""
    db = SessionLocal()
    try:
        logger.info("Seeding mock users...")
        
        users_to_create = [
            {"email": "operator1@google.com", "role_tier": "operator"},
            {"email": "operator2@google.com", "role_tier": "operator"},
            {"email": "risk1@google.com", "role_tier": "risk_manager"},
            {"email": "risk2@google.com", "role_tier": "risk_manager"},
            {"email": "client1@google.com", "role_tier": "client"},
            {"email": "client2@google.com", "role_tier": "client"},
        ]
        
        created_users = []
        for u in users_to_create:
            existing_user = db.query(User).filter(User.email == u["email"]).first()
            if not existing_user:
                new_user = User(
                    id=f"usr_{uuid.uuid4().hex[:12]}",
                    email=u["email"],
                    hashed_password=get_password_hash("password123"), # Default password for all mock users
                    is_active=True,
                    role_tier=u["role_tier"]
                )
                db.add(new_user)
                created_users.append(new_user)
            else:
                created_users.append(existing_user)
                
        db.commit()
        logger.info(f"Ensured {len(users_to_create)} mock users exist.")

        logger.info("Seeding mock portfolios for clients...")
        mandate = db.query(Mandate).filter(Mandate.is_active == True).first()
        if not mandate:
            logger.warning("No active mandates found! Run the seed-defaults API first. Skipping portfolio creation.")
            return

        client1 = next((u for u in created_users if u.email == "client1@google.com"), None)
        
        if client1 and not db.query(Portfolio).filter(Portfolio.user_id == client1.id).first():
            portfolios = [
                Portfolio(id=f"PORT-ALPHA-{uuid.uuid4().hex[:4].upper()}", user_id=client1.id, mandate_pk_id=mandate.pk_id, total_equity=150000.0, available_margin=150000.0),
                Portfolio(id=f"PORT-BETA-{uuid.uuid4().hex[:4].upper()}", user_id=client1.id, mandate_pk_id=mandate.pk_id, total_equity=50000.0, available_margin=50000.0)
            ]
            db.add_all(portfolios)
            db.commit()
            logger.info("Successfully seeded mock portfolios.")
        
    except Exception as e:
        logger.error(f"Failed to seed mock data: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_mock_data()