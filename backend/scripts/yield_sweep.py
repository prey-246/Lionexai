import sys
import os
import logging
from sqlalchemy.sql import func

# Ensure backend modules can be imported
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.models.domain import Trade, TreasuryPool, TreasuryTransaction

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def perform_yield_sweep():
    """
    Stateless yield sweep script.
    Calculates 10% of all historical winning PnL across the platform.
    Subtracts any yield already swept into the ledger.
    Sweeps the remaining difference into the YIELD treasury pool.
    """
    db = SessionLocal()
    try:
        # 1. Calculate total gross profit across all closed winning trades
        total_winning_pnl = db.query(func.sum(Trade.pnl)).filter(
            Trade.status == 'CLOSED',
            Trade.pnl > 0
        ).scalar() or 0.0

        target_yield = total_winning_pnl * 0.10

        # 2. Find the YIELD pool and calculate what has already been swept
        yield_pool = db.query(TreasuryPool).filter(TreasuryPool.id == 'YIELD').first()
        if not yield_pool:
            logger.warning("YIELD pool not found. Skipping sweep until Treasury is seeded.")
            return 0.0

        already_swept = db.query(func.sum(TreasuryTransaction.amount)).filter(
            TreasuryTransaction.pool_pk_id == yield_pool.pk_id,
            TreasuryTransaction.transaction_type == 'YIELD_SWEEP'
        ).scalar() or 0.0

        # 3. Calculate amount to sweep and execute ledger updates
        amount_to_sweep = target_yield - already_swept

        if amount_to_sweep > 0.01:
            logger.info(f"Sweeping ${amount_to_sweep:,.2f} into the YIELD pool.")
            yield_pool.balance += amount_to_sweep
            sweep_tx = TreasuryTransaction(pool_pk_id=yield_pool.pk_id, amount=amount_to_sweep, transaction_type="YIELD_SWEEP", description="Automated 10% platform yield sweep from profitable trades.")
            db.add(sweep_tx)
            db.commit()
            return amount_to_sweep
            
        return 0.0
    except Exception as e:
        logger.error(f"Failed to perform yield sweep: {e}")
        return 0.0
    finally:
        db.close()

if __name__ == "__main__":
    perform_yield_sweep()