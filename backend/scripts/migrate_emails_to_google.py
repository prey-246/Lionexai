"""One-off: replace @lionex.ai with @google.com in users and audit_logs."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text

from app.core.database import SessionLocal
from app.models import domain


def main():
    db = SessionLocal()
    try:
        before = [r[0] for r in db.query(domain.User.email).filter(domain.User.email.like("%@lionex.ai")).all()]
        print("users to update:", before)
        db.execute(
            text("UPDATE users SET email = REPLACE(email, '@lionex.ai', '@google.com') WHERE email LIKE '%@lionex.ai'")
        )
        db.execute(
            text(
                "UPDATE audit_logs SET description = REPLACE(description, '@lionex.ai', '@google.com') "
                "WHERE description LIKE '%@lionex.ai%'"
            )
        )
        db.commit()
        after = [r[0] for r in db.query(domain.User.email).order_by(domain.User.email).all()]
        print("users now:", after)
    finally:
        db.close()


if __name__ == "__main__":
    main()
