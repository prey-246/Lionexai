"""Single source of truth for portfolio, fund, validation, and treasury analytics.

All return-based metrics derive from equity curves (not dollar PnL).
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Sequence

import numpy as np
import pandas as pd
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import domain

logger = logging.getLogger("nexa.performance_engine")

PROVENANCE = ("DEMO", "VALIDATED_HISTORICAL", "PAPER_LIVE", "LIVE_CAPITAL")
TRADING_DAYS = 252
RISK_FREE_DAILY = 0.0


def _native(v: float | None) -> float | None:
    if v is None or (isinstance(v, float) and (np.isnan(v) or np.isinf(v))):
        return None
    return round(float(v), 4)


def equity_series_from_curves(curves: Sequence[domain.EquityCurve]) -> pd.Series:
    """Daily equity indexed by date (last point per calendar day)."""
    if not curves:
        return pd.Series(dtype=float)
    rows = [{"ts": c.timestamp.replace(hour=0, minute=0, second=0, microsecond=0), "equity": float(c.equity)} for c in curves]
    df = pd.DataFrame(rows).sort_values("ts")
    df = df.groupby("ts", as_index=True)["equity"].last()
    return df


def daily_returns_from_equity(equity: pd.Series) -> pd.Series:
    if equity.empty or len(equity) < 2:
        return pd.Series(dtype=float)
    return equity.pct_change().dropna()


def sharpe_ratio(returns: pd.Series, annualization: int = TRADING_DAYS) -> float | None:
    if returns.empty or len(returns) < 2:
        return None
    excess = returns - RISK_FREE_DAILY
    std = excess.std()
    if std == 0 or np.isnan(std):
        return None
    return _native(float(excess.mean() / std * np.sqrt(annualization)))


def sortino_ratio(returns: pd.Series, annualization: int = TRADING_DAYS) -> float | None:
    if returns.empty or len(returns) < 2:
        return None
    excess = returns - RISK_FREE_DAILY
    downside = excess[excess < 0]
    if downside.empty:
        return _native(float(excess.mean() / 1e-9 * np.sqrt(annualization)))
    dd_std = downside.std()
    if dd_std == 0 or np.isnan(dd_std):
        return None
    return _native(float(excess.mean() / dd_std * np.sqrt(annualization)))


def max_drawdown_pct(equity: pd.Series) -> float:
    if equity.empty:
        return 0.0
    peak = equity.cummax()
    dd = np.where(peak > 0, (peak - equity) / peak, 0.0)
    return _native(float(np.max(dd) * 100)) or 0.0


def volatility_annualized(returns: pd.Series, annualization: int = TRADING_DAYS) -> float | None:
    if returns.empty or len(returns) < 2:
        return None
    return _native(float(returns.std() * np.sqrt(annualization)))


def rolling_metric(series: pd.Series, window: int, fn) -> list[dict[str, Any]]:
    if series.empty:
        return []
    out = []
    for i in range(len(series)):
        start = max(0, i - window + 1)
        chunk = series.iloc[start : i + 1]
        val = fn(chunk)
        ts = series.index[i]
        out.append({"time": int(pd.Timestamp(ts).timestamp()), "value": val})
    return out


def period_return_pct(equity: pd.Series, days: int) -> float | None:
    if equity.empty or len(equity) < 2:
        return None
    last = equity.iloc[-1]
    if last <= 0:
        return None
    cutoff = equity.index[-1] - pd.Timedelta(days=days)
    baseline = equity.iloc[0]
    for ts, val in equity.items():
        if ts <= cutoff:
            baseline = val
    if baseline <= 0:
        return None
    return _native((last / baseline - 1.0) * 100)


def cagr_pct(equity: pd.Series) -> float | None:
    if equity.empty or len(equity) < 2:
        return None
    start, end = equity.iloc[0], equity.iloc[-1]
    if start <= 0 or end <= 0:
        return None
    days = max(1, (equity.index[-1] - equity.index[0]).days)
    years = days / 365.25
    if years <= 0:
        return None
    return _native(((end / start) ** (1 / years) - 1) * 100)


def calmar_ratio(cagr: float | None, max_dd_pct: float) -> float | None:
    if cagr is None or max_dd_pct <= 0:
        return None
    return _native(cagr / max_dd_pct)


def profit_factor_from_trades(trades: list[domain.Trade]) -> float | None:
    gross_profit = sum(t.pnl for t in trades if t.pnl and t.pnl > 0)
    gross_loss = abs(sum(t.pnl for t in trades if t.pnl and t.pnl < 0))
    if gross_loss <= 0:
        return None if gross_profit <= 0 else _native(float("inf"))
    return _native(gross_profit / gross_loss)


def win_rate_from_trades(trades: list[domain.Trade]) -> float | None:
    closed = [t for t in trades if t.pnl is not None]
    if not closed:
        return None
    wins = sum(1 for t in closed if t.pnl > 0)
    return _native(wins / len(closed) * 100)


def detect_provenance_from_trades(trades: list[domain.Trade]) -> str:
    if not trades:
        return "UNKNOWN"
    simulated = sum(1 for t in trades if (t.exchange or "").lower() == "simulated")
    ratio = simulated / len(trades)
    if ratio >= 0.95:
        return "DEMO"
    if ratio <= 0.05:
        return "PAPER_LIVE"
    return "MIXED"


class PerformanceEngine:
    """Unified analytics for portfolios, funds, validation, and treasury."""

    def __init__(self, db: Session):
        self.db = db

    def portfolio_equity_analytics(
        self,
        portfolio_pk: int,
        days: int | None = None,
    ) -> dict[str, Any]:
        q = (
            self.db.query(domain.EquityCurve)
            .filter(domain.EquityCurve.portfolio_id == portfolio_pk)
            .order_by(domain.EquityCurve.timestamp.asc())
        )
        if days:
            since = datetime.utcnow() - timedelta(days=days)
            q = q.filter(domain.EquityCurve.timestamp >= since)
        curves = q.all()
        equity = equity_series_from_curves(curves)
        returns = daily_returns_from_equity(equity)

        trades_q = self.db.query(domain.Trade).filter(domain.Trade.portfolio_id == portfolio_pk)
        if days:
            trades_q = trades_q.filter(domain.Trade.created_at >= datetime.utcnow() - timedelta(days=days))
        trades = trades_q.all()
        closed = [t for t in trades if t.status == "CLOSED" and t.pnl is not None]

        cagr = cagr_pct(equity)
        mdd = max_drawdown_pct(equity)
        return {
            "daily_return_pct": period_return_pct(equity, 1),
            "weekly_return_pct": period_return_pct(equity, 7),
            "monthly_return_pct": period_return_pct(equity, 30),
            "total_return_pct": period_return_pct(equity, 3650) if not equity.empty else None,
            "cagr_pct": cagr,
            "sharpe_ratio": sharpe_ratio(returns),
            "sortino_ratio": sortino_ratio(returns),
            "volatility_annualized": volatility_annualized(returns),
            "max_drawdown_pct": mdd,
            "calmar_ratio": calmar_ratio(cagr, mdd),
            "win_rate_pct": win_rate_from_trades(closed),
            "profit_factor": profit_factor_from_trades(closed),
            "equity_curve": [
                {"time": int(pd.Timestamp(ts).timestamp()), "value": float(v)}
                for ts, v in equity.items()
            ],
            "rolling_sharpe": rolling_metric(returns, 30, lambda r: sharpe_ratio(r) or 0),
            "rolling_sortino": rolling_metric(returns, 30, lambda r: sortino_ratio(r) or 0),
            "rolling_drawdown": rolling_metric(
                equity, 30, lambda e: max_drawdown_pct(e) if len(e) > 1 else 0
            ),
            "data_provenance": detect_provenance_from_trades(trades),
            "sample_days": len(equity),
        }

    def fund_analytics(self, fund: domain.Fund) -> dict[str, Any]:
        """Fund analytics — prefers validated historical backtest over demo ledger."""
        from app.services.validated_fund_service import validated_fund_metrics

        validated = validated_fund_metrics(self.db, fund.id)
        if validated:
            return {
                "fund_id": fund.id,
                "fund_name": fund.name,
                "data_provenance": "VALIDATED_HISTORICAL",
                "portfolio_count": (
                    self.db.query(domain.Portfolio)
                    .filter(domain.Portfolio.fund_pk_id == fund.pk_id, domain.Portfolio.auto_managed == True)
                    .count()
                ),
                "target_weekly_return_pct": fund.target_weekly_return_pct,
                "target_monthly_return_pct": fund.target_monthly_return_pct,
                "realized_total_return_pct": validated.get("total_return_pct"),
                "realized_weekly_return_pct": validated.get("avg_weekly_return_pct"),
                "realized_monthly_return_pct": validated.get("avg_monthly_return_pct"),
                "validated_monthly_return_pct": validated.get("avg_monthly_return_pct"),
                "cagr_pct": validated.get("cagr_pct"),
                "sharpe_ratio": validated.get("sharpe_ratio"),
                "sortino_ratio": validated.get("sortino_ratio"),
                "max_drawdown_pct": validated.get("max_drawdown_pct"),
                "calmar_ratio": validated.get("calmar_ratio"),
                "win_rate_pct": validated.get("win_rate_pct"),
                "yield_delivery_pct": validated.get("yield_delivery_pct"),
                "treasury_contributions": None,
            }

        portfolios = (
            self.db.query(domain.Portfolio)
            .filter(domain.Portfolio.fund_pk_id == fund.pk_id, domain.Portfolio.auto_managed == True)
            .all()
        )
        if not portfolios:
            return {"fund_id": fund.id, "data_provenance": "UNKNOWN", "portfolio_count": 0}

        weights = [p.total_equity or 0 for p in portfolios]
        total_aum = sum(weights)
        agg: dict[str, list[tuple[float, float | None]]] = {
            k: [] for k in (
                "weekly_return_pct", "monthly_return_pct", "sharpe_ratio", "sortino_ratio",
                "max_drawdown_pct", "cagr_pct", "calmar_ratio", "win_rate_pct",
            )
        }
        provenances: list[str] = []
        for p in portfolios:
            w = p.total_equity or 0
            pa = self.portfolio_equity_analytics(p.pk_id)
            provenances.append(pa.get("data_provenance", "UNKNOWN"))
            for key in agg:
                v = pa.get(key)
                if v is not None:
                    agg[key].append((w, v))

        def wavg(pairs: list[tuple[float, float | None]]) -> float | None:
            valid = [(w, v) for w, v in pairs if v is not None and w > 0]
            if not valid:
                return None
            tw = sum(w for w, _ in valid)
            return _native(sum(w * v for w, v in valid) / tw)

        total_principal = sum(p.principal or p.total_equity or 0 for p in portfolios)
        realized_total = None
        if total_principal > 0:
            realized_total = _native((total_aum / total_principal - 1) * 100)

        # Validated historical from fund-level backtest table
        validated_run = (
            self.db.query(domain.ValidatedFundRun)
            .filter(domain.ValidatedFundRun.fund_id == fund.id)
            .order_by(domain.ValidatedFundRun.created_at.desc())
            .first()
        )
        validated_monthly = None
        if validated_run and validated_run.metrics:
            validated_monthly = validated_run.metrics.get("avg_monthly_return_pct")

        prov = "MIXED"
        if all(p == "DEMO" for p in provenances):
            prov = "DEMO"
        elif all(p == "PAPER_LIVE" for p in provenances):
            prov = "PAPER_LIVE"

        settlements = self.db.query(domain.ClientSettlement).filter(
            domain.ClientSettlement.portfolio_id.in_([p.pk_id for p in portfolios])
        ).all()
        treasury_contrib = sum(s.excess_routed or 0 for s in settlements)
        delivered = sum(1 for s in settlements if (s.uncovered or 0) <= 0)
        yield_pct = _native(delivered / len(settlements) * 100) if settlements else None

        return {
            "fund_id": fund.id,
            "fund_name": fund.name,
            "portfolio_count": len(portfolios),
            "client_count": len({p.user_id for p in portfolios}),
            "total_aum": _native(total_aum),
            "target_weekly_return_pct": fund.target_weekly_return_pct,
            "target_monthly_return_pct": fund.target_monthly_return_pct,
            "realized_total_return_pct": realized_total,
            "realized_weekly_return_pct": wavg(agg["weekly_return_pct"]),
            "realized_monthly_return_pct": wavg(agg["monthly_return_pct"]),
            "validated_monthly_return_pct": validated_monthly,
            "sharpe_ratio": wavg(agg["sharpe_ratio"]),
            "sortino_ratio": wavg(agg["sortino_ratio"]),
            "max_drawdown_pct": wavg(agg["max_drawdown_pct"]),
            "cagr_pct": wavg(agg["cagr_pct"]),
            "calmar_ratio": wavg(agg["calmar_ratio"]),
            "win_rate_pct": wavg(agg["win_rate_pct"]),
            "treasury_contributions": _native(treasury_contrib),
            "yield_delivery_pct": yield_pct,
            "data_provenance": prov,
        }

    def treasury_analytics(self, start: datetime | None = None) -> dict[str, Any]:
        pools = self.db.query(domain.TreasuryPool).all()
        nav = sum(p.balance or 0 for p in pools)
        tx_q = self.db.query(domain.TreasuryTransaction)
        if start:
            tx_q = tx_q.filter(domain.TreasuryTransaction.timestamp >= start)
        txs = tx_q.order_by(domain.TreasuryTransaction.timestamp.asc()).all()

        growth_pct = 0.0
        if txs and nav > 0:
            first_nav_proxy = txs[0].amount if txs else nav
            if first_nav_proxy > 0:
                growth_pct = _native((nav / first_nav_proxy - 1) * 100) or 0.0

        lnx_pool = next((p for p in pools if p.id == "LNX_INDEX"), None)
        lnx_snaps = (
            self.db.query(domain.LNXIndexSnapshot)
            .order_by(domain.LNXIndexSnapshot.computed_at.desc())
            .limit(2)
            .all()
        )
        lnx_growth = 0.0
        if len(lnx_snaps) >= 2 and lnx_snaps[1].composite_index:
            lnx_growth = _native((lnx_snaps[0].composite_index / lnx_snaps[1].composite_index - 1) * 100) or 0.0

        return {
            "treasury_nav": _native(nav),
            "treasury_growth_pct": growth_pct,
            "lnx_pool_balance": _native(lnx_pool.balance if lnx_pool else 0),
            "lnx_growth_pct": lnx_growth,
            "pool_breakdown": {p.id: _native(p.balance) for p in pools},
            "transaction_count": len(txs),
            "data_provenance": "DEMO" if not txs else "PAPER_LIVE",
        }

    def validation_extended_metrics(self, start: datetime | None = None, end: datetime | None = None) -> dict[str, Any]:
        """Phase 4 extended metrics — equity-based, not dollar PnL."""
        fund_portfolios = self.db.query(domain.Portfolio).filter(domain.Portfolio.auto_managed == True).all()
        if not fund_portfolios:
            return {}

        total_aum = sum(p.total_equity or 0 for p in fund_portfolios)
        total_principal = sum(p.principal or p.total_equity or 0 for p in fund_portfolios)
        fund_performance_pct = _native((total_aum / total_principal - 1) * 100) if total_principal > 0 else 0.0

        treasury = self.treasury_analytics(start)

        settlements_q = self.db.query(domain.ClientSettlement)
        if start:
            settlements_q = settlements_q.filter(domain.ClientSettlement.period_end >= start)
        if end:
            settlements_q = settlements_q.filter(domain.ClientSettlement.period_end <= end)
        settlements = settlements_q.all()
        delivered = sum(1 for s in settlements if (s.uncovered or 0) <= 0 and s.status == "SETTLED")
        client_yield_delivery_pct = _native(delivered / len(settlements) * 100) if settlements else 100.0

        # Asset performance from equity allocation drift proxy — use closed trade return %
        trades = self.db.query(domain.Trade).filter(domain.Trade.status == "CLOSED", domain.Trade.pnl.isnot(None))
        if start:
            trades = trades.filter(domain.Trade.closed_at >= start)
        trades = trades.all()
        asset_returns: dict[str, list[float]] = {}
        for t in trades:
            if not t.symbol or not t.entry_price or not t.quantity:
                continue
            notional = t.entry_price * t.quantity
            if notional <= 0:
                continue
            ret = (t.pnl or 0) / notional * 100
            asset_returns.setdefault(t.symbol, []).append(ret)
        top_asset = max(asset_returns, key=lambda s: sum(asset_returns[s]) / len(asset_returns[s])) if asset_returns else None
        asset_performance_pct = None
        if top_asset:
            asset_performance_pct = _native(sum(asset_returns[top_asset]) / len(asset_returns[top_asset]))

        return {
            "fund_performance_pct": fund_performance_pct,
            "asset_performance_pct": asset_performance_pct,
            "top_asset_symbol": top_asset,
            "treasury_growth_pct": treasury.get("treasury_growth_pct"),
            "treasury_nav": treasury.get("treasury_nav"),
            "lnx_growth_pct": treasury.get("lnx_growth_pct"),
            "client_yield_delivery_pct": client_yield_delivery_pct,
            "data_provenance": detect_provenance_from_trades(trades),
        }

    def aggregate_fund_equity_curve(self, fund: domain.Fund) -> list[dict[str, Any]]:
        """Weighted aggregate equity curve — validated historical preferred over demo."""
        from app.services.validated_fund_service import get_latest_validated_fund_run

        validated = get_latest_validated_fund_run(self.db, fund.id)
        if validated and validated.equity_curve:
            return validated.equity_curve

        portfolios = (
            self.db.query(domain.Portfolio)
            .filter(domain.Portfolio.fund_pk_id == fund.pk_id, domain.Portfolio.auto_managed == True)
            .all()
        )
        if not portfolios:
            return []
        series_map: dict[int, float] = {}
        for p in portfolios:
            curves = (
                self.db.query(domain.EquityCurve)
                .filter(domain.EquityCurve.portfolio_id == p.pk_id)
                .order_by(domain.EquityCurve.timestamp.asc())
                .all()
            )
            eq = equity_series_from_curves(curves)
            w = p.total_equity or 1.0
            for ts, val in eq.items():
                t = int(pd.Timestamp(ts).timestamp())
                series_map[t] = series_map.get(t, 0) + val * w
        return [{"time": t, "value": round(v, 2)} for t, v in sorted(series_map.items())]
