"""LNX index attribution — explain every index movement by component."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.analytics.performance_engine import PerformanceEngine
from app.models import domain

logger = logging.getLogger("nexa.lnx_attribution")

LNX_SUPPLY = 100_000_000.0


class LNXAttributionEngine:
    def __init__(self, db: Session):
        self.db = db

    def compute_attribution(self, store: bool = True) -> dict[str, Any]:
        prev = (
            self.db.query(domain.LNXIndexSnapshot)
            .order_by(domain.LNXIndexSnapshot.computed_at.desc())
            .offset(1)
            .first()
        )
        latest = (
            self.db.query(domain.LNXIndexSnapshot)
            .order_by(domain.LNXIndexSnapshot.computed_at.desc())
            .first()
        )

        nav_total = float(self.db.query(func.sum(domain.TreasuryPool.balance)).scalar() or 0)
        reserve = self.db.query(domain.TreasuryPool).filter(domain.TreasuryPool.id == "RESERVE").first()
        reserve_ratio = (reserve.balance / nav_total * 100) if nav_total and reserve else 0

        aum = float(
            self.db.query(func.sum(domain.Portfolio.total_equity))
            .filter(domain.Portfolio.auto_managed == True)
            .scalar() or 0
        )

        cutoff = datetime.utcnow() - timedelta(days=30)
        profit_30d = float(
            self.db.query(func.sum(domain.Trade.pnl))
            .filter(domain.Trade.status == "CLOSED", domain.Trade.closed_at >= cutoff)
            .scalar() or 0
        )

        settlements = (
            self.db.query(domain.ClientSettlement)
            .filter(domain.ClientSettlement.period_end >= cutoff)
            .all()
        )
        yield_delivered = sum(s.client_entitlement or 0 for s in settlements)
        treasury_routed = sum(s.excess_routed or 0 for s in settlements)

        perf = PerformanceEngine(self.db)
        treasury = perf.treasury_analytics(cutoff)

        components = {
            "treasury_nav": {"value": nav_total, "weight": 0.30, "contribution_pts": 0.0},
            "aum_growth": {"value": aum, "weight": 0.15, "contribution_pts": 0.0},
            "reserve_strength": {"value": reserve_ratio, "weight": 0.10, "contribution_pts": 0.0},
            "yield_delivery": {"value": yield_delivered, "weight": 0.15, "contribution_pts": 0.0},
            "strategy_performance": {"value": profit_30d, "weight": 0.25, "contribution_pts": 0.0},
            "treasury_routing": {"value": treasury_routed, "weight": 0.05, "contribution_pts": 0.0},
        }

        index_delta = 0.0
        if latest and prev and prev.composite_index:
            index_delta = latest.composite_index - prev.composite_index

        # Attribute delta proportionally to component score changes
        if latest and prev:
            deltas = {
                "treasury_nav": (latest.treasury_health or 0) - (prev.treasury_health or 0),
                "strategy_performance": (latest.strategy_performance or 0) - (prev.strategy_performance or 0),
                "aum_growth": (latest.aum_growth or 0) - (prev.aum_growth or 0),
                "execution_quality": (latest.execution_quality or 0) - (prev.execution_quality or 0),
            }
            total_abs = sum(abs(v) for v in deltas.values()) or 1
            attribution = {
                k: round(v / total_abs * index_delta, 4) for k, v in deltas.items()
            }
            attribution["yield_delivery"] = round(
                (yield_delivered / max(aum, 1)) * index_delta * 0.15, 4
            )
            attribution["treasury_routing"] = round(
                (treasury_routed / max(nav_total, 1)) * index_delta * 0.05, 4
            )
        else:
            attribution = {k: 0.0 for k in components}
            attribution["execution_quality"] = 0.0

        dominant = max(attribution, key=lambda k: abs(attribution[k])) if attribution else None
        direction = "UP" if index_delta > 0 else "DOWN" if index_delta < 0 else "FLAT"

        explanation = self._build_explanation(direction, index_delta, attribution, dominant, components)

        result = {
            "computed_at": datetime.utcnow().isoformat(),
            "index_delta": round(index_delta, 4),
            "direction": direction,
            "current_composite": latest.composite_index if latest else None,
            "previous_composite": prev.composite_index if prev else None,
            "attribution": attribution,
            "components": components,
            "dominant_driver": dominant,
            "explanation": explanation,
            "data_provenance": treasury.get("data_provenance", "DEMO"),
        }

        if store:
            snap = domain.LNXAttributionSnapshot(
                id=f"lnx_attr_{uuid.uuid4().hex[:12]}",
                index_delta=round(index_delta, 4),
                direction=direction,
                attribution=attribution,
                components=components,
                explanation=explanation,
            )
            self.db.add(snap)
            self.db.commit()

        return result

    def _build_explanation(
        self, direction: str, delta: float, attribution: dict, dominant: str | None, components: dict,
    ) -> str:
        if direction == "FLAT":
            return "LNX index unchanged — all components stable."
        sign = "rose" if direction == "UP" else "fell"
        parts = [f"LNX {sign} by {abs(delta):.2f} pts."]
        if dominant:
            parts.append(f"Largest contributor: {dominant.replace('_', ' ')} ({attribution.get(dominant, 0):+.2f} pts).")
        if components.get("yield_delivery", {}).get("value"):
            parts.append(f"Yield delivered ${components['yield_delivery']['value']:,.0f} over 30D.")
        if components.get("treasury_nav", {}).get("value"):
            parts.append(f"Treasury NAV ${components['treasury_nav']['value']:,.0f}.")
        return " ".join(parts)

    def history(self, limit: int = 30) -> list[dict]:
        rows = (
            self.db.query(domain.LNXAttributionSnapshot)
            .order_by(domain.LNXAttributionSnapshot.computed_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "id": r.id,
                "index_delta": r.index_delta,
                "direction": r.direction,
                "attribution": r.attribution,
                "explanation": r.explanation,
                "computed_at": r.computed_at,
            }
            for r in rows
        ]
