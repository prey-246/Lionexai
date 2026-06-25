"""Alpha 20% monthly evidence program — objective statistical evaluation."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.models import domain
from app.validation.real_strategy_validation import RealStrategyValidator
from app.services.live_validation_engine import compute_live_validation_metrics, PERIODS

logger = logging.getLogger("nexa.alpha_evidence")

VERDICT_SUPPORTED = "SUPPORTED"
VERDICT_PARTIAL = "PARTIALLY_SUPPORTED"
VERDICT_NOT = "NOT_SUPPORTED"


def _safe_avg(values: list) -> float | None:
    nums = [float(v) for v in values if v is not None and isinstance(v, (int, float))]
    return round(sum(nums) / len(nums), 2) if nums else None


class AlphaEvidenceService:
    def __init__(self, db: Session):
        self.db = db
        self.validator = RealStrategyValidator(db)

    def evaluate(self, target_monthly_pct: float = 20.0, fund_id: str = "ALPHA") -> dict[str, Any]:
        fund = self.db.query(domain.Fund).filter(domain.Fund.id == fund_id.upper()).first()
        if not fund:
            raise ValueError(f"Fund not found: {fund_id}")

        # Fund-level historical backtest (primary evidence)
        fund_run = (
            self.db.query(domain.ValidatedFundRun)
            .filter(domain.ValidatedFundRun.fund_id == fund_id.upper())
            .order_by(domain.ValidatedFundRun.created_at.desc())
            .first()
        )
        fund_backtest = None
        if fund_run and fund_run.metrics and not fund_run.metrics.get("error"):
            fund_backtest = {
                "run_id": fund_run.id,
                "avg_monthly_return_pct": fund_run.metrics.get("avg_monthly_return_pct"),
                "cagr_pct": fund_run.metrics.get("cagr_pct"),
                "max_drawdown_pct": fund_run.metrics.get("max_drawdown_pct"),
                "sharpe_ratio": fund_run.metrics.get("sharpe_ratio"),
                "meets_target_monthly": fund_run.metrics.get("meets_target_monthly"),
                "period_start": fund_run.period_start,
                "period_end": fund_run.period_end,
                "provenance": "VALIDATED_HISTORICAL",
            }

        # Single-asset strategy grid (supplementary)
        historical = self.validator.evaluate_alpha_monthly_target(fund_id, target_monthly_pct)

        # Walk-forward + Monte Carlo from latest runs
        runs = (
            self.db.query(domain.ValidatedStrategyRun)
            .filter(domain.ValidatedStrategyRun.validation_type.in_(("WALK_FORWARD", "MONTE_CARLO", "BACKTEST")))
            .order_by(domain.ValidatedStrategyRun.created_at.desc())
            .limit(20)
            .all()
        )
        wf_monthly = [
            r.metrics.get("avg_monthly_return_pct")
            for r in runs
            if r.validation_type == "WALK_FORWARD" and r.metrics
        ]
        mc_monthly = [
            r.metrics.get("p50_monthly_return_pct") or r.metrics.get("avg_monthly_return_pct")
            for r in runs
            if r.validation_type == "MONTE_CARLO" and r.metrics
        ]

        # Paper-live
        portfolios = (
            self.db.query(domain.Portfolio)
            .filter(domain.Portfolio.fund_pk_id == fund.pk_id, domain.Portfolio.auto_managed == True)
            .all()
        )
        paper_metrics = []
        for p in portfolios:
            paper_metrics.append(compute_live_validation_metrics(self.db, p, PERIODS["90D"]))
        paper_monthly = [m["monthly_return_pct"] for m in paper_metrics if m.get("monthly_return_pct") is not None]
        paper_prov = paper_metrics[0].get("provenance") if paper_metrics else "UNKNOWN"
        if paper_prov == "DEMO":
            paper_monthly = []
            paper_prov = "EXCLUDED_DEMO"

        evidence = {
            "target_monthly_pct": target_monthly_pct,
            "fund_id": fund_id,
            "fund_backtest": fund_backtest,
            "historical_validation": {
                **historical,
                "provenance": "VALIDATED_HISTORICAL",
            },
            "walk_forward": {
                "run_count": len([v for v in wf_monthly if v is not None]),
                "avg_monthly_return_pct": _safe_avg(wf_monthly),
                "provenance": "VALIDATED_HISTORICAL",
            },
            "monte_carlo": {
                "run_count": len([v for v in mc_monthly if v is not None]),
                "median_monthly_return_pct": _safe_avg(mc_monthly),
                "provenance": "VALIDATED_HISTORICAL",
            },
            "paper_live": {
                "portfolio_count": len(paper_metrics),
                "avg_monthly_return_pct": round(sum(paper_monthly) / len(paper_monthly), 2) if paper_monthly else None,
                "provenance": paper_prov,
            },
        }

        verdict, rationale = self._verdict(evidence, target_monthly_pct)
        evidence["verdict"] = verdict
        evidence["rationale"] = rationale
        return evidence

    def _verdict(self, evidence: dict, target: float) -> tuple[str, str]:
        hits = 0
        checks = 0
        parts = []

        fb = evidence.get("fund_backtest")
        if fb and fb.get("avg_monthly_return_pct") is not None:
            checks += 1
            monthly = fb["avg_monthly_return_pct"]
            if monthly >= target:
                hits += 1
                parts.append(f"Fund historical backtest: {monthly}% avg monthly meets {target}% target.")
            else:
                parts.append(
                    f"Fund historical backtest: {monthly}% avg monthly — does NOT meet {target}% target (actual result)."
                )

        hist = evidence["historical_validation"]
        if hist.get("verdict") == "SUPPORTED" or hist.get("conclusion") == "SUPPORTED":
            hits += 1
            parts.append("Historical backtests meet target.")
        elif hist.get("verdict") == "PARTIALLY_SUPPORTED" or hist.get("conclusion") == "PARTIALLY_SUPPORTED":
            parts.append("Historical backtests partially meet target.")
        checks += 1

        wf = evidence["walk_forward"].get("avg_monthly_return_pct")
        if wf is not None:
            checks += 1
            if wf >= target * 0.8:
                hits += 1
                parts.append(f"Walk-forward avg {wf}% near target.")
            else:
                parts.append(f"Walk-forward avg {wf}% below target.")

        mc = evidence["monte_carlo"].get("median_monthly_return_pct")
        if mc is not None:
            checks += 1
            if mc >= target * 0.7:
                hits += 1
                parts.append(f"Monte Carlo median {mc}% supports feasibility.")
            else:
                parts.append(f"Monte Carlo median {mc}% does not support target.")

        pl = evidence["paper_live"]
        if pl.get("avg_monthly_return_pct") is not None and pl.get("provenance") == "PAPER_LIVE":
            checks += 1
            if pl["avg_monthly_return_pct"] >= target * 0.5:
                hits += 1
                parts.append("Paper-live tracking shows progress toward target.")
            else:
                parts.append("Paper-live results below target (early stage).")
        elif pl.get("provenance") in ("DEMO", "EXCLUDED_DEMO"):
            parts.append("Paper-live excluded — demo ledger not used as evidence.")

        if checks == 0:
            return VERDICT_NOT, "Insufficient validation data to assess target."

        ratio = hits / checks
        if ratio >= 0.75:
            return VERDICT_SUPPORTED, " ".join(parts)
        if ratio >= 0.4:
            return VERDICT_PARTIAL, " ".join(parts)
        return VERDICT_NOT, " ".join(parts)
