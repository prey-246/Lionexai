"""Per-asset and global market regime detection.

Classifies each active asset into BULL / BEAR / SIDEWAYS / CRISIS using trend
(50/200 MA structure + slope), momentum, realized volatility and drawdown. Results
are persisted to `market_regimes` and consumed by the AllocationEngine and the UI.
"""
import logging
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models import domain
from app.services import market_data_service

logger = logging.getLogger("nexa.regime_engine")

REGIMES = ("BULL", "BEAR", "SIDEWAYS", "CRISIS")


@dataclass
class RegimeResult:
    regime: str
    confidence: float
    indicators: Dict[str, float] = field(default_factory=dict)


def _annualized_vol(returns: pd.Series, window: int = 20, periods_per_year: int = 252) -> float:
    if len(returns) < 2:
        return 0.0
    r = returns.dropna().tail(window)
    if r.empty:
        return 0.0
    return float(r.std() * math.sqrt(periods_per_year))


def classify_series(df: pd.DataFrame) -> RegimeResult:
    """Classify a single asset's OHLCV history into a regime."""
    if df is None or df.empty or len(df) < 30:
        return RegimeResult("SIDEWAYS", 0.2, {"reason": "insufficient_data", "bars": float(len(df) if df is not None else 0)})

    close = df["close"].astype(float).reset_index(drop=True)
    n = len(close)

    ma_fast = close.rolling(window=min(50, n), min_periods=min(10, n)).mean()
    ma_slow = close.rolling(window=min(200, n), min_periods=min(20, n)).mean()

    price = float(close.iloc[-1])
    fast = float(ma_fast.iloc[-1])
    slow = float(ma_slow.iloc[-1])

    # Slope of the fast MA over the last ~10 bars (normalized).
    slope_window = min(10, n - 1)
    fast_prev = float(ma_fast.iloc[-1 - slope_window]) if n > slope_window else fast
    fast_slope = (fast - fast_prev) / fast_prev if fast_prev else 0.0

    returns = close.pct_change()
    vol = _annualized_vol(returns)
    vol_series = returns.rolling(20, min_periods=5).std() * math.sqrt(252)
    median_vol = float(vol_series.median()) if not vol_series.dropna().empty else vol

    mom_window = min(21, n - 1)
    momentum = (price / float(close.iloc[-1 - mom_window]) - 1.0) if n > mom_window else 0.0

    rolling_high = float(close.tail(min(60, n)).max())
    drawdown = (price / rolling_high - 1.0) if rolling_high else 0.0

    indicators = {
        "price": round(price, 6),
        "ma_fast": round(fast, 6),
        "ma_slow": round(slow, 6),
        "fast_slope": round(fast_slope, 6),
        "momentum_1m": round(momentum, 6),
        "ann_vol": round(vol, 6),
        "median_vol": round(median_vol, 6),
        "drawdown": round(drawdown, 6),
    }

    vol_spike = median_vol > 0 and vol > 1.6 * median_vol

    # CRISIS: deep drawdown with an accompanying volatility spike.
    if drawdown <= -0.18 and (vol_spike or vol > 0.9):
        conf = min(0.95, 0.6 + abs(drawdown))
        return RegimeResult("CRISIS", round(conf, 3), indicators)

    uptrend = price > fast and fast >= slow and fast_slope > 0
    downtrend = price < fast and fast <= slow and fast_slope < 0

    if uptrend and momentum > 0:
        conf = min(0.92, 0.55 + min(abs(momentum) * 2, 0.35))
        return RegimeResult("BULL", round(conf, 3), indicators)

    if downtrend and momentum < 0:
        conf = min(0.92, 0.55 + min(abs(momentum) * 2, 0.35))
        return RegimeResult("BEAR", round(conf, 3), indicators)

    # Flat / mixed -> sideways. Confidence higher when vol is low.
    conf = 0.5 if vol < median_vol else 0.4
    return RegimeResult("SIDEWAYS", round(conf, 3), indicators)


class RegimeEngine:
    def __init__(self, db: Session):
        self.db = db

    def classify_asset(self, symbol: str, timeframe: str = "1d") -> RegimeResult:
        df = market_data_service.get_bars_df(self.db, symbol, timeframe=timeframe, limit=400)
        return classify_series(df)

    def detect_all(self, store: bool = True) -> Dict[str, RegimeResult]:
        """Classify every active asset and (optionally) persist + compute the global regime."""
        assets = self.db.query(domain.Asset).filter(domain.Asset.is_active == True).all()
        results: Dict[str, RegimeResult] = {}
        for asset in assets:
            res = self.classify_asset(asset.symbol)
            results[asset.symbol] = res
            if store:
                self.db.add(domain.MarketRegime(
                    scope=asset.symbol,
                    regime=res.regime,
                    confidence=res.confidence,
                    indicators=res.indicators,
                ))

        global_res = self._global_regime(results)
        if store:
            self.db.add(domain.MarketRegime(
                scope="GLOBAL",
                regime=global_res.regime,
                confidence=global_res.confidence,
                indicators=global_res.indicators,
            ))
            self.db.commit()
        results["GLOBAL"] = global_res
        return results

    def _global_regime(self, results: Dict[str, RegimeResult]) -> RegimeResult:
        if not results:
            return RegimeResult("SIDEWAYS", 0.3, {})
        counts = {r: 0 for r in REGIMES}
        for res in results.values():
            counts[res.regime] = counts.get(res.regime, 0) + 1
        total = sum(counts.values()) or 1

        # Crisis dominates if a meaningful share of assets are in crisis.
        if counts["CRISIS"] / total >= 0.25:
            return RegimeResult("CRISIS", round(0.6 + counts["CRISIS"] / total * 0.3, 3), {"counts": counts})
        # Otherwise majority vote between bull/bear/sideways.
        dominant = max(("BULL", "BEAR", "SIDEWAYS"), key=lambda k: counts[k])
        conf = round(0.4 + counts[dominant] / total * 0.5, 3)
        return RegimeResult(dominant, conf, {"counts": counts})

    def latest_global(self) -> Optional[domain.MarketRegime]:
        return (
            self.db.query(domain.MarketRegime)
            .filter(domain.MarketRegime.scope == "GLOBAL")
            .order_by(domain.MarketRegime.detected_at.desc())
            .first()
        )


def run_regime_detection():
    """Scheduled job: refresh per-asset + global regimes."""
    db = SessionLocal()
    try:
        engine = RegimeEngine(db)
        results = engine.detect_all(store=True)
        logger.info("Regime detection complete. Global=%s", results.get("GLOBAL").regime if results.get("GLOBAL") else "n/a")
    except Exception as e:
        logger.error("Regime detection job failed: %s", e, exc_info=True)
        db.rollback()
    finally:
        db.close()
