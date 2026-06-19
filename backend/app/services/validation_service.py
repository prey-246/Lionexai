import logging
import re
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models import domain
from app.services.validation_constants import (
    EXECUTED_ACTIONS,
    REJECTED_ACTIONS,
    PAPER_TRADE_SOURCE,
    SNAPSHOT_PERIODS,
    SCOPED_SNAPSHOT_PERIODS,
    ROLLING_WINDOW_DAYS,
    HISTORY_RETENTION_DAYS,
    METRIC_TIMESERIES_FIELDS,
)

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def _slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_")[:48]


def _period_start(period_spec: int | str | None) -> datetime | None:
    if period_spec == "today":
        return datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    if period_spec is None:
        return None
    return datetime.utcnow() - timedelta(days=int(period_spec))


def _paper_trades_query(
    db: Session,
    start_date: datetime | None,
    closed_only: bool = False,
    end_date: datetime | None = None,
    portfolio_pk: int | None = None,
    strategy_name: str | None = None,
):
    query = db.query(domain.Trade).filter(domain.Trade.trade_source == PAPER_TRADE_SOURCE)
    if portfolio_pk is not None:
        query = query.filter(domain.Trade.portfolio_id == portfolio_pk)
    if strategy_name is not None:
        query = query.filter(domain.Trade.strategy_name == strategy_name)
    if closed_only:
        query = query.filter(domain.Trade.status == "CLOSED", domain.Trade.pnl.isnot(None))
        if start_date:
            query = query.filter(domain.Trade.closed_at >= start_date)
        if end_date:
            query = query.filter(domain.Trade.closed_at <= end_date)
    else:
        if start_date:
            query = query.filter(domain.Trade.created_at >= start_date)
        if end_date:
            query = query.filter(domain.Trade.created_at <= end_date)
    return query


def _paper_audit_query(
    db: Session,
    start_date: datetime | None,
    end_date: datetime | None = None,
    portfolio_pk: int | None = None,
):
    query = db.query(domain.AuditLog).filter(
        domain.AuditLog.metadata_json.op("->>")("exchange").in_(["binance", "bybit"])
    )
    if start_date:
        query = query.filter(domain.AuditLog.timestamp >= start_date)
    if end_date:
        query = query.filter(domain.AuditLog.timestamp <= end_date)
    if portfolio_pk is not None:
        portfolio = db.query(domain.Portfolio).filter(domain.Portfolio.pk_id == portfolio_pk).first()
        if portfolio:
            query = query.filter(
                domain.AuditLog.metadata_json.op("->>")("portfolio_id").in_([portfolio.id, str(portfolio.pk_id)])
            )
    return query


def _series_from_frame(frame: pd.DataFrame, time_col: str, value_col: str) -> list[dict[str, Any]]:
    if frame.empty:
        return []
    return [
        {"time": int(pd.Timestamp(row[time_col]).timestamp()), "value": float(row[value_col])}
        for _, row in frame.iterrows()
    ]


def _portfolio_id_map(db: Session, portfolio_pks: list[int]) -> dict[int, str]:
    if not portfolio_pks:
        return {}
    rows = db.query(domain.Portfolio.pk_id, domain.Portfolio.id).filter(
        domain.Portfolio.pk_id.in_(portfolio_pks)
    ).all()
    return {pk: portfolio_id for pk, portfolio_id in rows}


def _rank_best_worst(db: Session, closed_trades: list) -> dict[str, str | None]:
    pnl_by_portfolio: dict[int, float] = {}
    pnl_by_strategy: dict[str, float] = {}
    for trade in closed_trades:
        if trade.pnl is None:
            continue
        pnl_by_portfolio[trade.portfolio_id] = pnl_by_portfolio.get(trade.portfolio_id, 0.0) + trade.pnl
        if trade.strategy_name:
            pnl_by_strategy[trade.strategy_name] = pnl_by_strategy.get(trade.strategy_name, 0.0) + trade.pnl

    portfolio_map = _portfolio_id_map(db, list(pnl_by_portfolio.keys()))
    best_portfolio = worst_portfolio = best_strategy = worst_strategy = None
    if pnl_by_portfolio:
        best_portfolio = portfolio_map.get(max(pnl_by_portfolio, key=pnl_by_portfolio.get))
        worst_portfolio = portfolio_map.get(min(pnl_by_portfolio, key=pnl_by_portfolio.get))
    if pnl_by_strategy:
        best_strategy = max(pnl_by_strategy, key=pnl_by_strategy.get)
        worst_strategy = min(pnl_by_strategy, key=pnl_by_strategy.get)

    return {
        "best_portfolio": best_portfolio,
        "worst_portfolio": worst_portfolio,
        "best_strategy": best_strategy,
        "worst_strategy": worst_strategy,
    }


def _exchange_distribution(audit_base) -> dict[str, Any]:
    binance = audit_base.filter(
        domain.AuditLog.action_type.in_(EXECUTED_ACTIONS),
        domain.AuditLog.metadata_json.op("->>")("exchange") == "binance",
    ).count()
    bybit = audit_base.filter(
        domain.AuditLog.action_type.in_(EXECUTED_ACTIONS),
        domain.AuditLog.metadata_json.op("->>")("exchange") == "bybit",
    ).count()
    total = binance + bybit
    return {
        "binance": binance,
        "bybit": bybit,
        "binance_pct": round(binance / total * 100, 1) if total else 0.0,
        "bybit_pct": round(bybit / total * 100, 1) if total else 0.0,
    }


def _calculate_advanced_metrics(
    db: Session,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    portfolio_pk: int | None = None,
    strategy_name: str | None = None,
) -> dict:
    closed_trades = _paper_trades_query(
        db, start_date, closed_only=True, end_date=end_date,
        portfolio_pk=portfolio_pk, strategy_name=strategy_name,
    ).order_by(domain.Trade.closed_at.asc()).all()
    all_trades = _paper_trades_query(
        db, start_date, closed_only=False, end_date=end_date,
        portfolio_pk=portfolio_pk, strategy_name=strategy_name,
    ).all()

    empty = {
        "sharpe_ratio": None,
        "max_drawdown_pct": 0.0,
        "avg_return_pct": 0.0,
        "equity_curve": [],
        "cumulative_pnl": [],
        "daily_pnl": [],
        "weekly_pnl": [],
        "monthly_pnl": [],
        "drawdown_series": [],
        "rolling_drawdown": [],
        "daily_trades": [],
        "daily_returns": [],
        "rolling_win_rate": [],
    }

    if all_trades:
        activity_rows = []
        for trade in all_trades:
            ts = trade.created_at.replace(hour=0, minute=0, second=0, microsecond=0)
            activity_rows.append({"day": ts})
        activity_df = pd.DataFrame(activity_rows).groupby("day", as_index=False).size()
        activity_df.columns = ["day", "trade_count"]
        daily_trades = _series_from_frame(activity_df, "day", "trade_count")
    else:
        daily_trades = []

    if not closed_trades:
        return {**empty, "daily_trades": daily_trades}

    rows = []
    cumulative = 0.0
    for trade in closed_trades:
        if trade.closed_at is None or trade.pnl is None:
            continue
        cumulative += trade.pnl
        rows.append({
            "closed_at": trade.closed_at.replace(hour=0, minute=0, second=0, microsecond=0),
            "pnl": trade.pnl,
            "win": 1 if trade.pnl > 0 else 0,
            "cumulative_pnl": cumulative,
            "return_pct": (
                (trade.pnl / (trade.entry_price * trade.quantity)) * 100
                if trade.entry_price and trade.quantity
                else 0.0
            ),
        })

    if not rows:
        return {**empty, "daily_trades": daily_trades}

    df = pd.DataFrame(rows)
    daily = df.groupby("closed_at", as_index=False).agg(
        daily_pnl=("pnl", "sum"),
        wins=("win", "sum"),
        trade_count=("pnl", "count"),
        cumulative_pnl=("cumulative_pnl", "last"),
        avg_return_pct=("return_pct", "mean"),
    )
    daily["daily_return"] = daily["cumulative_pnl"].pct_change().fillna(0)
    daily["daily_return_pct"] = daily["daily_return"] * 100
    daily["win_rate"] = np.where(
        daily["trade_count"] > 0,
        daily["wins"] / daily["trade_count"] * 100,
        0.0,
    )
    daily["rolling_win_rate"] = daily["win_rate"].rolling(
        window=ROLLING_WINDOW_DAYS, min_periods=1
    ).mean()

    daily_returns = daily["daily_return"].dropna()
    if len(daily_returns) > 1 and daily_returns.std() > 0:
        sharpe_ratio = (daily_returns.mean() / daily_returns.std()) * np.sqrt(365)
    else:
        sharpe_ratio = None

    daily["cumulative_max"] = daily["cumulative_pnl"].cummax()
    daily["drawdown"] = np.where(
        daily["cumulative_max"] > 0,
        (daily["cumulative_max"] - daily["cumulative_pnl"]) / daily["cumulative_max"],
        0.0,
    )
    daily["rolling_drawdown"] = daily["drawdown"].rolling(
        window=ROLLING_WINDOW_DAYS, min_periods=1
    ).mean()

    max_drawdown_pct = float(daily["drawdown"].max() * 100) if not daily.empty else 0.0
    avg_return_pct = float(daily["avg_return_pct"].mean()) if not daily.empty else 0.0

    weekly = daily.set_index("closed_at").resample("W").agg({"daily_pnl": "sum"}).reset_index()
    monthly = daily.set_index("closed_at").resample("M").agg({"daily_pnl": "sum"}).reset_index()
    cumulative_pnl = _series_from_frame(daily, "closed_at", "cumulative_pnl")

    return {
        "sharpe_ratio": round(sharpe_ratio, 2) if sharpe_ratio is not None else None,
        "max_drawdown_pct": round(max_drawdown_pct, 2),
        "avg_return_pct": round(avg_return_pct, 2),
        "equity_curve": cumulative_pnl,
        "cumulative_pnl": cumulative_pnl,
        "daily_pnl": _series_from_frame(daily, "closed_at", "daily_pnl"),
        "weekly_pnl": _series_from_frame(weekly, "closed_at", "daily_pnl"),
        "monthly_pnl": _series_from_frame(monthly, "closed_at", "daily_pnl"),
        "drawdown_series": [
            {"time": int(row.closed_at.timestamp()), "value": -float(row.drawdown) * 100}
            for row in daily.itertuples()
        ],
        "rolling_drawdown": [
            {"time": int(row.closed_at.timestamp()), "value": -float(row.rolling_drawdown) * 100}
            for row in daily.itertuples()
        ],
        "daily_trades": daily_trades,
        "daily_returns": _series_from_frame(daily, "closed_at", "daily_return_pct"),
        "rolling_win_rate": _series_from_frame(daily, "closed_at", "rolling_win_rate"),
    }


def _build_snapshot_key(
    snapshot_type: str,
    period_label: str,
    scope_id: str | None = None,
) -> str:
    if snapshot_type == "GLOBAL":
        return f"GLOBAL_{period_label}"
    if snapshot_type == "PORTFOLIO":
        return f"PORTFOLIO_{scope_id}_{period_label}"
    return f"STRATEGY_{_slug(scope_id or 'unknown')}_{period_label}"


def _build_snapshot_data(
    db: Session,
    period_label: str,
    period_spec: int | str | None,
    snapshot_type: str = "GLOBAL",
    scope_id: str | None = None,
    portfolio_pk: int | None = None,
    strategy_name: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> dict[str, Any]:
    if start_date is None:
        start_date = _period_start(period_spec)

    closed_trades = _paper_trades_query(
        db, start_date, closed_only=True, end_date=end_date,
        portfolio_pk=portfolio_pk, strategy_name=strategy_name,
    ).all()

    total_trades = len(closed_trades)
    winning_trades = sum(1 for t in closed_trades if t.pnl is not None and t.pnl > 0)
    losing_trades = sum(1 for t in closed_trades if t.pnl is not None and t.pnl < 0)
    win_rate_pct = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0
    total_pnl = sum(t.pnl for t in closed_trades if t.pnl is not None)
    gross_profit = sum(t.pnl for t in closed_trades if t.pnl is not None and t.pnl > 0)
    gross_loss = abs(sum(t.pnl for t in closed_trades if t.pnl is not None and t.pnl < 0))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else None
    largest_win = max((t.pnl for t in closed_trades if t.pnl is not None), default=0.0)
    largest_loss = min((t.pnl for t in closed_trades if t.pnl is not None), default=0.0)

    audit_base = _paper_audit_query(db, start_date, end_date=end_date, portfolio_pk=portfolio_pk)
    filled_orders = audit_base.filter(domain.AuditLog.action_type.in_(EXECUTED_ACTIONS)).count()
    rejected_orders = audit_base.filter(domain.AuditLog.action_type.in_(REJECTED_ACTIONS)).count()
    total_orders = filled_orders + rejected_orders
    fill_rate_pct = (filled_orders / total_orders * 100) if total_orders > 0 else 100.0

    latency_logs = audit_base.filter(
        domain.AuditLog.action_type.in_(EXECUTED_ACTIONS),
        domain.AuditLog.metadata_json.op("->>")("latency_ms").isnot(None),
    ).with_entities(domain.AuditLog.metadata_json).all()
    latencies = [
        log[0]["latency_ms"]
        for log in latency_logs
        if log[0] and log[0].get("latency_ms") is not None
    ]
    trade_latencies = [t.execution_latency_ms for t in closed_trades if t.execution_latency_ms is not None]
    all_latencies = latencies + trade_latencies
    avg_latency_ms = sum(all_latencies) / len(all_latencies) if all_latencies else 0.0

    rankings = _rank_best_worst(db, closed_trades) if snapshot_type == "GLOBAL" else {}
    exchange_dist = _exchange_distribution(audit_base)
    advanced_metrics = _calculate_advanced_metrics(
        db, start_date=start_date, end_date=end_date,
        portfolio_pk=portfolio_pk, strategy_name=strategy_name,
    )

    chart_data = {
        "equity_curve": advanced_metrics.get("equity_curve", []),
        "cumulative_pnl": advanced_metrics.get("cumulative_pnl", []),
        "daily_pnl": advanced_metrics.get("daily_pnl", []),
        "weekly_pnl": advanced_metrics.get("weekly_pnl", []),
        "monthly_pnl": advanced_metrics.get("monthly_pnl", []),
        "drawdown_series": advanced_metrics.get("drawdown_series", []),
        "rolling_drawdown": advanced_metrics.get("rolling_drawdown", []),
        "daily_trades": advanced_metrics.get("daily_trades", []),
        "daily_returns": advanced_metrics.get("daily_returns", []),
        "rolling_win_rate": advanced_metrics.get("rolling_win_rate", []),
    }

    snapshot_key = _build_snapshot_key(snapshot_type, period_label, scope_id)

    return {
        "snapshot_key": snapshot_key,
        "snapshot_type": snapshot_type,
        "period": period_label,
        "scope_id": scope_id,
        "total_trades": total_trades,
        "total_orders": total_orders,
        "filled_orders": filled_orders,
        "rejected_orders": rejected_orders,
        "winning_trades": winning_trades,
        "losing_trades": losing_trades,
        "win_rate_pct": round(win_rate_pct, 2),
        "total_pnl": round(total_pnl, 2),
        "profit_factor": round(profit_factor, 2) if profit_factor is not None else None,
        "largest_win": round(largest_win, 2),
        "largest_loss": round(largest_loss, 2),
        "fill_rate_pct": round(fill_rate_pct, 2),
        "avg_latency_ms": round(avg_latency_ms, 2),
        "avg_return_pct": advanced_metrics.get("avg_return_pct", 0.0),
        "sharpe_ratio": advanced_metrics.get("sharpe_ratio"),
        "max_drawdown_pct": advanced_metrics.get("max_drawdown_pct", 0.0),
        "best_portfolio": rankings.get("best_portfolio"),
        "worst_portfolio": rankings.get("worst_portfolio"),
        "best_strategy": rankings.get("best_strategy"),
        "worst_strategy": rankings.get("worst_strategy"),
        "exchange_distribution": exchange_dist,
        "chart_data": chart_data,
    }


def _upsert_snapshot(db: Session, snapshot_data: dict[str, Any]) -> domain.ValidationSnapshot:
    existing = db.query(domain.ValidationSnapshot).filter(
        domain.ValidationSnapshot.snapshot_key == snapshot_data["snapshot_key"]
    ).first()
    payload = {k: v for k, v in snapshot_data.items() if k != "snapshot_key"}
    if existing:
        for key, value in payload.items():
            setattr(existing, key, value)
        return existing
    row = domain.ValidationSnapshot(snapshot_key=snapshot_data["snapshot_key"], **payload)
    db.add(row)
    return row


def _calculate_and_store_snapshot(
    db: Session,
    period_label: str,
    period_spec: int | str | None,
    snapshot_type: str = "GLOBAL",
    scope_id: str | None = None,
    portfolio_pk: int | None = None,
    strategy_name: str | None = None,
):
    logger.info(f"Calculating {snapshot_type} '{period_label}' snapshot scope={scope_id or 'GLOBAL'}...")
    snapshot_data = _build_snapshot_data(
        db,
        period_label=period_label,
        period_spec=period_spec,
        snapshot_type=snapshot_type,
        scope_id=scope_id,
        portfolio_pk=portfolio_pk,
        strategy_name=strategy_name,
    )
    _upsert_snapshot(db, snapshot_data)
    db.commit()
    logger.info(f"Updated '{snapshot_data['snapshot_key']}' PnL={snapshot_data['total_pnl']}")


def _distinct_autonomous_portfolios(db: Session) -> list[tuple[int, str]]:
    rows = (
        db.query(domain.Trade.portfolio_id, domain.Portfolio.id)
        .join(domain.Portfolio, domain.Portfolio.pk_id == domain.Trade.portfolio_id)
        .filter(domain.Trade.trade_source == PAPER_TRADE_SOURCE)
        .distinct()
        .all()
    )
    return [(pk, portfolio_id) for pk, portfolio_id in rows]


def _distinct_autonomous_strategies(db: Session) -> list[str]:
    rows = (
        db.query(domain.Trade.strategy_name)
        .filter(
            domain.Trade.trade_source == PAPER_TRADE_SOURCE,
            domain.Trade.strategy_name.isnot(None),
            domain.Trade.strategy_name != "",
        )
        .distinct()
        .all()
    )
    return [row[0] for row in rows]


def archive_snapshots_to_history(db: Session, archive_date: date | None = None) -> int:
    """Append today's snapshot rows to history (one row per snapshot_key per day)."""
    archive_date = archive_date or date.today()
    snapshots = db.query(domain.ValidationSnapshot).all()
    archived = 0

    for snapshot in snapshots:
        exists = db.query(domain.ValidationSnapshotHistory).filter(
            domain.ValidationSnapshotHistory.archive_date == archive_date,
            domain.ValidationSnapshotHistory.snapshot_key == snapshot.snapshot_key,
        ).first()
        if exists:
            continue

        db.add(domain.ValidationSnapshotHistory(
            archive_date=archive_date,
            snapshot_key=snapshot.snapshot_key,
            snapshot_type=snapshot.snapshot_type,
            period=snapshot.period,
            scope_id=snapshot.scope_id,
            total_trades=snapshot.total_trades,
            total_orders=snapshot.total_orders,
            filled_orders=snapshot.filled_orders,
            rejected_orders=snapshot.rejected_orders,
            best_portfolio=snapshot.best_portfolio,
            worst_portfolio=snapshot.worst_portfolio,
            best_strategy=snapshot.best_strategy,
            worst_strategy=snapshot.worst_strategy,
            exchange_distribution=snapshot.exchange_distribution,
            winning_trades=snapshot.winning_trades,
            losing_trades=snapshot.losing_trades,
            win_rate_pct=snapshot.win_rate_pct,
            total_pnl=snapshot.total_pnl,
            profit_factor=snapshot.profit_factor,
            sharpe_ratio=snapshot.sharpe_ratio,
            max_drawdown_pct=snapshot.max_drawdown_pct,
            avg_return_pct=snapshot.avg_return_pct,
            largest_win=snapshot.largest_win,
            largest_loss=snapshot.largest_loss,
            avg_latency_ms=snapshot.avg_latency_ms,
            fill_rate_pct=snapshot.fill_rate_pct,
            chart_data=snapshot.chart_data,
        ))
        archived += 1

    if archived:
        db.commit()
        logger.info(f"Archived {archived} validation snapshots for {archive_date}")
    return archived


def purge_old_validation_history(db: Session, retention_days: int = HISTORY_RETENTION_DAYS) -> int:
    cutoff = date.today() - timedelta(days=retention_days)
    deleted = db.query(domain.ValidationSnapshotHistory).filter(
        domain.ValidationSnapshotHistory.archive_date < cutoff
    ).delete()
    if deleted:
        db.commit()
        logger.info(f"Purged {deleted} validation history rows older than {cutoff}")
    return deleted


def compute_validation_for_date_range(
    db: Session,
    start_date: datetime,
    end_date: datetime,
    portfolio_id: str | None = None,
    strategy: str | None = None,
) -> dict[str, Any]:
    """On-demand validation metrics for an arbitrary date window."""
    portfolio_pk = None
    scope_id = None
    snapshot_type = "GLOBAL"
    if portfolio_id:
        portfolio = db.query(domain.Portfolio).filter(domain.Portfolio.id == portfolio_id).first()
        if not portfolio:
            raise ValueError(f"Portfolio not found: {portfolio_id}")
        portfolio_pk = portfolio.pk_id
        scope_id = portfolio.id
        snapshot_type = "PORTFOLIO"
    elif strategy:
        scope_id = strategy
        snapshot_type = "STRATEGY"

    period_label = "CUSTOM"
    data = _build_snapshot_data(
        db,
        period_label=period_label,
        period_spec=None,
        snapshot_type=snapshot_type,
        scope_id=scope_id,
        portfolio_pk=portfolio_pk,
        strategy_name=strategy,
        start_date=start_date,
        end_date=end_date,
    )
    data["period"] = period_label
    data["range_start"] = start_date.isoformat()
    data["range_end"] = end_date.isoformat()
    return data


def query_metric_timeseries(
    db: Session,
    snapshot_key: str,
    metric: str,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[dict[str, Any]]:
    if metric not in METRIC_TIMESERIES_FIELDS:
        raise ValueError(f"Unsupported metric: {metric}")

    query = db.query(domain.ValidationSnapshotHistory).filter(
        domain.ValidationSnapshotHistory.snapshot_key == snapshot_key
    )
    if start_date:
        query = query.filter(domain.ValidationSnapshotHistory.archive_date >= start_date)
    if end_date:
        query = query.filter(domain.ValidationSnapshotHistory.archive_date <= end_date)

    rows = query.order_by(domain.ValidationSnapshotHistory.archive_date.asc()).all()
    series = []
    for row in rows:
        value = getattr(row, metric)
        series.append({
            "date": row.archive_date.isoformat(),
            "time": int(datetime.combine(row.archive_date, datetime.min.time()).timestamp()),
            "value": float(value) if value is not None else None,
        })
    return series


def query_validation_history(
    db: Session,
    snapshot_key: str | None = None,
    snapshot_type: str | None = None,
    scope_id: str | None = None,
    period: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    limit: int = 100,
) -> list[domain.ValidationSnapshotHistory]:
    query = db.query(domain.ValidationSnapshotHistory)
    if snapshot_key:
        query = query.filter(domain.ValidationSnapshotHistory.snapshot_key == snapshot_key)
    if snapshot_type:
        query = query.filter(domain.ValidationSnapshotHistory.snapshot_type == snapshot_type.upper())
    if scope_id:
        query = query.filter(domain.ValidationSnapshotHistory.scope_id == scope_id)
    if period:
        query = query.filter(domain.ValidationSnapshotHistory.period == period.upper())
    if start_date:
        query = query.filter(domain.ValidationSnapshotHistory.archive_date >= start_date)
    if end_date:
        query = query.filter(domain.ValidationSnapshotHistory.archive_date <= end_date)
    return query.order_by(
        domain.ValidationSnapshotHistory.archive_date.desc(),
        domain.ValidationSnapshotHistory.snapshot_key.asc(),
    ).limit(limit).all()


def update_validation_snapshots_job():
    """Scheduled job: global + portfolio + strategy snapshots, daily archive, retention purge."""
    logger.info("Starting scheduled job: update_validation_snapshots")
    db: Session | None = None
    try:
        db = SessionLocal()

        for period_label, period_spec in SNAPSHOT_PERIODS:
            _calculate_and_store_snapshot(db, period_label=period_label, period_spec=period_spec)

        for portfolio_pk, portfolio_id in _distinct_autonomous_portfolios(db):
            for period_label, period_spec in SCOPED_SNAPSHOT_PERIODS:
                _calculate_and_store_snapshot(
                    db,
                    period_label=period_label,
                    period_spec=period_spec,
                    snapshot_type="PORTFOLIO",
                    scope_id=portfolio_id,
                    portfolio_pk=portfolio_pk,
                )

        for strategy_name in _distinct_autonomous_strategies(db):
            for period_label, period_spec in SCOPED_SNAPSHOT_PERIODS:
                _calculate_and_store_snapshot(
                    db,
                    period_label=period_label,
                    period_spec=period_spec,
                    snapshot_type="STRATEGY",
                    scope_id=strategy_name,
                    strategy_name=strategy_name,
                )

        archive_snapshots_to_history(db)
        purge_old_validation_history(db)
        logger.info("Finished scheduled job: update_validation_snapshots")
    except Exception as e:
        logger.error(f"Error during validation snapshot update: {e}", exc_info=True)
        if db:
            db.rollback()
    finally:
        if db:
            db.close()
