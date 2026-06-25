#!/usr/bin/env python3
"""Run Alpha Optimization Program phases."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.validation.alpha_optimization_engine import AlphaOptimizationEngine
from app.validation.validated_institutional_regenerator import ValidatedInstitutionalRegenerator

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("run_alpha_optimization")


def main():
    parser = argparse.ArgumentParser(description="LionexAI Alpha Optimization Program")
    parser.add_argument(
        "--phase",
        choices=["all", "verify", "strategy-matrix", "asset-analysis", "grid", "select-best", "regenerate"],
        default="all",
    )
    parser.add_argument("--fund", choices=["PRESERVE", "BALANCE", "ALPHA"], default=None)
    parser.add_argument("--bar-limit", type=int, default=2000)
    parser.add_argument("--no-persist", action="store_true")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        engine = AlphaOptimizationEngine(db, bar_limit=args.bar_limit)
        persist = not args.no_persist

        if args.phase == "verify":
            depth = engine.verify_history_depth()
            print(json.dumps(depth, indent=2))
            return

        if args.phase == "strategy-matrix":
            matrix = engine.run_strategy_matrix(persist=persist)
            logger.info("Strategy matrix: %d results", len(matrix))
            return

        if args.phase == "asset-analysis":
            analysis = engine.analyze_asset_universe()
            print(json.dumps(analysis, indent=2, default=str))
            return

        if args.phase == "grid":
            funds = [args.fund] if args.fund else ["PRESERVE", "BALANCE", "ALPHA"]
            for fid in funds:
                exps = engine.run_fund_grid(fid, persist=persist)
                top = sorted(
                    [e for e in exps if e.get("rank_score") is not None],
                    key=lambda x: x["rank_score"],
                    reverse=True,
                )[:5]
                logger.info("Top configs for %s:", fid)
                for t in top:
                    m = t.get("metrics", {})
                    logger.info(
                        "  %s rank=%.3f CAGR=%s Sharpe=%s DD=%s",
                        t.get("label"), t.get("rank_score"),
                        m.get("cagr_pct"), m.get("sharpe_ratio"), m.get("max_drawdown_pct"),
                    )
            return

        if args.phase == "select-best":
            funds = [args.fund] if args.fund else ["PRESERVE", "BALANCE", "ALPHA"]
            for fid in funds:
                sel = engine.select_best_per_fund(fid)
                logger.info("Selected %s: %s", fid, json.dumps(sel.best_metrics, default=str))
            return

        if args.phase == "regenerate":
            regen = ValidatedInstitutionalRegenerator(db).regenerate_all()
            print(json.dumps(regen, indent=2, default=str))
            return

        # phase == all
        result = engine.run_full_program(persist=persist)
        if result.get("status") == "blocked":
            logger.error("Blocked: %s", json.dumps(result, indent=2))
            sys.exit(1)

        logger.info("Selections: %s", json.dumps(result.get("selections"), indent=2))
        regen = ValidatedInstitutionalRegenerator(db).regenerate_all()
        logger.info("Regeneration complete: %s", json.dumps(regen, indent=2, default=str))

    finally:
        db.close()


if __name__ == "__main__":
    main()
