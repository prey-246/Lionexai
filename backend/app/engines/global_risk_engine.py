"""Global Risk Engine — composite 0-100 score with explainable components."""

from __future__ import annotations

import logging
from dataclasses import dataclass, asdict
from typing import Any

from sqlalchemy.orm import Session

from app.models import domain
from app.engines.macro_intelligence import MacroIntelligenceEngine
from app.engines.regime_engine import RegimeEngine
from app.services import market_data_service

logger = logging.getLogger("nexa.global_risk_engine")


@dataclass
class GlobalRiskAssessment:
    global_risk_score: float
    risk_label: str
    explanation: str
    components: dict[str, Any]

    def to_dict(self) -> dict:
        return asdict(self)


class GlobalRiskEngine:
    """Fuses news sentiment, regimes, volatility, gold, FX proxy, and liquidity signals."""

    def __init__(self, db: Session):
        self.db = db

    def assess(self) -> GlobalRiskAssessment:
        macro = MacroIntelligenceEngine(self.db).latest()
        base_score = float(macro.global_risk_score) if macro else 50.0
        regime = macro.market_regime if macro else "SIDEWAYS"
        risk_on_off = macro.risk_on_off if macro else "NEUTRAL"

        components: dict[str, Any] = {
            "macro_base_score": round(base_score, 2),
            "market_regime": regime,
            "risk_on_off": risk_on_off,
        }

        # News sentiment aggregate
        sentiments = self.db.query(domain.MarketSensitivityScore).order_by(
            domain.MarketSensitivityScore.timestamp.desc()
        ).limit(20).all()
        if sentiments:
            avg = sum(s.score for s in sentiments if s.score is not None) / len(sentiments)
            components["news_sentiment_avg"] = round(avg, 3)
            components["news_source_count"] = len(sentiments)
            base_score += (-avg) * 15  # bearish sentiment increases risk
        else:
            components["news_sentiment_avg"] = 0.0
            components["news_source_count"] = 0

        # Volatility proxy from BTC
        vol_adj = self._volatility_component("BTC/USDT")
        components["btc_realized_vol_annualized"] = vol_adj.get("vol")
        base_score += vol_adj.get("risk_delta", 0)

        # Gold crisis / safe-haven
        gold_adj = self._momentum_component("XAUUSD", invert=True)
        components["gold_stress_signal"] = gold_adj
        base_score += gold_adj * 5

        # Dollar strength proxy via EURUSD
        fx_adj = self._momentum_component("EURUSD", invert=False)
        components["fx_usd_strength_proxy"] = fx_adj
        base_score += fx_adj * 3

        # Economic events density
        events = self.db.query(domain.EconomicEvent).count()
        components["economic_events_tracked"] = events
        if events == 0:
            base_score += 5  # low visibility → moderate uncertainty bump

        # Cross-asset correlation stress (simplified)
        corr_stress = self._correlation_stress(["BTC/USDT", "ETH/USDT", "XAUUSD"])
        components["cross_asset_correlation_stress"] = corr_stress
        base_score += corr_stress * 10

        # Phase 6: FRED macro inputs (VIX, yield curve, DXY)
        macro_v2 = self._macro_v2_component()
        components["macro_v2"] = macro_v2
        base_score += macro_v2.get("risk_delta", 0)

        score = max(0.0, min(100.0, round(base_score, 2)))
        label = self._label(score)
        explanation = self._explain(score, components)

        return GlobalRiskAssessment(
            global_risk_score=score,
            risk_label=label,
            explanation=explanation,
            components=components,
        )

    def _volatility_component(self, symbol: str) -> dict:
        df = market_data_service.get_bars_df(self.db, symbol, timeframe="1d", limit=60)
        if df is None or len(df) < 20:
            return {"vol": None, "risk_delta": 5}
        rets = df["close"].astype(float).pct_change().dropna()
        vol = float(rets.std() * (252 ** 0.5))
        delta = min(20, vol * 30) if vol > 0.5 else 0
        return {"vol": round(vol, 4), "risk_delta": round(delta, 2)}

    def _momentum_component(self, symbol: str, invert: bool = False) -> float:
        df = market_data_service.get_bars_df(self.db, symbol, timeframe="1d", limit=90)
        if df is None or len(df) < 30:
            return 0.0
        close = df["close"].astype(float)
        mom = float(close.iloc[-1] / close.iloc[-30] - 1.0)
        return round(-mom if invert else mom, 4)

    def _correlation_stress(self, symbols: list[str]) -> float:
        series = {}
        for sym in symbols:
            df = market_data_service.get_bars_df(self.db, sym, timeframe="1d", limit=60)
            if df is not None and len(df) >= 30:
                series[sym] = df["close"].astype(float).pct_change().dropna()
        if len(series) < 2:
            return 0.0
        import pandas as pd
        frame = pd.DataFrame(series).dropna()
        if frame.empty:
            return 0.0
        corr = frame.corr().values.mean()
        return round(float(corr), 4)

    def _macro_v2_component(self) -> dict[str, Any]:
        """FRED / stored macro snapshots — explainable, no black-box."""
        from app.services.providers.fred_provider import fetch_macro_snapshot

        latest = (
            self.db.query(domain.MacroDataSnapshot)
            .order_by(domain.MacroDataSnapshot.computed_at.desc())
            .first()
        )
        snap = latest.series_data if latest else {}
        if not snap:
            live = fetch_macro_snapshot()
            snap = live.get("series", {})
            inverted = live.get("yield_curve_inverted")
        else:
            inverted = (latest.risk_drivers or {}).get("yield_curve_inverted")

        risk_delta = 0.0
        drivers: list[str] = []

        vix = snap.get("VIXCLS", {}).get("latest", {}).get("value")
        if vix is not None:
            drivers.append(f"VIX {vix:.1f}")
            if vix > 30:
                risk_delta += 15
            elif vix > 20:
                risk_delta += 8

        spread = snap.get("T10Y2Y", {}).get("latest", {}).get("value")
        if spread is not None:
            drivers.append(f"10Y-2Y spread {spread:.2f}%")
            if spread < 0:
                risk_delta += 10

        if inverted:
            drivers.append("Yield curve inverted")
            risk_delta += 5

        dxy = snap.get("DTWEXBGS", {}).get("latest", {}).get("value")
        if dxy is not None:
            drivers.append(f"DXY proxy {dxy:.1f}")

        infl = snap.get("T10YIE", {}).get("latest", {}).get("value")
        if infl is not None:
            drivers.append(f"10Y breakeven inflation {infl:.2f}%")

        return {
            "risk_delta": round(risk_delta, 2),
            "risk_drivers": drivers,
            "data_available": bool(snap),
            "yield_curve_inverted": inverted,
        }

    def _label(self, score: float) -> str:
        if score >= 75:
            return "ELEVATED"
        if score >= 55:
            return "MODERATE"
        if score >= 35:
            return "BALANCED"
        return "LOW"

    def _explain(self, score: float, c: dict) -> str:
        parts = [
            f"Composite risk {score}/100 ({self._label(score)}).",
            f"Regime {c.get('market_regime')} / {c.get('risk_on_off')}.",
        ]
        if c.get("news_source_count", 0) > 0:
            parts.append(f"News sentiment avg {c.get('news_sentiment_avg'):+.2f} from {c['news_source_count']} scores.")
        else:
            parts.append("Limited NLP sentiment coverage — score partially data-deficient.")
        if c.get("btc_realized_vol_annualized"):
            parts.append(f"BTC annualized vol ~{c['btc_realized_vol_annualized']:.1%}.")
        macro = c.get("macro_v2", {})
        if macro.get("risk_drivers"):
            parts.append("Macro: " + "; ".join(macro["risk_drivers"]) + ".")
        elif not macro.get("data_available"):
            parts.append("Macro V2: set FRED_API_KEY for yield curve / VIX feeds.")
        return " ".join(parts)
