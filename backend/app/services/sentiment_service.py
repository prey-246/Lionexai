"""Resolve AI sentiment scores with explicit coverage provenance."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.models import domain

# Symbols shown first on Intelligence Hub (have news keyword coverage)
PULSE_PRIORITY = [
    "BTC/USDT",
    "ETH/USDT",
    "SOL/USDT",
    "XAUUSD",
    "XAGUSD",
    "WTIUSD",
    "EURUSD",
    "GLOBAL_RISK",
]

ASSET_CLASS_PROXY = {
    "BOND": "GLOBAL_RISK",
    "SECTOR_ETF": "GLOBAL_RISK",
    "COMMODITY_BASKET": "WTIUSD",
    "VOLATILITY": "GLOBAL_RISK",
    "CRYPTO": "BTC/USDT",
    "METAL": "XAUUSD",
    "ENERGY": "WTIUSD",
    "FX": "EURUSD",
    "EQUITY_INDEX": "GLOBAL_RISK",
}


def _neutral_score(symbol: str, reason: str) -> domain.MarketSensitivityScore:
    return domain.MarketSensitivityScore(
        id=f"sens_{uuid.uuid4().hex[:12]}",
        symbol=symbol,
        score=0.0,
        contributing_factors={
            "coverage": "NONE",
            "reason": reason,
            "article_count": 0,
            "data_provenance": "INSUFFICIENT_DATA",
        },
        timestamp=datetime.utcnow(),
    )


SYMBOL_FALLBACK_PROXY = {
    "WTIUSD": "XLE",
    "EURUSD": "GBPUSD",
}


def resolve_sentiment(db: Session, symbol: str) -> domain.MarketSensitivityScore:
    """Return latest score, class proxy, or explicit neutral with coverage metadata."""
    row = (
        db.query(domain.MarketSensitivityScore)
        .filter(domain.MarketSensitivityScore.symbol == symbol)
        .order_by(domain.MarketSensitivityScore.timestamp.desc())
        .first()
    )
    if row:
        factors = dict(row.contributing_factors or {})
        factors.setdefault("coverage", "DIRECT")
        factors.setdefault("data_provenance", "NEWS_AGGREGATE")
        row.contributing_factors = factors
        return row

    asset = db.query(domain.Asset).filter(domain.Asset.symbol == symbol).first()
    if asset and asset.asset_class in ASSET_CLASS_PROXY:
        proxy_sym = ASSET_CLASS_PROXY[asset.asset_class]
        proxy = (
            db.query(domain.MarketSensitivityScore)
            .filter(domain.MarketSensitivityScore.symbol == proxy_sym)
            .order_by(domain.MarketSensitivityScore.timestamp.desc())
            .first()
        )
        if proxy:
            return domain.MarketSensitivityScore(
                id=f"sens_{uuid.uuid4().hex[:12]}",
                symbol=symbol,
                score=proxy.score,
                contributing_factors={
                    "coverage": "ASSET_CLASS_PROXY",
                    "proxy_symbol": proxy_sym,
                    "proxy_score": proxy.score,
                    "article_count": (proxy.contributing_factors or {}).get("article_count", 0),
                    "data_provenance": "PROXY",
                    "asset_class": asset.asset_class,
                },
                timestamp=proxy.timestamp,
            )

    fallback_sym = SYMBOL_FALLBACK_PROXY.get(symbol)
    if fallback_sym:
        fallback = (
            db.query(domain.MarketSensitivityScore)
            .filter(domain.MarketSensitivityScore.symbol == fallback_sym)
            .order_by(domain.MarketSensitivityScore.timestamp.desc())
            .first()
        )
        if fallback:
            return domain.MarketSensitivityScore(
                id=f"sens_{uuid.uuid4().hex[:12]}",
                symbol=symbol,
                score=fallback.score,
                contributing_factors={
                    "coverage": "ASSET_CLASS_PROXY",
                    "proxy_symbol": fallback_sym,
                    "proxy_score": fallback.score,
                    "article_count": (fallback.contributing_factors or {}).get("article_count", 0),
                    "data_provenance": "PROXY",
                },
                timestamp=fallback.timestamp,
            )

    return _neutral_score(symbol, "No NLP news coverage for this symbol yet.")


def list_pulse_scores(db: Session, limit: int = 12) -> list[domain.MarketSensitivityScore]:
    """Priority symbols with direct or proxy sentiment for the Intelligence Hub."""
    seen: set[str] = set()
    out: list[domain.MarketSensitivityScore] = []
    for sym in PULSE_PRIORITY:
        if sym in seen:
            continue
        seen.add(sym)
        out.append(resolve_sentiment(db, sym))
        if len(out) >= limit:
            return out

    latest = (
        db.query(domain.MarketSensitivityScore)
        .order_by(domain.MarketSensitivityScore.timestamp.desc())
        .limit(limit * 2)
        .all()
    )
    for row in latest:
        if row.symbol in seen:
            continue
        seen.add(row.symbol)
        out.append(resolve_sentiment(db, row.symbol))
        if len(out) >= limit:
            break
    return out
