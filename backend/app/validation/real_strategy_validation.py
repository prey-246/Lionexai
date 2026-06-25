"""Real strategy validation on historical market data — never mixed with demo ledger metrics."""

from __future__ import annotations

import logging
import math
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import Any

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from app.models import domain
from app.services import market_data_service
from app.strategies import get_strategy

logger = logging.getLogger("nexa.real_strategy_validation")

RISK_FREE_RATE = 0.04  # annualized approx for Sharpe/Sortino


@dataclass
class ValidationRunResult:
    run_id: str
    strategy_key: str
    symbol: str
    validation_type: str  # BACKTEST, WALK_FORWARD, MONTE_CARLO, OUT_OF_SAMPLE, REGIME_SEGMENT
    period_start: datetime | None
    period_end: datetime | None
    metrics: dict[str, Any] = field(default_factory=dict)
    regime_breakdown: dict[str, Any] = field(default_factory=dict)
    equity_curve: list[dict] = field(default_factory=list)
    data_source: str = "HISTORICAL_MARKET_BARS"
    provenance: str = "VALIDATED_HISTORICAL"

    def to_dict(self) -> dict:
        return asdict(self)


class RealStrategyValidator:
    """Run strategies against stored OHLCV with institutional metrics."""

    def __init__(self, db: Session):
        self.db = db

    def run_single_asset_backtest(
        self,
        symbol: str,
        strategy_key: str,
        initial_capital: float = 100_000.0,
        limit: int = 2000,
        strategy_params: dict | None = None,
        commission_pct: float = 0.1,
        slippage_pct: float = 0.1,
    ) -> ValidationRunResult:
        df = market_data_service.get_bars_df(self.db, symbol, timeframe="1d", limit=limit)
        if df is None or df.empty or len(df) < 60:
            raise ValueError(f"Insufficient historical bars for {symbol}. Run market backfill first.")

        df = df.copy()
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("timestamp").reset_index(drop=True)

        strategy_cls = get_strategy(strategy_key)
        if not strategy_cls:
            raise ValueError(f"Unknown strategy: {strategy_key}")

        strat = strategy_cls(df, strategy_params or {})
        sig_df = strat.generate_signals()
        portfolio = self._simulate_portfolio(
            sig_df, initial_capital, commission_pct, slippage_pct,
        )
        metrics = self._compute_metrics(portfolio, initial_capital)
        curve = [
            {"time": int(row["timestamp"].timestamp()), "value": float(row["equity"])}
            for _, row in portfolio.iterrows()
        ]

        return ValidationRunResult(
            run_id=f"vsr_{uuid.uuid4().hex[:12]}",
            strategy_key=strategy_key.upper(),
            symbol=symbol,
            validation_type="BACKTEST",
            period_start=df["timestamp"].iloc[0].to_pydatetime(),
            period_end=df["timestamp"].iloc[-1].to_pydatetime(),
            metrics=metrics,
            equity_curve=curve,
        )

    def run_walk_forward(
        self,
        symbol: str,
        strategy_key: str,
        train_days: int = 252,
        test_days: int = 63,
        initial_capital: float = 100_000.0,
    ) -> ValidationRunResult:
        df = market_data_service.get_bars_df(self.db, symbol, timeframe="1d", limit=2000)
        if df is None or len(df) < train_days + test_days + 30:
            raise ValueError("Not enough data for walk-forward test.")

        df = df.copy()
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("timestamp").reset_index(drop=True)

        oos_returns: list[float] = []
        windows: list[dict] = []
        equity = initial_capital

        start = 0
        while start + train_days + test_days <= len(df):
            train = df.iloc[start : start + train_days]
            test = df.iloc[start + train_days : start + train_days + test_days]
            combined = pd.concat([train, test]).reset_index(drop=True)

            strategy_cls = get_strategy(strategy_key)
            strat = strategy_cls(combined, {})
            sig = strat.generate_signals()
            test_sig = sig.iloc[-len(test):].copy()
            port = self._simulate_portfolio(test_sig, equity, 0.1, 0.1)
            window_ret = (port["equity"].iloc[-1] / port["equity"].iloc[0] - 1.0) if len(port) > 1 else 0.0
            oos_returns.append(window_ret)
            equity = float(port["equity"].iloc[-1])
            windows.append({
                "train_end": str(train["timestamp"].iloc[-1]),
                "test_end": str(test["timestamp"].iloc[-1]),
                "oos_return_pct": round(window_ret * 100, 2),
            })
            start += test_days

        avg_oos = np.mean(oos_returns) * 100 if oos_returns else 0.0
        return ValidationRunResult(
            run_id=f"vsr_{uuid.uuid4().hex[:12]}",
            strategy_key=strategy_key.upper(),
            symbol=symbol,
            validation_type="WALK_FORWARD",
            period_start=df["timestamp"].iloc[0].to_pydatetime(),
            period_end=df["timestamp"].iloc[-1].to_pydatetime(),
            metrics={
                "windows": len(windows),
                "avg_oos_return_pct": round(float(avg_oos), 2),
                "oos_win_rate_pct": round(
                    sum(1 for r in oos_returns if r > 0) / max(len(oos_returns), 1) * 100, 2
                ),
                "final_equity": round(equity, 2),
            },
            regime_breakdown={"windows": windows},
        )

    def run_monte_carlo(
        self,
        symbol: str,
        strategy_key: str,
        simulations: int = 500,
        initial_capital: float = 100_000.0,
    ) -> ValidationRunResult:
        base = self.run_single_asset_backtest(symbol, strategy_key, initial_capital)
        rets = pd.Series([p["value"] for p in base.equity_curve]).pct_change().dropna()
        if rets.empty:
            raise ValueError("No return series for Monte Carlo.")

        horizon = len(rets)
        sim_finals: list[float] = []
        for _ in range(simulations):
            sampled = np.random.choice(rets.values, size=horizon, replace=True)
            path = initial_capital * np.cumprod(1 + sampled)
            sim_finals.append(float(path[-1]))

        sim_finals_arr = np.array(sim_finals)
        return ValidationRunResult(
            run_id=f"vsr_{uuid.uuid4().hex[:12]}",
            strategy_key=strategy_key.upper(),
            symbol=symbol,
            validation_type="MONTE_CARLO",
            period_start=base.period_start,
            period_end=base.period_end,
            metrics={
                **base.metrics,
                "simulations": simulations,
                "mc_median_final": round(float(np.median(sim_finals_arr)), 2),
                "mc_p5_final": round(float(np.percentile(sim_finals_arr, 5)), 2),
                "mc_p95_final": round(float(np.percentile(sim_finals_arr, 95)), 2),
                "mc_prob_loss_pct": round(float((sim_finals_arr < initial_capital).mean() * 100), 2),
            },
        )

    def evaluate_alpha_monthly_target(
        self,
        fund_id: str = "ALPHA",
        target_monthly_pct: float = 20.0,
        symbols: list[str] | None = None,
    ) -> dict[str, Any]:
        """Evidence framework: can Alpha strategies achieve target on historical data?"""
        fund = self.db.query(domain.Fund).filter(domain.Fund.id == fund_id).first()
        if not fund:
            raise ValueError(f"Fund {fund_id} not found")

        if symbols is None:
            symbols = [fau.asset.symbol for fau in fund.asset_universe if fau.asset][:5]

        strategies = ["MOMENTUM", "TREND_FOLLOWING", "VOL_BREAKOUT", "CROSS_ASSET_ROTATION", "RISK_PARITY"]
        results: list[dict] = []
        for strat in strategies:
            for sym in symbols:
                try:
                    run = self.run_single_asset_backtest(sym, strat)
                    m = run.metrics
                    monthly = m.get("avg_monthly_return_pct", 0)
                    meets = monthly >= target_monthly_pct
                    results.append({
                        "strategy": strat,
                        "symbol": sym,
                        "monthly_return_pct": monthly,
                        "cagr_pct": m.get("cagr_pct"),
                        "max_drawdown_pct": m.get("max_drawdown_pct"),
                        "sharpe": m.get("sharpe_ratio"),
                        "meets_20pct_monthly": meets,
                    })
                except Exception as e:
                    results.append({"strategy": strat, "symbol": sym, "error": str(e)})

        best = max(
            (r for r in results if "monthly_return_pct" in r),
            key=lambda x: x["monthly_return_pct"],
            default=None,
        )
        any_meets = any(r.get("meets_20pct_monthly") for r in results)
        return {
            "fund_id": fund_id,
            "target_monthly_compounded_pct": target_monthly_pct,
            "conclusion": "NOT_SUPPORTED" if not any_meets else "PARTIALLY_SUPPORTED",
            "evidence_summary": (
                f"Best historical monthly return: {best['monthly_return_pct']}% "
                f"({best['strategy']} on {best['symbol']})"
                if best else "No successful backtests."
            ),
            "any_strategy_meets_target": any_meets,
            "results": results,
            "provenance": "VALIDATED_HISTORICAL",
            "disclaimer": "Historical backtest ≠ future performance. Demo ledger returns are excluded.",
        }

    def persist_run(self, result: ValidationRunResult) -> domain.ValidatedStrategyRun:
        row = domain.ValidatedStrategyRun(
            id=result.run_id,
            strategy_key=result.strategy_key,
            symbol=result.symbol,
            validation_type=result.validation_type,
            period_start=result.period_start,
            period_end=result.period_end,
            metrics=result.metrics,
            regime_breakdown=result.regime_breakdown,
            equity_curve=result.equity_curve,
            data_source=result.data_source,
            provenance=result.provenance,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def _simulate_portfolio(
        self,
        df: pd.DataFrame,
        initial_capital: float,
        commission_pct: float,
        slippage_pct: float,
    ) -> pd.DataFrame:
        """Position-sized long-only simulation on daily signals."""
        df = df.copy()
        if "signal" not in df.columns:
            df["signal"] = 0
        df["position"] = df["signal"].clip(0, 1)
        df["position"] = df["position"].ffill().fillna(0)

        cash = initial_capital
        shares = 0.0
        equities: list[float] = []

        for i, row in df.iterrows():
            price = float(row["close"])
            target_pos = float(row["position"])
            target_value = cash + shares * price
            desired_shares = (target_value * target_pos) / price if price > 0 else 0
            delta = desired_shares - shares
            if abs(delta) * price > 1.0:
                notional = abs(delta) * price
                cost = notional * (commission_pct + slippage_pct) / 100.0
                if delta > 0 and cash >= notional + cost:
                    cash -= notional + cost
                    shares += delta
                elif delta < 0:
                    cash += abs(delta) * price - cost
                    shares += delta
            equities.append(cash + shares * price)

        out = df.copy()
        out["equity"] = equities
        return out

    def _compute_metrics(self, portfolio: pd.DataFrame, initial_capital: float) -> dict[str, Any]:
        eq = portfolio["equity"].astype(float)
        rets = eq.pct_change().dropna()
        if rets.empty:
            return {}

        days = max((portfolio["timestamp"].iloc[-1] - portfolio["timestamp"].iloc[0]).days, 1)
        years = days / 365.25
        final = float(eq.iloc[-1])
        total_return = (final / initial_capital - 1.0) * 100
        cagr = ((final / initial_capital) ** (1 / years) - 1) * 100 if years > 0 else 0.0

        rolling_max = eq.cummax()
        dd = (eq / rolling_max - 1.0)
        max_dd = abs(float(dd.min()) * 100)

        ann_vol = float(rets.std() * np.sqrt(252) * 100) if len(rets) > 1 else 0.0
        excess = rets - RISK_FREE_RATE / 252
        sharpe = float(excess.mean() / excess.std() * np.sqrt(252)) if excess.std() > 0 else 0.0
        downside = rets[rets < 0]
        sortino = (
            float(excess.mean() / downside.std() * np.sqrt(252))
            if len(downside) > 0 and downside.std() > 0
            else 0.0
        )
        calmar = float(cagr / max_dd) if max_dd > 0 else 0.0

        monthly = pd.Series(eq.values, index=pd.DatetimeIndex(pd.to_datetime(portfolio["timestamp"])))
        monthly = monthly.resample("ME").last().pct_change().dropna()
        avg_monthly = float(monthly.mean() * 100) if len(monthly) else 0.0

        # Round-trip trades from position changes
        pos_diff = portfolio["position"].diff().fillna(0)
        trade_pnls: list[float] = []
        entry_price = None
        for i, d in pos_diff.items():
            if d > 0:
                entry_price = float(portfolio.loc[i, "close"])
            elif d < 0 and entry_price:
                trade_pnls.append(float(portfolio.loc[i, "close"]) - entry_price)
                entry_price = None

        wins = [p for p in trade_pnls if p > 0]
        losses = [abs(p) for p in trade_pnls if p < 0]
        win_rate = len(wins) / len(trade_pnls) * 100 if trade_pnls else 0.0
        profit_factor = sum(wins) / sum(losses) if losses else None
        expectancy = float(np.mean(trade_pnls)) if trade_pnls else 0.0
        recovery = float(total_return / max_dd) if max_dd > 0 else 0.0

        return {
            "cagr_pct": round(cagr, 2),
            "annualized_return_pct": round(cagr, 2),
            "total_return_pct": round(total_return, 2),
            "avg_monthly_return_pct": round(avg_monthly, 2),
            "win_rate_pct": round(win_rate, 2),
            "sharpe_ratio": round(sharpe, 2),
            "sortino_ratio": round(sortino, 2),
            "calmar_ratio": round(calmar, 2),
            "max_drawdown_pct": round(max_dd, 2),
            "profit_factor": round(profit_factor, 2) if profit_factor else None,
            "recovery_factor": round(recovery, 2),
            "expectancy": round(expectancy, 4),
            "volatility_pct": round(ann_vol, 2),
            "total_trades": len(trade_pnls),
            "final_equity": round(final, 2),
        }
