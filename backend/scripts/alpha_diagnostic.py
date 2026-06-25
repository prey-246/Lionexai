#!/usr/bin/env python3
"""Phase 1 root-cause diagnostic — asset returns, costs, regime exposure."""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
from app.core.database import SessionLocal
from app.models import domain
from app.services import market_data_service
from app.analytics import performance_engine as pe


def asset_buy_hold_metrics(db, symbol: str, limit: int = 2000) -> dict:
    df = market_data_service.get_bars_df(db, symbol, limit=limit)
    if df.empty or len(df) < 30:
        return {"symbol": symbol, "status": "insufficient"}
    close = df.set_index(pd.to_datetime(df["timestamp"]))["close"].astype(float)
    rets = close.pct_change().dropna()
    cagr = pe.cagr_pct(close)
    mdd = pe.max_drawdown_pct(close)
    sharpe = pe.sharpe_ratio(rets)
    total = (close.iloc[-1] / close.iloc[0] - 1) * 100
    return {
        "symbol": symbol,
        "status": "ok",
        "total_return_pct": round(total, 2),
        "cagr_pct": cagr,
        "sharpe_ratio": sharpe,
        "max_drawdown_pct": mdd,
        "bars": len(df),
    }


def analyze_fund_run(db, fund_id: str) -> dict:
    run = (
        db.query(domain.ValidatedFundRun)
        .filter(domain.ValidatedFundRun.fund_id == fund_id)
        .order_by(domain.ValidatedFundRun.created_at.desc())
        .first()
    )
    if not run:
        return {"fund_id": fund_id, "error": "no run"}
    m = run.metrics or {}
    log = run.rebalance_log or []
    costs = sum(r.get("trade_cost", 0) for r in log)
    regimes = {}
    for r in log:
        reg = r.get("regime", "?")
        regimes[reg] = regimes.get(reg, 0) + 1
    cash_pcts = [r.get("cash_pct", 0) for r in log if r.get("cash_pct") is not None]
    avg_cash = round(sum(cash_pcts) / len(cash_pcts), 2) if cash_pcts else None
    return {
        "fund_id": fund_id,
        "run_id": run.id,
        "metrics": m,
        "policy": run.allocation_policy_snapshot,
        "period": f"{run.period_start} → {run.period_end}",
        "rebalance_count": len(log),
        "total_trade_cost": round(costs, 2),
        "cost_pct_of_initial": round(costs / run.initial_capital * 100, 3) if run.initial_capital else None,
        "regime_distribution": regimes,
        "avg_cash_pct_at_rebalance": avg_cash,
        "symbols": m.get("symbols_used"),
    }


def correlation_matrix(db, symbols: list, limit: int = 500) -> dict:
    frames = {}
    for sym in symbols:
        df = market_data_service.get_bars_df(db, sym, limit=limit)
        if not df.empty:
            frames[sym] = df.set_index(pd.to_datetime(df["timestamp"]))["close"].astype(float)
    if len(frames) < 2:
        return {}
    panel = pd.DataFrame(frames).dropna()
    corr = panel.pct_change().dropna().corr()
    return {sym: {k: round(float(corr.loc[sym, k]), 3) for k in corr.columns} for sym in corr.index}


def main():
    db = SessionLocal()
    try:
        symbols = [a[0] for a in [
            ("BTC/USDT",), ("ETH/USDT",), ("SOL/USDT",), ("XAUUSD",), ("XAGUSD",),
            ("WTIUSD",), ("SPX",), ("NDX",), ("EURUSD",), ("GBPUSD",),
        ]]
        assets = [asset_buy_hold_metrics(db, s) for s in symbols]
        funds = [analyze_fund_run(db, f) for f in ("PRESERVE", "BALANCE", "ALPHA")]
        corr = correlation_matrix(db, [a["symbol"] for a in assets if a.get("status") == "ok"])
        out = {"assets_buy_hold": assets, "fund_runs": funds, "correlation": corr}
        print(json.dumps(out, indent=2, default=str))
    finally:
        db.close()


if __name__ == "__main__":
    main()
