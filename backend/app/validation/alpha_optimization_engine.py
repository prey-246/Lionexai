"""Alpha optimization program — strategy matrix, grids, ensemble, selection."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from app.analytics import performance_engine as pe
from app.models import domain
from app.services import market_data_service
from app.validation.historical_fund_simulator import (
    HistoricalFundSimulator,
    SimulationConfig,
    MIN_OPTIMIZATION_BARS,
)
from app.validation.real_strategy_validation import RealStrategyValidator
from app.validation.strategy_overlay import STRATEGY_KEYS

logger = logging.getLogger("nexa.alpha_optimization")

FULL_UNIVERSE = [
    "BTC/USDT", "ETH/USDT", "SOL/USDT", "XAUUSD", "XAGUSD", "WTIUSD",
    "SPX", "NDX", "EURUSD", "GBPUSD",
]

RECOMMENDED_UNIVERSES: dict[str, list[str]] = {
    "PRESERVE": ["BTC/USDT", "XAUUSD", "XAGUSD", "WTIUSD"],
    "BALANCE": ["BTC/USDT", "SOL/USDT", "XAUUSD", "WTIUSD", "SPX", "GBPUSD"],
    "ALPHA": ["BTC/USDT", "SOL/USDT", "XAUUSD", "WTIUSD", "SPX", "GBPUSD", "XAGUSD"],
}

PORTFOLIO_METHODS = [
    "inverse_vol",
    "regime_momentum",
    "risk_parity",
    "relative_strength",
    "max_diversification",
]

REBALANCE_GRID = [
    (3, "calendar"),
    (7, "calendar"),
    (14, "calendar"),
    (30, "calendar"),
    (7, "regime_change"),
]

FUND_CASH_FLOORS: dict[str, list[float]] = {
    "PRESERVE": [15.0, 25.0],
    "BALANCE": [10.0, 20.0],
    "ALPHA": [5.0, 15.0],
}


@dataclass
class OptimizationSummary:
    fund_id: str
    best_run_id: str | None = None
    best_config: dict[str, Any] = field(default_factory=dict)
    best_metrics: dict[str, Any] = field(default_factory=dict)
    experiments_run: int = 0
    asset_analysis: dict[str, Any] = field(default_factory=dict)
    strategy_matrix_summary: list[dict] = field(default_factory=list)


def compute_rank_score(metrics: dict[str, Any], wf_penalty: float = 0.0) -> float:
    sharpe = float(metrics.get("sharpe_ratio") or 0)
    sortino = float(metrics.get("sortino_ratio") or 0)
    calmar = float(metrics.get("calmar_ratio") or 0)
    pf = float(metrics.get("profit_factor") or 1.0)
    dd = float(metrics.get("max_drawdown_pct") or 100.0)
    cagr = float(metrics.get("cagr_pct") or 0)
    dd_term = max(0.0, 1.0 - dd / 100.0)
    score = (
        0.35 * sharpe
        + 0.20 * sortino
        + 0.20 * calmar
        + 0.15 * min(pf, 3.0)
        + 0.10 * dd_term
    )
    if cagr < 0:
        score -= 0.5
    return round(score - wf_penalty, 4)


class AlphaOptimizationEngine:
    def __init__(self, db: Session, bar_limit: int = 2000):
        self.db = db
        self.bar_limit = bar_limit
        self.sim = HistoricalFundSimulator(db)
        self.validator = RealStrategyValidator(db)

    def verify_history_depth(self, symbols: list[str] | None = None) -> dict[str, Any]:
        syms = symbols or FULL_UNIVERSE
        panel, coverage = market_data_service.get_bars_panel(
            self.db, syms, limit=self.bar_limit, min_bars=60,
        )
        aligned = coverage.get("_aligned", {})
        rows = aligned.get("rows", len(panel))
        ok = rows >= MIN_OPTIMIZATION_BARS
        return {
            "aligned_rows": rows,
            "min_required": MIN_OPTIMIZATION_BARS,
            "sufficient": ok,
            "period_start": aligned.get("period_start"),
            "period_end": aligned.get("period_end"),
            "symbols": aligned.get("symbols", []),
        }

    def run_strategy_matrix(self, persist: bool = True) -> list[dict]:
        """Phase 2: independent strategy backtests per asset."""
        results: list[dict] = []
        for strat in STRATEGY_KEYS:
            for sym in FULL_UNIVERSE:
                try:
                    run = self.validator.run_single_asset_backtest(sym, strat, limit=self.bar_limit)
                    if persist:
                        self.validator.persist_run(run)
                    results.append({
                        "strategy": strat,
                        "symbol": sym,
                        "metrics": run.metrics,
                        "run_id": run.run_id,
                    })
                except Exception as e:
                    results.append({"strategy": strat, "symbol": sym, "error": str(e)})
        logger.info("Strategy matrix complete: %d runs", len(results))
        return results

    def analyze_asset_universe(self) -> dict[str, Any]:
        """Phase 4: per-asset buy-hold metrics and correlation."""
        panel, _ = market_data_service.get_bars_panel(
            self.db, FULL_UNIVERSE, limit=self.bar_limit, min_bars=MIN_OPTIMIZATION_BARS,
        )
        if panel.empty:
            return {"error": "insufficient data"}

        assets: list[dict] = []
        for sym in panel.columns:
            s = panel[sym].dropna()
            eq = pd.Series(s.values, index=pd.DatetimeIndex(panel.index[: len(s)]))
            rets = pe.daily_returns_from_equity(eq)
            assets.append({
                "symbol": sym,
                "total_return_pct": round((s.iloc[-1] / s.iloc[0] - 1) * 100, 2),
                "cagr_pct": pe.cagr_pct(eq),
                "sharpe_ratio": pe.sharpe_ratio(rets),
                "max_drawdown_pct": pe.max_drawdown_pct(eq),
            })

        corr = panel.pct_change().corr().round(3).to_dict()
        ranked = sorted(assets, key=lambda x: x.get("sharpe_ratio") or -999, reverse=True)
        remove = [
            a["symbol"] for a in assets
            if (a.get("cagr_pct") or 0) < 0 or (a.get("sharpe_ratio") or 0) < 0
        ]
        return {
            "assets": assets,
            "correlation": corr,
            "ranked_by_sharpe": [a["symbol"] for a in ranked],
            "remove_candidates": remove,
            "recommended_universes": RECOMMENDED_UNIVERSES,
        }

    def run_fund_grid(self, fund_id: str, persist: bool = True) -> list[dict]:
        """Phases 6–7: rebalance × method × cash floor grid with optional ensemble."""
        fund_id = fund_id.upper()
        symbols = RECOMMENDED_UNIVERSES.get(fund_id, FULL_UNIVERSE)
        experiments: list[dict] = []

        configs_to_test: list[SimulationConfig] = []
        for method in PORTFOLIO_METHODS:
            for freq, mode in REBALANCE_GRID:
                for cash in FUND_CASH_FLOORS.get(fund_id, [15.0]):
                    configs_to_test.append(SimulationConfig(
                        method=method,
                        rebalance_freq_days=freq,
                        rebalance_mode=mode,
                        cash_floor_pct=cash,
                        symbols=symbols,
                        regime_cash_escalation=(fund_id == "PRESERVE"),
                        experiment_type="GRID",
                        experiment_label=f"{method}_{freq}d_{mode}_cash{cash}",
                        validation_type="OPTIMIZATION_GRID",
                    ))
        # Ensemble + vol target variants
        for freq in (7, 14):
            configs_to_test.append(SimulationConfig(
                method="regime_momentum",
                rebalance_freq_days=freq,
                rebalance_mode="both",
                cash_floor_pct=FUND_CASH_FLOORS[fund_id][0],
                symbols=symbols,
                use_regime_v2=True,
                use_ensemble=True,
                vol_target_pct=12.0 if fund_id == "PRESERVE" else 18.0,
                regime_cash_escalation=(fund_id == "PRESERVE"),
                experiment_type="ENSEMBLE",
                experiment_label=f"ensemble_v2_vol{12 if fund_id == 'PRESERVE' else 18}_{freq}d",
                validation_type="OPTIMIZATION_ENSEMBLE",
            ))

        for cfg in configs_to_test:
            try:
                logger.info("Running %s / %s", fund_id, cfg.experiment_label)
                result = self.sim.run_fund_backtest(
                    fund_id,
                    bar_limit=self.bar_limit,
                    config=cfg,
                    min_aligned_bars=MIN_OPTIMIZATION_BARS,
                )
                wf_penalty = self._walk_forward_penalty(result)
                rank = compute_rank_score(result.metrics, wf_penalty)
                if persist:
                    self.sim.persist_run(result, rank_score=rank)
                experiments.append({
                    "run_id": result.run_id,
                    "label": cfg.experiment_label,
                    "rank_score": rank,
                    "metrics": result.metrics,
                    "config": cfg.to_dict(),
                })
            except Exception as e:
                experiments.append({"label": cfg.experiment_label, "error": str(e)})

        logger.info("Fund grid %s: %d experiments", fund_id, len(experiments))
        return experiments

    def _walk_forward_penalty(self, result) -> float:
        """Simple IS/OOS Sharpe decay penalty on last 25% holdout."""
        curve = result.equity_curve
        if len(curve) < 120:
            return 0.0
        split = int(len(curve) * 0.75)
        values = [p["value"] for p in curve]
        ts = pd.DatetimeIndex([pd.Timestamp(p["time"], unit="s") for p in curve])
        eq = pd.Series(values, index=ts)
        rets = pe.daily_returns_from_equity(eq)
        is_rets = rets.iloc[:split]
        oos_rets = rets.iloc[split:]
        is_sh = pe.sharpe_ratio(is_rets) or 0.0
        oos_sh = pe.sharpe_ratio(oos_rets) or 0.0
        if is_sh <= 0:
            return 0.2
        if oos_sh < 0.5 * is_sh:
            return 0.3
        return 0.0

    def select_best_per_fund(self, fund_id: str) -> OptimizationSummary:
        """Phase 9 selection: highest rank_score with positive CAGR."""
        fund_id = fund_id.upper()
        rows = (
            self.db.query(domain.ValidatedFundRun)
            .filter(
                domain.ValidatedFundRun.fund_id == fund_id,
                domain.ValidatedFundRun.validation_type.like("OPTIMIZATION%"),
            )
            .order_by(domain.ValidatedFundRun.rank_score.desc().nullslast())
            .all()
        )
        best = None
        for row in rows:
            m = row.metrics or {}
            if m.get("error"):
                continue
            if (m.get("cagr_pct") or 0) <= 0 and fund_id != "PRESERVE":
                continue
            if row.rank_score is not None:
                best = row
                break
        if not best and rows:
            best = rows[0]

        summary = OptimizationSummary(fund_id=fund_id, experiments_run=len(rows))
        if best:
            best.provenance = "SELECTED_BEST"
            self.db.commit()
            summary.best_run_id = best.id
            summary.best_config = best.experiment_config or best.allocation_policy_snapshot or {}
            summary.best_metrics = best.metrics or {}

            # Promote copy as primary validated run
            promoted = domain.ValidatedFundRun(
                id=f"vfr_best_{uuid.uuid4().hex[:10]}",
                fund_id=fund_id,
                validation_type="SELECTED_BEST",
                period_start=best.period_start,
                period_end=best.period_end,
                initial_capital=best.initial_capital,
                metrics={**(best.metrics or {}), "selected_from": best.id},
                equity_curve=best.equity_curve,
                rebalance_log=best.rebalance_log,
                allocation_policy_snapshot=best.allocation_policy_snapshot,
                data_coverage=best.data_coverage,
                provenance="VALIDATED_HISTORICAL",
                experiment_config=best.experiment_config,
                rank_score=best.rank_score,
            )
            self.db.add(promoted)
            self.db.commit()
            summary.best_run_id = promoted.id

        return summary

    def run_full_program(self, persist: bool = True) -> dict[str, Any]:
        depth = self.verify_history_depth()
        if not depth["sufficient"]:
            return {
                "status": "blocked",
                "reason": f"Need {MIN_OPTIMIZATION_BARS} aligned bars; have {depth['aligned_rows']}",
                "depth": depth,
            }

        strategy_matrix = self.run_strategy_matrix(persist=persist)
        asset_analysis = self.analyze_asset_universe()

        fund_results: dict[str, Any] = {}
        selections: dict[str, Any] = {}
        for fund_id in ("PRESERVE", "BALANCE", "ALPHA"):
            fund_results[fund_id] = self.run_fund_grid(fund_id, persist=persist)
            sel = self.select_best_per_fund(fund_id)
            selections[fund_id] = {
                "best_run_id": sel.best_run_id,
                "best_config": sel.best_config,
                "best_metrics": sel.best_metrics,
                "experiments_run": sel.experiments_run,
            }

        return {
            "status": "complete",
            "depth": depth,
            "strategy_matrix_count": len(strategy_matrix),
            "asset_analysis": asset_analysis,
            "fund_experiments": {k: len(v) for k, v in fund_results.items()},
            "selections": selections,
        }
