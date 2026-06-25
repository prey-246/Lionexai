"""Asset classification layer for multi-asset expansion."""

from __future__ import annotations

from typing import Any

from app.models import domain

# Extended asset registry — bonds, ETFs, vol products, commodity baskets
EXTENDED_ASSETS: list[dict[str, Any]] = [
    {"symbol": "TLT", "display_name": "iShares 20+ Year Treasury Bond ETF", "asset_class": "BOND", "data_provider": "yfinance", "data_symbol": "TLT", "region": "US", "risk_tier": "LOW", "liquidity_score": 95, "volatility_score": 25},
    {"symbol": "IEF", "display_name": "iShares 7-10 Year Treasury ETF", "asset_class": "BOND", "data_provider": "yfinance", "data_symbol": "IEF", "region": "US", "risk_tier": "LOW", "liquidity_score": 92, "volatility_score": 20},
    {"symbol": "SHY", "display_name": "iShares 1-3 Year Treasury ETF", "asset_class": "BOND", "data_provider": "yfinance", "data_symbol": "SHY", "region": "US", "risk_tier": "LOW", "liquidity_score": 90, "volatility_score": 10},
    {"symbol": "XLK", "display_name": "Technology Select Sector SPDR", "asset_class": "SECTOR_ETF", "data_provider": "yfinance", "data_symbol": "XLK", "region": "US", "risk_tier": "MEDIUM", "liquidity_score": 95, "volatility_score": 55},
    {"symbol": "XLF", "display_name": "Financial Select Sector SPDR", "asset_class": "SECTOR_ETF", "data_provider": "yfinance", "data_symbol": "XLF", "region": "US", "risk_tier": "MEDIUM", "liquidity_score": 93, "volatility_score": 50},
    {"symbol": "XLE", "display_name": "Energy Select Sector SPDR", "asset_class": "SECTOR_ETF", "data_provider": "yfinance", "data_symbol": "XLE", "region": "US", "risk_tier": "HIGH", "liquidity_score": 90, "volatility_score": 65},
    {"symbol": "VXX", "display_name": "iPath Series B S&P 500 VIX Short-Term Futures ETN", "asset_class": "VOLATILITY", "data_provider": "yfinance", "data_symbol": "VXX", "region": "US", "risk_tier": "HIGH", "liquidity_score": 75, "volatility_score": 95},
    {"symbol": "UVXY", "display_name": "ProShares Ultra VIX Short-Term Futures ETF", "asset_class": "VOLATILITY", "data_provider": "yfinance", "data_symbol": "UVXY", "region": "US", "risk_tier": "EXTREME", "liquidity_score": 70, "volatility_score": 98},
    {"symbol": "DBC", "display_name": "Invesco DB Commodity Index Tracking Fund", "asset_class": "COMMODITY_BASKET", "data_provider": "yfinance", "data_symbol": "DBC", "region": "GLOBAL", "risk_tier": "MEDIUM", "liquidity_score": 80, "volatility_score": 45},
    {"symbol": "GSG", "display_name": "iShares S&P GSCI Commodity-Indexed Trust", "asset_class": "COMMODITY_BASKET", "data_provider": "yfinance", "data_symbol": "GSG", "region": "GLOBAL", "risk_tier": "MEDIUM", "liquidity_score": 78, "volatility_score": 48},
    {"symbol": "TIP", "display_name": "iShares TIPS Bond ETF", "asset_class": "BOND", "data_provider": "yfinance", "data_symbol": "TIP", "region": "US", "risk_tier": "LOW", "liquidity_score": 88, "volatility_score": 18},
    {"symbol": "HYG", "display_name": "iShares iBoxx High Yield Corporate Bond ETF", "asset_class": "BOND", "data_provider": "yfinance", "data_symbol": "HYG", "region": "US", "risk_tier": "MEDIUM", "liquidity_score": 85, "volatility_score": 40},
]

RISK_TIER_LIMITS = {
    "LOW": {"max_weight_pct": 40, "max_leverage": 1.0},
    "MEDIUM": {"max_weight_pct": 25, "max_leverage": 1.5},
    "HIGH": {"max_weight_pct": 15, "max_leverage": 2.0},
    "EXTREME": {"max_weight_pct": 5, "max_leverage": 1.0},
}


def classify_asset(asset: domain.Asset) -> dict[str, Any]:
    return {
        "symbol": asset.symbol,
        "asset_class": asset.asset_class,
        "region": getattr(asset, "region", None) or "GLOBAL",
        "risk_tier": getattr(asset, "risk_tier", None) or _default_risk_tier(asset.asset_class),
        "liquidity_score": getattr(asset, "liquidity_score", None) or 50,
        "volatility_score": getattr(asset, "volatility_score", None) or 50,
    }


def _default_risk_tier(asset_class: str) -> str:
    mapping = {
        "BOND": "LOW",
        "SECTOR_ETF": "MEDIUM",
        "VOLATILITY": "EXTREME",
        "COMMODITY_BASKET": "MEDIUM",
        "CRYPTO": "HIGH",
        "METAL": "MEDIUM",
        "FX": "MEDIUM",
        "ENERGY": "HIGH",
        "EQUITY_INDEX": "MEDIUM",
    }
    return mapping.get(asset_class, "MEDIUM")


def seed_extended_assets(db) -> int:
    """Idempotently register Phase 6 multi-asset instruments."""
    added = 0
    for spec in EXTENDED_ASSETS:
        existing = db.query(domain.Asset).filter(domain.Asset.symbol == spec["symbol"]).first()
        if existing:
            for key in ("region", "risk_tier", "liquidity_score", "volatility_score", "asset_class"):
                if spec.get(key) is not None:
                    setattr(existing, key, spec[key])
            continue
        db.add(domain.Asset(
            symbol=spec["symbol"],
            display_name=spec["display_name"],
            asset_class=spec["asset_class"],
            data_provider=spec.get("data_provider", "yfinance"),
            data_symbol=spec.get("data_symbol", spec["symbol"]),
            execution_venue="SIMULATED",
            region=spec.get("region", "GLOBAL"),
            risk_tier=spec.get("risk_tier", "MEDIUM"),
            liquidity_score=spec.get("liquidity_score", 50),
            volatility_score=spec.get("volatility_score", 50),
        ))
        added += 1
    db.commit()
    return added


def risk_constraints_for_portfolio(db, portfolio: domain.Portfolio) -> dict[str, Any]:
    """Aggregate classification constraints for allocation/risk engines."""
    allocations = (
        db.query(domain.PortfolioAllocation)
        .filter(domain.PortfolioAllocation.portfolio_id == portfolio.pk_id)
        .all()
    )
    constraints = []
    for alloc in allocations:
        asset = db.query(domain.Asset).filter(domain.Asset.pk_id == alloc.asset_pk_id).first()
        if not asset:
            continue
        cls = classify_asset(asset)
        tier = cls["risk_tier"]
        limits = RISK_TIER_LIMITS.get(tier, RISK_TIER_LIMITS["MEDIUM"])
        constraints.append({**cls, **limits, "target_weight_pct": alloc.target_weight_pct})
    return {"portfolio_id": portfolio.id, "assets": constraints}
