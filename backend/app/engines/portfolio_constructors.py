"""Portfolio weight constructors for historical fund simulation."""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

from app.engines.regime_engine import _annualized_vol

VOL_FLOOR = 0.05
MOMENTUM_K = 2.0


def _returns_matrix(panel: pd.DataFrame, idx: int, window: int = 63) -> pd.DataFrame:
    start = max(0, idx - window)
    sub = panel.iloc[start : idx + 1].pct_change().dropna(how="all")
    return sub


def equal_weight(symbols: list[str], invested_pct: float, caps: dict[str, float]) -> dict[str, float]:
    if not symbols:
        return {}
    w = invested_pct / len(symbols)
    return {s: round(min(w, caps.get(s, 100.0)), 4) for s in symbols}


def inverse_vol_weights(
    panel: pd.DataFrame,
    idx: int,
    symbols: list[str],
    invested_pct: float,
    caps: dict[str, float],
    momentum_boost: bool = False,
) -> dict[str, float]:
    raw: dict[str, float] = {}
    for sym in symbols:
        hist = panel[sym].iloc[: idx + 1].dropna()
        if len(hist) < 20:
            continue
        vol = max(_annualized_vol(hist.pct_change()), VOL_FLOOR)
        score = 1.0 / vol
        if momentum_boost:
            mom_w = min(63, len(hist) - 1)
            mom = float(hist.iloc[-1] / hist.iloc[-1 - mom_w] - 1.0) if len(hist) > mom_w else 0.0
            score *= 1.0 + max(mom, 0.0) * MOMENTUM_K
        raw[sym] = max(score, 0.0)
    return _normalize(raw, invested_pct, caps)


def risk_parity_weights(
    panel: pd.DataFrame,
    idx: int,
    symbols: list[str],
    invested_pct: float,
    caps: dict[str, float],
    window: int = 63,
) -> dict[str, float]:
    rets = _returns_matrix(panel, idx, window)
    raw: dict[str, float] = {}
    for sym in symbols:
        if sym not in rets.columns:
            continue
        vol = float(rets[sym].std() * math.sqrt(252))
        vol = max(vol, VOL_FLOOR)
        raw[sym] = 1.0 / vol
    return _normalize(raw, invested_pct, caps)


def min_variance_weights(
    panel: pd.DataFrame,
    idx: int,
    symbols: list[str],
    invested_pct: float,
    caps: dict[str, float],
    window: int = 63,
) -> dict[str, float]:
    rets = _returns_matrix(panel, idx, window)
    avail = [s for s in symbols if s in rets.columns and rets[s].notna().sum() >= 10]
    if len(avail) < 1:
        return {}
    var = rets[avail].var()
    raw = {s: 1.0 / max(float(var[s]), VOL_FLOOR ** 2) for s in avail}
    return _normalize(raw, invested_pct, caps)


def max_diversification_weights(
    panel: pd.DataFrame,
    idx: int,
    symbols: list[str],
    invested_pct: float,
    caps: dict[str, float],
    window: int = 63,
) -> dict[str, float]:
    rets = _returns_matrix(panel, idx, window)
    avail = [s for s in symbols if s in rets.columns and rets[s].notna().sum() >= 10]
    if len(avail) < 2:
        return inverse_vol_weights(panel, idx, avail or symbols, invested_pct, caps)
    corr = rets[avail].corr().fillna(0)
    raw: dict[str, float] = {}
    for sym in avail:
        others = [s for s in avail if s != sym]
        avg_corr = float(corr.loc[sym, others].abs().mean()) if others else 0.0
        vol = max(float(rets[sym].std() * math.sqrt(252)), VOL_FLOOR)
        raw[sym] = (1.0 - avg_corr) / vol
    return _normalize(raw, invested_pct, caps)


def relative_strength_weights(
    panel: pd.DataFrame,
    idx: int,
    symbols: list[str],
    invested_pct: float,
    caps: dict[str, float],
    lookback: int = 63,
    top_k: int | None = None,
) -> dict[str, float]:
    scores: dict[str, float] = {}
    for sym in symbols:
        hist = panel[sym].iloc[: idx + 1].dropna()
        lb = min(lookback, len(hist) - 1)
        if lb < 5:
            continue
        ret = float(hist.iloc[-1] / hist.iloc[-1 - lb] - 1.0)
        if ret > 0:
            scores[sym] = ret
    if top_k:
        ranked = sorted(scores, key=scores.get, reverse=True)[:top_k]
        scores = {s: scores[s] for s in ranked}
    return _normalize(scores, invested_pct, caps)


def _normalize(raw: dict[str, float], invested_pct: float, caps: dict[str, float]) -> dict[str, float]:
    total = sum(raw.values())
    if total <= 0:
        return {}
    weights = {}
    for sym, r in raw.items():
        tgt = (r / total) * invested_pct
        weights[sym] = round(min(tgt, caps.get(sym, 100.0)), 4)
    return weights


def apply_regime_multipliers(
    weights: dict[str, float],
    asset_regimes: dict[str, str],
    global_regime: str,
    risk_on_off: str,
    safe_havens: set[str],
) -> dict[str, float]:
    adjusted: dict[str, float] = {}
    for sym, w in weights.items():
        mult = 1.0
        ar = asset_regimes.get(sym, "SIDEWAYS")
        if ar == "BULL":
            mult *= 1.25
        elif ar == "BEAR":
            mult *= 0.4
        elif ar == "CRISIS":
            mult *= 0.1
        if risk_on_off == "RISK_OFF" and sym in safe_havens:
            mult *= 1.5
        adjusted[sym] = w * mult
    total = sum(adjusted.values())
    if total <= 0:
        return {}
    scale = sum(weights.values()) / total
    return {s: round(v * scale, 4) for s, v in adjusted.items()}


def build_weights(
    method: str,
    panel: pd.DataFrame,
    idx: int,
    symbols: list[str],
    invested_pct: float,
    caps: dict[str, float],
    max_assets: int = 8,
) -> dict[str, float]:
    method = method.lower()
    if method == "equal_weight":
        syms = symbols[:max_assets]
        return equal_weight(syms, invested_pct, caps)
    if method == "inverse_vol":
        w = inverse_vol_weights(panel, idx, symbols, invested_pct, caps, momentum_boost=False)
    elif method == "regime_momentum":
        w = inverse_vol_weights(panel, idx, symbols, invested_pct, caps, momentum_boost=True)
    elif method == "risk_parity":
        w = risk_parity_weights(panel, idx, symbols, invested_pct, caps)
    elif method == "min_variance":
        w = min_variance_weights(panel, idx, symbols, invested_pct, caps)
    elif method == "max_diversification":
        w = max_diversification_weights(panel, idx, symbols, invested_pct, caps)
    elif method == "relative_strength":
        w = relative_strength_weights(panel, idx, symbols, invested_pct, caps, top_k=max_assets)
    else:
        w = inverse_vol_weights(panel, idx, symbols, invested_pct, caps, momentum_boost=False)

    if len(w) > max_assets:
        top = sorted(w, key=w.get, reverse=True)[:max_assets]
        w = {s: w[s] for s in top}
        tot = sum(w.values())
        if tot > 0:
            scale = invested_pct / tot
            w = {s: round(v * scale, 4) for s, v in w.items()}
    return w
