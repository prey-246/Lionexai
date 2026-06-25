"""Institutional monthly fund reports — reproducible from stored data."""

from __future__ import annotations

import csv
import io
import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.analytics.performance_engine import PerformanceEngine
from app.engines.global_risk_engine import GlobalRiskEngine
from app.models import domain
from app.services.lnx_attribution_engine import LNXAttributionEngine

logger = logging.getLogger("nexa.institutional_report")


class InstitutionalReportService:
    def __init__(self, db: Session):
        self.db = db
        self.perf = PerformanceEngine(db)

    def generate_monthly_fund_report(self, fund_id: str, end_date: datetime | None = None) -> dict[str, Any]:
        fund = self.db.query(domain.Fund).filter(domain.Fund.id == fund_id.upper()).first()
        if not fund:
            raise ValueError(f"Fund not found: {fund_id}")

        end = end_date or datetime.utcnow()
        start = end - timedelta(days=30)

        fund_analytics = self.perf.fund_analytics(fund)
        treasury = self.perf.treasury_analytics(start)
        risk = GlobalRiskEngine(self.db).assess().to_dict()
        lnx_attr = LNXAttributionEngine(self.db).compute_attribution(store=False)
        equity_curve = self.perf.aggregate_fund_equity_curve(fund)

        allocations = self._allocation_changes(fund, start)
        commentary = self._market_commentary(risk)

        report = {
            "report_id": f"ifr_{uuid.uuid4().hex[:12]}",
            "report_type": "MONTHLY_FUND",
            "fund_id": fund.id,
            "fund_name": fund.name,
            "period_start": start.isoformat(),
            "period_end": end.isoformat(),
            "generated_at": datetime.utcnow().isoformat(),
            "market_commentary": commentary,
            "fund_performance": fund_analytics,
            "target_vs_realized": {
                "target_monthly_pct": fund.target_monthly_return_pct,
                "realized_monthly_pct": fund_analytics.get("realized_monthly_return_pct"),
                "validated_monthly_pct": fund_analytics.get("validated_monthly_return_pct"),
                "data_provenance": fund_analytics.get("data_provenance"),
            },
            "allocation_changes": allocations,
            "treasury_growth": treasury,
            "lnx_attribution": lnx_attr,
            "risk_metrics": {
                "global_risk_score": risk.get("global_risk_score"),
                "risk_label": risk.get("risk_label"),
                "explanation": risk.get("explanation"),
            },
            "performance_curve": equity_curve,
        }

        row = domain.InstitutionalReport(
            id=report["report_id"],
            report_type="MONTHLY_FUND",
            fund_id=fund.id,
            period_start=start,
            period_end=end,
            payload=report,
        )
        self.db.add(row)
        self.db.commit()
        return report

    def _allocation_changes(self, fund: domain.Fund, since: datetime) -> list[dict]:
        portfolios = (
            self.db.query(domain.Portfolio)
            .filter(domain.Portfolio.fund_pk_id == fund.pk_id, domain.Portfolio.auto_managed == True)
            .all()
        )
        changes = []
        for p in portfolios:
            rebalances = (
                self.db.query(domain.RebalanceEvent)
                .filter(
                    domain.RebalanceEvent.portfolio_id == p.pk_id,
                    domain.RebalanceEvent.created_at >= since,
                )
                .order_by(domain.RebalanceEvent.created_at.desc())
                .limit(5)
                .all()
            )
            for r in rebalances:
                changes.append({
                    "portfolio_id": p.id,
                    "trigger": r.trigger,
                    "regime": r.regime,
                    "decisions": r.decisions,
                    "created_at": r.created_at.isoformat(),
                })
        return changes

    def _market_commentary(self, risk: dict) -> str:
        return (
            f"Global risk {risk.get('global_risk_score')}/100 ({risk.get('risk_label')}). "
            f"{risk.get('explanation', '')}"
        )

    def export_json(self, report: dict) -> str:
        return json.dumps(report, indent=2, default=str)

    def export_csv(self, report: dict) -> str:
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["Section", "Metric", "Value", "Provenance"])
        fp = report.get("fund_performance", {})
        for key, val in fp.items():
            if isinstance(val, (int, float, str)) and val is not None:
                writer.writerow(["Fund Performance", key, val, fp.get("data_provenance", "")])
        tvr = report.get("target_vs_realized", {})
        for key, val in tvr.items():
            writer.writerow(["Target vs Realized", key, val, tvr.get("data_provenance", "")])
        tg = report.get("treasury_growth", {})
        for key, val in tg.items():
            if isinstance(val, (int, float, str)):
                writer.writerow(["Treasury", key, val, tg.get("data_provenance", "")])
        return buf.getvalue()

    def list_reports(self, fund_id: str | None = None, limit: int = 20) -> list[dict]:
        q = self.db.query(domain.InstitutionalReport).order_by(
            domain.InstitutionalReport.created_at.desc()
        )
        if fund_id:
            q = q.filter(domain.InstitutionalReport.fund_id == fund_id.upper())
        return [
            {
                "id": r.id,
                "report_type": r.report_type,
                "fund_id": r.fund_id,
                "period_start": r.period_start,
                "period_end": r.period_end,
                "created_at": r.created_at,
            }
            for r in q.limit(limit).all()
        ]

    def get_report(self, report_id: str) -> dict | None:
        row = self.db.query(domain.InstitutionalReport).filter(domain.InstitutionalReport.id == report_id).first()
        return row.payload if row else None
