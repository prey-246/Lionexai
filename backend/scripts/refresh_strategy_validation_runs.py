"""
Recompute and persist validated_strategy_runs with fixed simulation engine.

Fixes stale rows where final_equity stayed at 100000 due to fee-aware sizing bug.

Usage:
  python scripts/refresh_strategy_validation_runs.py --dry-run
  python scripts/refresh_strategy_validation_runs.py --confirm
  python scripts/refresh_strategy_validation_runs.py --confirm --delete-stale
"""
from __future__ import annotations

import argparse
import logging
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.models import domain
from app.validation.real_strategy_validation import RealStrategyValidator

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("refresh_strategy_runs")


def _is_stale(row: domain.ValidatedStrategyRun) -> bool:
    m = row.metrics or {}
    fe = float(m.get("final_equity") or 0)
    total = float(m.get("total_return_pct") or 0)
    sharpe = abs(float(m.get("sharpe_ratio") or 0))
    if sharpe > 1000:
        return True
    if row.validation_type == "BACKTEST" and fe == 100_000.0 and total == 0.0 and int(m.get("total_trades") or 0) > 0:
        return True
    return False


def refresh(*, dry_run: bool = True, delete_stale: bool = False) -> None:
    db = SessionLocal()
    try:
        validator = RealStrategyValidator(db)
        rows = db.query(domain.ValidatedStrategyRun).order_by(domain.ValidatedStrategyRun.created_at.asc()).all()
        stale = [r for r in rows if _is_stale(r)]
        logger.info("Total runs: %d, stale: %d", len(rows), len(stale))

        if delete_stale and not dry_run:
            for row in stale:
                db.delete(row)
            db.commit()
            logger.info("Deleted %d stale runs", len(stale))

        # Always refresh all runs (or only stale when not deleting)
        targets = rows if not delete_stale else stale
        updated = 0
        created = 0
        for row in list(targets):
            vt = (row.validation_type or "BACKTEST").upper()
            try:
                if vt == "WALK_FORWARD":
                    result = validator.run_walk_forward(row.symbol, row.strategy_key)
                elif vt == "MONTE_CARLO":
                    result = validator.run_monte_carlo(row.symbol, row.strategy_key)
                else:
                    result = validator.run_single_asset_backtest(row.symbol, row.strategy_key)
            except Exception as e:
                logger.warning("Skip %s %s %s: %s", row.strategy_key, row.symbol, vt, e)
                continue

            if dry_run:
                logger.info(
                    "Would refresh %s %s %s -> final=%s total=%s sharpe=%s",
                    row.strategy_key, row.symbol, vt,
                    result.metrics.get("final_equity"),
                    result.metrics.get("total_return_pct"),
                    result.metrics.get("sharpe_ratio"),
                )
            else:
                row.metrics = result.metrics
                row.period_start = result.period_start
                row.period_end = result.period_end
                row.equity_curve = result.equity_curve
                updated += 1

        if not dry_run:
            db.commit()
            logger.info("Updated %d runs", updated)
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--confirm", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--delete-stale", action="store_true", help="Remove stale rows then refresh remaining")
    args = parser.parse_args()
    dry = not args.confirm
    refresh(dry_run=dry, delete_stale=args.delete_stale)
