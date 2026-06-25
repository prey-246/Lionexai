"""Expanded regime taxonomy for optimization and ensemble weighting."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict

import pandas as pd

from app.engines.regime_engine import RegimeResult, classify_series, _annualized_vol

REGIMES_V2 = (
    "BULL_TREND",
    "BEAR_TREND",
    "SIDEWAYS",
    "HIGH_VOL",
    "LOW_VOL",
    "INFLATIONARY",
    "DEFLATIONARY",
    "CRISIS",
)


@dataclass
class RegimeV2Result:
    regime: str
    confidence: float
    base_regime: str
    indicators: Dict[str, float] = field(default_factory=dict)


def classify_series_v2(df: pd.DataFrame, inflation_proxy: float | None = None) -> RegimeV2Result:
    """Map base 4-regime + vol/inflation overlays into 8-regime taxonomy."""
    base = classify_series(df)
    if df is None or df.empty or len(df) < 30:
        return RegimeV2Result("SIDEWAYS", 0.2, "SIDEWAYS", {"reason": "insufficient_data"})

    close = df["close"].astype(float)
    returns = close.pct_change()
    vol = _annualized_vol(returns)
    vol_series = returns.rolling(20, min_periods=5).std() * math.sqrt(252)
    median_vol = float(vol_series.median()) if not vol_series.dropna().empty else vol
    vol_pct = float(vol_series.rank(pct=True).iloc[-1]) if len(vol_series.dropna()) > 5 else 0.5

    price = float(close.iloc[-1])
    ma200 = close.rolling(min(200, len(close)), min_periods=20).mean().iloc[-1]
    trend_up = price > float(ma200)

    indicators = dict(base.indicators)
    indicators["vol_percentile"] = round(vol_pct, 4)
    if inflation_proxy is not None:
        indicators["inflation_proxy"] = round(inflation_proxy, 4)

    if base.regime == "CRISIS":
        return RegimeV2Result("CRISIS", base.confidence, base.regime, indicators)

    if vol_pct >= 0.75 or vol > 1.4 * max(median_vol, 0.01):
        return RegimeV2Result("HIGH_VOL", min(0.9, base.confidence + 0.1), base.regime, indicators)
    if vol_pct <= 0.25:
        return RegimeV2Result("LOW_VOL", min(0.85, base.confidence + 0.05), base.regime, indicators)

    if inflation_proxy is not None:
        if inflation_proxy > 0.03:
            return RegimeV2Result("INFLATIONARY", 0.65, base.regime, indicators)
        if inflation_proxy < -0.01:
            return RegimeV2Result("DEFLATIONARY", 0.65, base.regime, indicators)

    if base.regime == "BULL" and trend_up:
        return RegimeV2Result("BULL_TREND", base.confidence, base.regime, indicators)
    if base.regime == "BEAR" and not trend_up:
        return RegimeV2Result("BEAR_TREND", base.confidence, base.regime, indicators)

    return RegimeV2Result("SIDEWAYS", base.confidence, base.regime, indicators)


# Data-driven ensemble priors (updated by optimization engine from backtests)
DEFAULT_ENSEMBLE_WEIGHTS: dict[str, dict[str, float]] = {
    "BULL_TREND": {
        "MOMENTUM": 0.35,
        "TREND_FOLLOWING": 0.30,
        "CROSS_ASSET_ROTATION": 0.20,
        "MEAN_REVERSION": 0.15,
    },
    "BEAR_TREND": {
        "RISK_PARITY": 0.35,
        "MEAN_REVERSION": 0.25,
        "TREND_FOLLOWING": 0.20,
        "CROSS_ASSET_ROTATION": 0.20,
    },
    "HIGH_VOL": {
        "RISK_PARITY": 0.40,
        "MEAN_REVERSION": 0.30,
        "VOL_BREAKOUT": 0.15,
        "MOMENTUM": 0.15,
    },
    "LOW_VOL": {
        "MOMENTUM": 0.30,
        "TREND_FOLLOWING": 0.30,
        "RELATIVE_STRENGTH": 0.25,
        "MEAN_REVERSION": 0.15,
    },
    "CRISIS": {
        "RISK_PARITY": 0.50,
        "MEAN_REVERSION": 0.30,
        "TREND_FOLLOWING": 0.20,
    },
    "SIDEWAYS": {
        "MEAN_REVERSION": 0.35,
        "RISK_PARITY": 0.30,
        "RELATIVE_STRENGTH": 0.20,
        "MOMENTUM": 0.15,
    },
}
