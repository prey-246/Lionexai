"""Multi-asset strategy signal overlays for fund simulation."""

from __future__ import annotations

import pandas as pd

from app.strategies import get_strategy

STRATEGY_KEYS = (
    "MOMENTUM",
    "TREND_FOLLOWING",
    "VOL_BREAKOUT",
    "MEAN_REVERSION",
    "CROSS_ASSET_ROTATION",
    "RISK_PARITY",
    "RELATIVE_STRENGTH",
)


def _ohlcv_from_panel(panel: pd.DataFrame, sym: str, idx: int) -> pd.DataFrame:
    close = panel[sym].iloc[: idx + 1].dropna()
    ts = close.index
    df = pd.DataFrame({
        "timestamp": ts,
        "open": close.values,
        "high": close.values,
        "low": close.values,
        "close": close.values,
        "volume": 1.0,
    })
    return df


def strategy_signal_at(panel: pd.DataFrame, sym: str, idx: int, strategy_key: str) -> float:
    """Return signal in [-1, 1] for one asset at simulation index."""
    if sym not in panel.columns or idx < 30:
        return 0.0
    df = _ohlcv_from_panel(panel, sym, idx)
    if len(df) < 30:
        return 0.0
    cls = get_strategy(strategy_key)
    if not cls:
        return 0.0
    try:
        sig_df = cls(df, {}).generate_signals()
        val = float(sig_df["signal"].iloc[-1])
        return max(-1.0, min(1.0, val))
    except Exception:
        return 0.0


def overlay_multipliers(
    panel: pd.DataFrame,
    idx: int,
    symbols: list[str],
    strategy_weights: dict[str, float],
) -> dict[str, float]:
    """Combine strategy signals into per-asset weight multipliers in [0.1, 2.0]."""
    if not strategy_weights:
        return {s: 1.0 for s in symbols}

    combined: dict[str, float] = {s: 0.0 for s in symbols}
    total_w = sum(strategy_weights.values()) or 1.0

    for strat, sw in strategy_weights.items():
        if sw <= 0:
            continue
        for sym in symbols:
            sig = strategy_signal_at(panel, sym, idx, strat)
            # Long-only overlay: negative signals reduce weight, positive increase
            adj = 1.0 + sig * 0.5
            combined[sym] += (sw / total_w) * adj

    mult: dict[str, float] = {}
    for sym in symbols:
        m = combined.get(sym, 1.0)
        mult[sym] = round(max(0.1, min(2.0, m)), 4)
    return mult


def score_strategies_weekly(
    panel: pd.DataFrame,
    idx: int,
    symbols: list[str],
    lookback: int = 63,
) -> dict[str, float]:
    """Score strategies on trailing window using signal-direction accuracy."""
    if idx < lookback + 5:
        return {k: 1.0 / len(STRATEGY_KEYS) for k in STRATEGY_KEYS}

    scores: dict[str, float] = {}
    start = max(lookback, idx - lookback)
    for strat in STRATEGY_KEYS:
        hits = 0
        total = 0
        for sym in symbols[:5]:
            if sym not in panel.columns:
                continue
            for j in range(start, idx, 10):
                sig = strategy_signal_at(panel, sym, j, strat)
                if abs(sig) < 0.01:
                    continue
                fwd_end = min(j + 5, idx)
                p0 = float(panel[sym].iloc[j])
                p1 = float(panel[sym].iloc[fwd_end])
                if p0 <= 0:
                    continue
                ret = p1 / p0 - 1.0
                total += 1
                if (sig > 0 and ret > 0) or (sig < 0 and ret < 0):
                    hits += 1
        scores[strat] = (hits / total) if total > 0 else 0.33

    total_score = sum(scores.values()) or 1.0
    return {k: v / total_score for k, v in scores.items()}
