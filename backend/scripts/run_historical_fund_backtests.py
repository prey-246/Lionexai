#!/usr/bin/env python3
"""Run historical fund backtests for PRESERVE, BALANCE, and ALPHA on market_bars."""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.services.market_data_service import run_backfill
from app.validation.historical_fund_simulator import HistoricalFundSimulator


def main():
    parser = argparse.ArgumentParser(description="Historical fund backtests on market_bars")
    parser.add_argument("--backfill", action="store_true", help="Refresh market_bars before backtest")
    parser.add_argument("--limit", type=int, default=2000, help="Bar limit per symbol")
    parser.add_argument("--capital", type=float, default=1_000_000.0)
    parser.add_argument("--fund", type=str, default=None, help="Single fund id (default: all)")
    args = parser.parse_args()

    if args.backfill:
        print("Backfilling market_bars...")
        run_backfill(limit=args.limit)

    db = SessionLocal()
    try:
        sim = HistoricalFundSimulator(db)
        if args.fund:
            result = sim.run_fund_backtest(args.fund.upper(), args.capital, args.limit)
            row = sim.persist_run(result)
            print(json.dumps({"persisted_id": row.id, "metrics": result.metrics}, indent=2, default=str))
        else:
            results = sim.run_all_funds(args.capital, args.limit, persist=True)
            summary = []
            for r in results:
                summary.append({
                    "fund_id": r.fund_id,
                    "run_id": r.run_id,
                    "error": r.metrics.get("error"),
                    "cagr_pct": r.metrics.get("cagr_pct"),
                    "avg_monthly_return_pct": r.metrics.get("avg_monthly_return_pct"),
                    "max_drawdown_pct": r.metrics.get("max_drawdown_pct"),
                    "sharpe_ratio": r.metrics.get("sharpe_ratio"),
                    "alpha_20pct_supported": r.metrics.get("alpha_20pct_supported"),
                    "period_start": r.period_start,
                    "period_end": r.period_end,
                })
            print(json.dumps(summary, indent=2, default=str))
    finally:
        db.close()


if __name__ == "__main__":
    main()
