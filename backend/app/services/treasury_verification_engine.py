"""Treasury verification — validate routing, settlements, pool movements, solvency."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models import domain
from app.services.settlement_constants import PROFIT_ROUTING_SPLIT

logger = logging.getLogger("nexa.treasury_verification")

STRESS_SCENARIOS = (
    "MARKET_CRASH_20",
    "MARKET_CRASH_40",
    "CONSECUTIVE_LOSING_MONTHS",
    "YIELD_POOL_DEPLETION",
    "RESERVE_DEPLETION",
)

# Baseline pool balances after institutional demo reset (operational ledger anchor).
OPERATIONAL_POOL_BASELINE: dict[str, float] = {
    "RESERVE": 1_000_000.0,
    "YIELD": 250_000.0,
    "GROWTH": 400_000.0,
    "OPERATIONS": 150_000.0,
    "INSURANCE": 500_000.0,
    "LNX_INDEX": 75_000.0,
}


def _is_validated_settlement(settlement: domain.ClientSettlement) -> bool:
    """Synthetic settlements from validated backtests — not operational treasury events."""
    sid = settlement.id or ""
    if sid.startswith("stl_val_"):
        return True
    breakdown = settlement.breakdown or {}
    if breakdown.get("provenance") == "VALIDATED_HISTORICAL":
        return True
    return False


def _operational_settlements(settlements: list[domain.ClientSettlement]) -> list[domain.ClientSettlement]:
    return [s for s in settlements if not _is_validated_settlement(s)]


@dataclass
class TreasuryVerificationResult:
    solvency_score: float
    status: str
    issues: list[str]
    pool_balances: dict[str, float]
    routing_integrity_pct: float
    settlement_coverage_pct: float
    stress_results: dict[str, Any]
    provenance: str = "AUDIT"
    ledger_reconciliation: dict[str, Any] | None = None

    def to_dict(self) -> dict:
        return asdict(self)


class TreasuryVerificationEngine:
    def __init__(self, db: Session):
        self.db = db

    def verify(self) -> TreasuryVerificationResult:
        issues: list[str] = []
        pools = {p.id: p for p in self.db.query(domain.TreasuryPool).all()}
        balances = {pid: round(p.balance or 0, 2) for pid, p in pools.items()}
        nav = sum(balances.values())

        all_settlements = self.db.query(domain.ClientSettlement).all()
        operational = _operational_settlements(all_settlements)
        validated_count = len(all_settlements) - len(operational)
        txs = self.db.query(domain.TreasuryTransaction).all()

        ledger_recon = self._ledger_reconciliation(pools, txs)
        ledger_gap = ledger_recon.get("total_balance_gap", 0.0)
        if abs(ledger_gap) > 1000.0:
            issues.append(
                f"Ledger drift: pool balances exceed baseline+transactions by ${ledger_gap:,.2f} "
                f"(likely validated backtest contamination — run reconcile_treasury_ledger.py)"
            )

        if validated_count > 0:
            val_excess = sum(s.excess_routed or 0 for s in all_settlements if _is_validated_settlement(s))
            if val_excess > 0:
                issues.append(
                    f"Validated synthetic settlements ({validated_count}) record ${val_excess:,.2f} "
                    f"excess_routed — excluded from operational routing checks"
                )

        # Settlement coverage — operational ledger only (guaranteed-target model)
        if operational:
            covered = sum(1 for s in operational if (s.uncovered or 0) <= 0)
            settlement_coverage = covered / len(operational) * 100
        else:
            settlement_coverage = 100.0

        # Routing integrity — operational settlements vs PROFIT_ROUTING ledger
        routed_from_settlements = sum(s.excess_routed or 0 for s in operational)
        routed_txs = sum(
            t.amount for t in txs if t.transaction_type == "PROFIT_ROUTING" and t.amount > 0
        )
        routing_delta = abs(routed_from_settlements - routed_txs)
        if routing_delta > 1.0 and routed_from_settlements > 0:
            issues.append(
                f"Operational routing mismatch: settlements ${routed_from_settlements:,.2f} "
                f"vs treasury transactions ${routed_txs:,.2f}"
            )
        routing_integrity = max(0, 100 - (routing_delta / max(routed_from_settlements, 1) * 100))

        # Double routing detection (operational txs only)
        op_txs = [t for t in txs if t.transaction_type == "PROFIT_ROUTING" and t.settlement_pk_id]
        settlement_refs = [t.settlement_pk_id for t in op_txs]
        dup_refs = {r for r in settlement_refs if settlement_refs.count(r) > len(PROFIT_ROUTING_SPLIT)}
        if dup_refs:
            issues.append(f"Possible double routing on {len(dup_refs)} settlement(s)")

        # Pool imbalance vs targets (operational NAV only — use ledger-implied if contaminated)
        recon_nav = ledger_recon.get("implied_total_nav") or nav
        for pid, pool in pools.items():
            target = pool.target_allocation_pct or 0
            actual_pct = (pool.balance / nav * 100) if nav > 0 else 0
            implied_pct = (ledger_recon.get("implied_balances", {}).get(pid, pool.balance) / recon_nav * 100) if recon_nav > 0 else 0
            if target > 0 and abs(actual_pct - target) > target * 0.5:
                issues.append(
                    f"Pool {pid} drift: target {target:.1f}% actual {actual_pct:.1f}% "
                    f"(ledger-implied {implied_pct:.1f}%)"
                )

        for expected in PROFIT_ROUTING_SPLIT:
            if expected not in pools:
                issues.append(f"Missing treasury pool: {expected}")

        reserve = balances.get("RESERVE", 0)
        yield_pool = balances.get("YIELD", 0)
        if nav > 0 and reserve / nav < 0.05:
            issues.append("Reserve ratio below 5% — solvency concern")

        stress = self._run_stress_tests(balances, nav, operational)
        for scenario, result in stress.items():
            if result.get("insolvent"):
                issues.append(f"Stress {scenario}: insolvency projected")

        score = self._solvency_score(nav, reserve, yield_pool, settlement_coverage, routing_integrity, len(issues))
        status = "HEALTHY" if score >= 80 else "WATCH" if score >= 60 else "AT_RISK"

        return TreasuryVerificationResult(
            solvency_score=round(score, 2),
            status=status,
            issues=issues,
            pool_balances=balances,
            routing_integrity_pct=round(routing_integrity, 2),
            settlement_coverage_pct=round(settlement_coverage, 2),
            stress_results=stress,
            ledger_reconciliation=ledger_recon,
        )

    def _ledger_reconciliation(
        self, pools: dict[str, domain.TreasuryPool], txs: list[domain.TreasuryTransaction]
    ) -> dict[str, Any]:
        """Compare stored pool balances to baseline + immutable transaction ledger."""
        implied: dict[str, float] = {}
        gaps: dict[str, float] = {}
        for pid, pool in pools.items():
            baseline = OPERATIONAL_POOL_BASELINE.get(pid, 0.0)
            net_tx = sum(t.amount for t in txs if t.pool_pk_id == pool.pk_id)
            implied_bal = round(baseline + net_tx, 2)
            implied[pid] = implied_bal
            gaps[pid] = round((pool.balance or 0) - implied_bal, 2)
        implied_nav = sum(implied.values())
        stored_nav = sum(p.balance or 0 for p in pools.values())
        return {
            "implied_balances": implied,
            "balance_gaps": gaps,
            "implied_total_nav": round(implied_nav, 2),
            "stored_total_nav": round(stored_nav, 2),
            "total_balance_gap": round(stored_nav - implied_nav, 2),
            "baseline": OPERATIONAL_POOL_BASELINE,
        }

    def _solvency_score(
        self, nav: float, reserve: float, yield_pool: float,
        settlement_cov: float, routing_int: float, issue_count: int,
    ) -> float:
        reserve_ratio = (reserve / nav * 100) if nav > 0 else 0
        score = 40.0
        score += min(20, reserve_ratio)
        score += settlement_cov * 0.2
        score += routing_int * 0.15
        score += min(10, yield_pool / max(nav, 1) * 100)
        score -= issue_count * 5
        return max(0, min(100, score))

    def _run_stress_tests(
        self, balances: dict[str, float], nav: float, settlements: list,
    ) -> dict[str, Any]:
        reserve = balances.get("RESERVE", 0)
        yield_pool = balances.get("YIELD", 0)
        avg_shortfall = 0.0
        if settlements:
            shortfalls = [s.shortfall_topup or 0 for s in settlements if (s.shortfall_topup or 0) > 0]
            avg_shortfall = sum(shortfalls) / len(shortfalls) if shortfalls else 0

        aum_proxy = sum(
            p.total_equity or 0
            for p in self.db.query(domain.Portfolio).filter(domain.Portfolio.auto_managed == True).all()
            if not (p.id or "").endswith("-VALIDATED")
        )

        return {
            "MARKET_CRASH_20": {
                "aum_after_shock": round(aum_proxy * 0.8, 2),
                "reserve_after_topups": round(reserve - avg_shortfall * 4, 2),
                "insolvent": reserve - avg_shortfall * 4 < 0,
            },
            "MARKET_CRASH_40": {
                "aum_after_shock": round(aum_proxy * 0.6, 2),
                "reserve_after_topups": round(reserve - avg_shortfall * 8, 2),
                "insolvent": reserve - avg_shortfall * 8 < 0,
            },
            "CONSECUTIVE_LOSING_MONTHS": {
                "months_covered_by_reserve": round(reserve / max(avg_shortfall, 1), 1),
                "insolvent": reserve < avg_shortfall * 3,
            },
            "YIELD_POOL_DEPLETION": {
                "yield_pool": yield_pool,
                "insolvent": yield_pool <= 0,
            },
            "RESERVE_DEPLETION": {
                "reserve": reserve,
                "insolvent": reserve <= nav * 0.02 if nav > 0 else True,
            },
        }

    def persist_run(self, result: TreasuryVerificationResult) -> domain.TreasuryVerificationRun:
        row = domain.TreasuryVerificationRun(
            id=f"tvr_{uuid.uuid4().hex[:12]}",
            solvency_score=result.solvency_score,
            status=result.status,
            issues=result.issues,
            pool_balances=result.pool_balances,
            routing_integrity_pct=result.routing_integrity_pct,
            settlement_coverage_pct=result.settlement_coverage_pct,
            stress_results=result.stress_results,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row
