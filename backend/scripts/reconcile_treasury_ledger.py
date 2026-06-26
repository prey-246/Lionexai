"""
Rebuild treasury pool balances from operational ledger (baseline + transactions).

Fixes inflation caused by ValidatedInstitutionalRegenerator applying
total_routed * percentage (without /100) directly to pool balances.

Does NOT delete transactions or settlements. Preserves audit trail.

Usage:
  python scripts/reconcile_treasury_ledger.py --dry-run
  python scripts/reconcile_treasury_ledger.py --confirm
"""
from __future__ import annotations

import argparse
import logging
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.models import domain
from app.services.audit_service import create_audit_log
from app.services.treasury_verification_engine import OPERATIONAL_POOL_BASELINE

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("reconcile_treasury_ledger")


def reconcile(dry_run: bool = True) -> dict:
    db = SessionLocal()
    try:
        pools = db.query(domain.TreasuryPool).all()
        txs = db.query(domain.TreasuryTransaction).all()
        report: dict = {"pools": [], "before_nav": 0.0, "after_nav": 0.0}

        for pool in pools:
            baseline = OPERATIONAL_POOL_BASELINE.get(pool.id, 0.0)
            net_tx = sum(t.amount for t in txs if t.pool_pk_id == pool.pk_id)
            implied = round(baseline + net_tx, 2)
            before = round(pool.balance or 0, 2)
            gap = round(before - implied, 2)
            report["before_nav"] += before
            report["after_nav"] += implied
            report["pools"].append({
                "pool_id": pool.id,
                "before": before,
                "implied": implied,
                "gap": gap,
                "baseline": baseline,
                "net_transactions": round(net_tx, 2),
            })
            if not dry_run and abs(gap) > 0.01:
                pool.balance = implied
                logger.info("%s: %.2f -> %.2f (gap %.2f)", pool.id, before, implied, gap)

        if not dry_run:
            create_audit_log(
                db,
                action_type="TREASURY_LEDGER_RECONCILE",
                description="Treasury pool balances rebuilt from baseline + transaction ledger.",
                metadata_json={
                    "before_nav": round(report["before_nav"], 2),
                    "after_nav": round(report["after_nav"], 2),
                    "pools": report["pools"],
                },
            )
            db.commit()
        return report
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reconcile treasury pool balances to ledger")
    parser.add_argument("--confirm", action="store_true", help="Apply balance corrections")
    parser.add_argument("--dry-run", action="store_true", help="Report only (default)")
    args = parser.parse_args()
    dry = not args.confirm
    result = reconcile(dry_run=dry)
    print(f"Mode: {'DRY-RUN' if dry else 'APPLIED'}")
    print(f"NAV before: ${result['before_nav']:,.2f}")
    print(f"NAV after:  ${result['after_nav']:,.2f}")
    print(f"Gap:        ${result['after_nav'] - result['before_nav']:,.2f}")
    for p in result["pools"]:
        print(
            f"  {p['pool_id']:12} before={p['before']:>14,.2f} implied={p['implied']:>14,.2f} gap={p['gap']:>14,.2f}"
        )
