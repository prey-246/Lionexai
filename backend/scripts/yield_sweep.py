import sys
import os
import logging
from sqlalchemy.sql import func

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.models.domain import Trade, TreasuryPool, TreasuryTransaction
from app.services.audit_service import create_audit_log

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def perform_yield_sweep(db=None, user_id: str | None = None):
    """
    Legacy platform-wide yield sweep for non-auto-managed portfolios.
    Calculates 10% of all historical winning PnL, credits YIELD pool.
    Auto-managed portfolios use SettlementEngine instead.
    """
    own_session = db is None
    if own_session:
        db = SessionLocal()
    try:
        total_winning_pnl = db.query(func.sum(Trade.pnl)).filter(
            Trade.status == 'CLOSED',
            Trade.pnl > 0,
        ).scalar() or 0.0

        target_yield = total_winning_pnl * 0.10

        yield_pool = db.query(TreasuryPool).filter(TreasuryPool.id == 'YIELD').first()
        if not yield_pool:
            logger.warning("YIELD pool not found. Skipping sweep until Treasury is seeded.")
            return 0.0

        already_swept = db.query(func.sum(TreasuryTransaction.amount)).filter(
            TreasuryTransaction.pool_pk_id == yield_pool.pk_id,
            TreasuryTransaction.transaction_type == 'YIELD_SWEEP',
        ).scalar() or 0.0

        amount_to_sweep = target_yield - already_swept

        if amount_to_sweep > 0.01:
            logger.info("Sweeping $%.2f into the YIELD pool.", amount_to_sweep)
            yield_pool.balance += amount_to_sweep
            db.add(TreasuryTransaction(
                pool_pk_id=yield_pool.pk_id,
                amount=amount_to_sweep,
                transaction_type="YIELD_SWEEP",
                description="Automated 10% platform yield sweep from profitable trades (legacy).",
            ))
            create_audit_log(
                db,
                action_type="YIELD_SWEEP",
                description=f"Legacy yield sweep: ${amount_to_sweep:,.2f} to YIELD pool.",
                metadata_json={"amount": amount_to_sweep, "user_id": user_id},
            )
            db.commit()
            return amount_to_sweep

        return 0.0
    except Exception as e:
        logger.error("Failed to perform yield sweep: %s", e)
        if own_session:
            db.rollback()
        return 0.0
    finally:
        if own_session:
            db.close()


if __name__ == "__main__":
    perform_yield_sweep()
