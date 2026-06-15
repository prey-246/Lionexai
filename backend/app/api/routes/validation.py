import io
import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.core.database import get_db
from app.models import domain

logger = logging.getLogger(__name__)
router = APIRouter()

EXECUTED_ACTIONS = (
    "AUTONOMOUS_TRADE_EXECUTED_BINANCE",
    "AUTONOMOUS_TRADE_EXECUTED_BYBIT",
    "AUTONOMOUS_TRADE_EXECUTED_VIA_BINANCE",
    "AUTONOMOUS_TRADE_EXECUTED_VIA_BYBIT",
    "ORDER_FILLED",
)


class DayMetrics(BaseModel):
    day: int
    label: str
    trades_executed: int
    success_rate_pct: float
    risk_rejections: int
    orders_filled: int
    orders_rejected: int


class PortfolioPerformance(BaseModel):
    portfolio_id: str
    trade_count: int
    success_count: int


class ValidationSummary(BaseModel):
    days: list[DayMetrics]
    total_orders: int
    filled_orders: int
    rejected_orders: int
    average_latency_ms: float
    best_portfolio: str | None
    worst_portfolio: str | None
    exchange_uptime_pct: float
    validation_started_at: datetime | None


def _day_window(day_offset: int) -> tuple[datetime, datetime]:
    """day_offset 0 = today, 1 = yesterday, 2 = two days ago."""
    end = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    start = end - timedelta(days=day_offset + 1)
    end = start + timedelta(days=1)
    return start, end


def _day_metrics(db: Session, day_num: int, day_offset: int) -> DayMetrics:
    start, end = _day_window(day_offset)
    label = start.strftime("%Y-%m-%d")

    executed = db.query(func.count(domain.AuditLog.id)).filter(
        and_(
            domain.AuditLog.action_type.in_(EXECUTED_ACTIONS),
            domain.AuditLog.timestamp >= start,
            domain.AuditLog.timestamp < end,
        )
    ).scalar() or 0

    rejected = db.query(func.count(domain.AuditLog.id)).filter(
        and_(
            domain.AuditLog.action_type.in_(["ORDER_REJECTED", "RISK_REJECTION"]),
            domain.AuditLog.timestamp >= start,
            domain.AuditLog.timestamp < end,
        )
    ).scalar() or 0

    filled = db.query(func.count(domain.AuditLog.id)).filter(
        and_(
            domain.AuditLog.action_type == "ORDER_FILLED",
            domain.AuditLog.timestamp >= start,
            domain.AuditLog.timestamp < end,
        )
    ).scalar() or 0

    total = executed + rejected
    success_rate = (executed / total * 100) if total > 0 else 100.0

    return DayMetrics(
        day=day_num,
        label=label,
        trades_executed=executed,
        success_rate_pct=round(success_rate, 2),
        risk_rejections=rejected,
        orders_filled=filled or executed,
        orders_rejected=rejected,
    )


@router.get(
    "/summary",
    response_model=ValidationSummary,
    dependencies=[Depends(require_role(["admin", "operator", "risk_manager"]))],
)
def get_validation_summary(db: Session = Depends(get_db)):
    days = [_day_metrics(db, i + 1, i) for i in range(3)]

    three_days_ago = datetime.utcnow() - timedelta(days=3)
    total_orders = db.query(func.count(domain.AuditLog.id)).filter(
        and_(
            or_(
                domain.AuditLog.action_type.in_(EXECUTED_ACTIONS),
                domain.AuditLog.action_type.in_(["ORDER_REJECTED", "RISK_REJECTION"]),
            ),
            domain.AuditLog.timestamp >= three_days_ago,
        )
    ).scalar() or 0

    filled_orders = db.query(func.count(domain.AuditLog.id)).filter(
        and_(
            domain.AuditLog.action_type.in_(list(EXECUTED_ACTIONS) + ["ORDER_FILLED"]),
            domain.AuditLog.timestamp >= three_days_ago,
        )
    ).scalar() or 0

    rejected_orders = db.query(func.count(domain.AuditLog.id)).filter(
        and_(
            domain.AuditLog.action_type.in_(["ORDER_REJECTED", "RISK_REJECTION"]),
            domain.AuditLog.timestamp >= three_days_ago,
        )
    ).scalar() or 0

    latency_logs = db.query(domain.AuditLog).filter(
        and_(
            domain.AuditLog.action_type.in_(list(EXECUTED_ACTIONS)),
            domain.AuditLog.timestamp >= three_days_ago,
        )
    ).all()
    latencies = [
        float(log.metadata_json["latency_ms"])
        for log in latency_logs
        if log.metadata_json and log.metadata_json.get("latency_ms") is not None
    ]
    avg_latency = round(sum(latencies) / len(latencies), 2) if latencies else 0.0

    portfolio_stats: dict[str, PortfolioPerformance] = {}
    for log in latency_logs:
        meta = log.metadata_json or {}
        pid = meta.get("portfolio")
        if not pid:
            continue
        if pid not in portfolio_stats:
            portfolio_stats[pid] = PortfolioPerformance(portfolio_id=pid, trade_count=0, success_count=0)
        portfolio_stats[pid].trade_count += 1
        portfolio_stats[pid].success_count += 1

    best_portfolio = None
    worst_portfolio = None
    if portfolio_stats:
        ranked = sorted(portfolio_stats.values(), key=lambda p: p.success_count, reverse=True)
        best_portfolio = ranked[0].portfolio_id
        worst_portfolio = ranked[-1].portfolio_id

    reconnects = db.query(func.count(domain.AuditLog.id)).filter(
        domain.AuditLog.action_type == "EXCHANGE_RECONNECTED",
        domain.AuditLog.timestamp >= three_days_ago,
    ).scalar() or 0
    disconnects = db.query(func.count(domain.AuditLog.id)).filter(
        domain.AuditLog.action_type == "EXCHANGE_DISCONNECTED",
        domain.AuditLog.timestamp >= three_days_ago,
    ).scalar() or 0
    uptime_pct = 100.0
    if reconnects + disconnects > 0:
        uptime_pct = round(reconnects / (reconnects + disconnects) * 100, 2)

    first_log = db.query(domain.AuditLog).filter(
        domain.AuditLog.action_type.in_(list(EXECUTED_ACTIONS))
    ).order_by(domain.AuditLog.timestamp.asc()).first()

    return ValidationSummary(
        days=days,
        total_orders=total_orders,
        filled_orders=filled_orders,
        rejected_orders=rejected_orders,
        average_latency_ms=avg_latency,
        best_portfolio=best_portfolio,
        worst_portfolio=worst_portfolio,
        exchange_uptime_pct=uptime_pct,
        validation_started_at=first_log.timestamp if first_log else None,
    )


@router.get(
    "/report/pdf",
    dependencies=[Depends(require_role(["admin", "operator", "risk_manager"]))],
)
def download_validation_report_pdf(db: Session = Depends(get_db)):
    summary = get_validation_summary(db)

    try:
        from weasyprint import HTML
    except ImportError:
        return Response(content=b"PDF generation unavailable.", status_code=501)

    day_rows = "".join(
        f"<tr><td>Day {d.day} ({d.label})</td><td>{d.trades_executed}</td>"
        f"<td>{d.success_rate_pct}%</td><td>{d.risk_rejections}</td></tr>"
        for d in summary.days
    )

    html = f"""
    <!DOCTYPE html>
    <html><head><style>
    body {{ font-family: Arial, sans-serif; margin: 40px; color: #1a1a1a; }}
    h1 {{ color: #c9a227; }} table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
    th {{ background: #f5f5f5; }}
    </style></head><body>
    <h1>NEXA Platform — Validation Report</h1>
    <p>Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</p>
    <h2>Three-Day Performance</h2>
    <table>
      <tr><th>Day</th><th>Trades Executed</th><th>Success Rate</th><th>Risk Rejections</th></tr>
      {day_rows}
    </table>
    <h2>Aggregated Results</h2>
    <ul>
      <li>Total Orders: {summary.total_orders}</li>
      <li>Filled Orders: {summary.filled_orders}</li>
      <li>Rejected Orders: {summary.rejected_orders}</li>
      <li>Average Latency: {summary.average_latency_ms} ms</li>
      <li>Best Portfolio: {summary.best_portfolio or 'N/A'}</li>
      <li>Worst Portfolio: {summary.worst_portfolio or 'N/A'}</li>
      <li>Exchange Uptime: {summary.exchange_uptime_pct}%</li>
    </ul>
    <p><em>Historical Strategy Performance Simulation — Illustrative Projections Only.</em></p>
    </body></html>
    """

    pdf_bytes = HTML(string=html).write_pdf()
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=nexa_validation_report.pdf"},
    )
