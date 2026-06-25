"""Global Market Intelligence: risk score, regime, risk-on/off and asset ranking.

Aggregates per-asset price behaviour (from `market_bars`) with existing sentiment
(`market_sensitivity_scores`) and economic-event severity (`economic_events`) into a
single `global_market_state` snapshot the AllocationEngine and UI consume.
"""
import logging
import math
from datetime import datetime, timedelta
from typing import Dict, List

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models import domain
from app.services import market_data_service
from app.engines.regime_engine import RegimeEngine, _annualized_vol

logger = logging.getLogger("nexa.macro_intelligence")

SAFE_HAVENS = {"XAUUSD", "XAGUSD"}
EQUITY_INDICES = {"SPX", "NDX"}


def _clamp(x: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, x))


class MacroIntelligenceEngine:
    def __init__(self, db: Session):
        self.db = db

    def _asset_metrics(self) -> Dict[str, Dict[str, float]]:
        assets = self.db.query(domain.Asset).filter(domain.Asset.is_active == True).all()
        metrics: Dict[str, Dict[str, float]] = {}
        for asset in assets:
            df = market_data_service.get_bars_df(self.db, asset.symbol, timeframe="1d", limit=200)
            if df is None or df.empty or len(df) < 20:
                continue
            close = df["close"].astype(float).reset_index(drop=True)
            returns = close.pct_change()
            vol = _annualized_vol(returns)
            mom_window = min(63, len(close) - 1)  # ~3 months
            momentum = (float(close.iloc[-1]) / float(close.iloc[-1 - mom_window]) - 1.0) if len(close) > mom_window else 0.0
            rolling_high = float(close.tail(min(90, len(close))).max())
            drawdown = (float(close.iloc[-1]) / rolling_high - 1.0) if rolling_high else 0.0
            risk_adj_mom = momentum / vol if vol > 1e-9 else momentum
            metrics[asset.symbol] = {
                "asset_class": asset.asset_class,
                "vol": round(vol, 6),
                "momentum_3m": round(momentum, 6),
                "drawdown": round(drawdown, 6),
                "risk_adjusted_momentum": round(risk_adj_mom, 6),
            }
        return metrics

    def _avg_sentiment(self) -> float:
        cutoff = datetime.utcnow() - timedelta(days=3)
        rows = (
            self.db.query(domain.MarketSensitivityScore.score)
            .filter(domain.MarketSensitivityScore.timestamp >= cutoff)
            .all()
        )
        if not rows:
            return 0.0
        return float(np.mean([r[0] for r in rows]))

    def _econ_severity(self) -> int:
        cutoff = datetime.utcnow() - timedelta(days=3)
        from sqlalchemy import func as sa_func
        return (
            self.db.query(domain.EconomicEvent)
            .filter(
                domain.EconomicEvent.timestamp >= cutoff,
                sa_func.upper(domain.EconomicEvent.impact) == "HIGH",
            )
            .count()
        )

    def compute(self, store: bool = True) -> domain.GlobalMarketState:
        metrics = self._asset_metrics()

        # --- Cross-asset volatility component (0..100) ---
        vols = [m["vol"] for m in metrics.values()] or [0.3]
        avg_vol = float(np.mean(vols))
        # Map vol 0.10 -> ~10, 0.80 -> ~80 (crypto-heavy universe runs hot).
        vol_component = _clamp(avg_vol * 110.0)

        # --- Equity drawdown component ---
        eq_dd = [abs(m["drawdown"]) for s, m in metrics.items() if s in EQUITY_INDICES]
        dd_component = _clamp((max(eq_dd) if eq_dd else 0.0) * 300.0)  # -15% dd -> ~45

        # --- Sentiment component (negative sentiment -> higher risk) ---
        sentiment = self._avg_sentiment()  # -1..1
        sentiment_component = _clamp(50.0 - sentiment * 50.0)

        # --- Economic event severity ---
        severity = self._econ_severity()
        econ_component = _clamp(min(severity, 8) / 8.0 * 100.0)

        # --- Safe-haven behaviour (gold up while equities down -> risk-off) ---
        gold_mom = np.mean([metrics[s]["momentum_3m"] for s in SAFE_HAVENS if s in metrics]) if any(s in metrics for s in SAFE_HAVENS) else 0.0
        eq_mom = np.mean([metrics[s]["momentum_3m"] for s in EQUITY_INDICES if s in metrics]) if any(s in metrics for s in EQUITY_INDICES) else 0.0
        haven_signal = float(gold_mom) - float(eq_mom)
        haven_component = _clamp(50.0 + haven_signal * 150.0)

        risk_score = _clamp(
            0.34 * vol_component
            + 0.22 * dd_component
            + 0.20 * sentiment_component
            + 0.12 * econ_component
            + 0.12 * haven_component
        )

        # --- Global regime from RegimeEngine ---
        regime_engine = RegimeEngine(self.db)
        latest = regime_engine.latest_global()
        if latest:
            market_regime = latest.regime
        else:
            results = regime_engine.detect_all(store=False)
            market_regime = results.get("GLOBAL").regime if results.get("GLOBAL") else "SIDEWAYS"
        if risk_score >= 78:
            market_regime = "CRISIS"

        # --- Risk on/off ---
        if risk_score >= 60:
            risk_on_off = "RISK_OFF"
        elif risk_score <= 40:
            risk_on_off = "RISK_ON"
        else:
            risk_on_off = "NEUTRAL"

        # --- Asset ranking (risk-adjusted momentum, regime-tilted) ---
        ranking = self._rank_assets(metrics, risk_on_off)

        macro_inputs = {
            "avg_vol": round(avg_vol, 6),
            "vol_component": round(vol_component, 2),
            "dd_component": round(dd_component, 2),
            "sentiment": round(sentiment, 4),
            "sentiment_component": round(sentiment_component, 2),
            "econ_high_impact_events": severity,
            "econ_component": round(econ_component, 2),
            "haven_signal": round(haven_signal, 6),
            "haven_component": round(haven_component, 2),
        }

        state = domain.GlobalMarketState(
            global_risk_score=round(risk_score, 2),
            market_regime=market_regime,
            risk_on_off=risk_on_off,
            asset_ranking=ranking,
            macro_inputs=macro_inputs,
        )
        if store:
            self.db.add(state)
            self.db.commit()
            self.db.refresh(state)
        return state

    def _rank_assets(self, metrics: Dict[str, Dict[str, float]], risk_on_off: str) -> List[Dict]:
        scored = []
        for symbol, m in metrics.items():
            score = m["risk_adjusted_momentum"]
            # In risk-off, tilt toward safe havens; in risk-on, tilt toward growth/crypto.
            if risk_on_off == "RISK_OFF" and symbol in SAFE_HAVENS:
                score += 0.5
            if risk_on_off == "RISK_ON" and m["asset_class"] == "CRYPTO":
                score += 0.3
            scored.append({
                "symbol": symbol,
                "asset_class": m["asset_class"],
                "score": round(float(score), 4),
                "momentum_3m": m["momentum_3m"],
                "vol": m["vol"],
            })
        scored.sort(key=lambda x: x["score"], reverse=True)
        for i, row in enumerate(scored):
            row["rank"] = i + 1
        return scored

    def latest(self) -> domain.GlobalMarketState | None:
        return (
            self.db.query(domain.GlobalMarketState)
            .order_by(domain.GlobalMarketState.computed_at.desc())
            .first()
        )


def run_global_market_state():
    """Scheduled job: compute and persist the latest global market state."""
    db = SessionLocal()
    try:
        engine = MacroIntelligenceEngine(db)
        state = engine.compute(store=True)
        logger.info(
            "Global market state: risk=%.1f regime=%s risk_on_off=%s",
            state.global_risk_score, state.market_regime, state.risk_on_off,
        )
    except Exception as e:
        logger.error("Global market state job failed: %s", e, exc_info=True)
        db.rollback()
    finally:
        db.close()
