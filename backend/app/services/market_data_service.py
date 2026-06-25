"""Unified multi-asset market-data service.

Routes OHLCV / live-price requests to the correct provider based on
`Asset.data_provider`, persists candles into the unified `market_bars` table, and
exposes convenience readers (pandas DataFrame / latest close) used by the regime
and allocation engines. Replaces the Binance-only market_data/historical_data path
for Phase 4 consumers while leaving the legacy services intact for back-compat.
"""
import logging
from datetime import datetime
from typing import List, Optional, Any

import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert

from app.core.database import SessionLocal
from app.models import domain
from app.services.providers import get_provider

logger = logging.getLogger("nexa.market_data_service")

DEFAULT_TIMEFRAME = "1d"
DEFAULT_BACKFILL_LIMIT = 400


def get_live_price(asset: domain.Asset) -> float:
    """Latest price for an asset via its configured provider."""
    provider = get_provider(asset.data_provider)
    return provider.fetch_live_price(asset.data_symbol)


def get_live_price_for_symbol(db: Session, symbol: str) -> Optional[float]:
    cached = latest_close(db, symbol)
    if cached:
        return cached
    asset = db.query(domain.Asset).filter(domain.Asset.symbol == symbol).first()
    if not asset:
        return None
    return get_live_price(asset)


def ingest_asset(db: Session, asset: domain.Asset, timeframe: str = DEFAULT_TIMEFRAME,
                 limit: int = DEFAULT_BACKFILL_LIMIT) -> int:
    """Fetch and upsert OHLCV bars for a single asset. Returns rows fetched."""
    provider = get_provider(asset.data_provider)
    bars = provider.fetch_ohlcv(asset.data_symbol, timeframe=timeframe, limit=limit)
    if not bars:
        logger.warning("No bars returned for %s (%s/%s).", asset.symbol, asset.data_provider, timeframe)
        return 0

    rows = [
        {
            "symbol": asset.symbol,
            "timeframe": timeframe,
            "timestamp": b.timestamp,
            "open": b.open,
            "high": b.high,
            "low": b.low,
            "close": b.close,
            "volume": b.volume,
        }
        for b in bars
    ]
    try:
        stmt = insert(domain.MarketBar).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=["symbol", "timeframe", "timestamp"],
            set_={
                "open": stmt.excluded.open,
                "high": stmt.excluded.high,
                "low": stmt.excluded.low,
                "close": stmt.excluded.close,
                "volume": stmt.excluded.volume,
            },
        )
        db.execute(stmt)
        db.commit()
        logger.info("Ingested %d bars for %s (%s).", len(rows), asset.symbol, timeframe)
        return len(rows)
    except Exception as e:
        logger.error("Failed to ingest bars for %s: %s", asset.symbol, e, exc_info=True)
        db.rollback()
        return 0


def ingest_all(db: Session, timeframe: str = DEFAULT_TIMEFRAME, limit: int = DEFAULT_BACKFILL_LIMIT) -> int:
    """Ingest OHLCV for every active asset. Returns total bars processed."""
    assets = db.query(domain.Asset).filter(domain.Asset.is_active == True).all()
    total = 0
    for asset in assets:
        total += ingest_asset(db, asset, timeframe=timeframe, limit=limit)
    return total


def get_bars_df(db: Session, symbol: str, timeframe: str = DEFAULT_TIMEFRAME,
                limit: int = DEFAULT_BACKFILL_LIMIT) -> pd.DataFrame:
    """Return an oldest-first DataFrame [timestamp, open, high, low, close, volume]."""
    fetch_limit = limit * 3 if timeframe == DEFAULT_TIMEFRAME else limit
    q = (
        db.query(
            domain.MarketBar.timestamp,
            domain.MarketBar.open,
            domain.MarketBar.high,
            domain.MarketBar.low,
            domain.MarketBar.close,
            domain.MarketBar.volume,
        )
        .filter(domain.MarketBar.symbol == symbol, domain.MarketBar.timeframe == timeframe)
        .order_by(domain.MarketBar.timestamp.desc())
        .limit(fetch_limit)
    )
    df = pd.read_sql(q.statement, db.bind)
    if df.empty:
        return df
    df = df.iloc[::-1].reset_index(drop=True)
    for col in ("open", "high", "low", "close", "volume"):
        df[col] = df[col].astype(float)
    if timeframe == DEFAULT_TIMEFRAME:
        df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.normalize()
        df = (
            df.groupby("timestamp", as_index=False)
            .agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"})
            .sort_values("timestamp")
        )
        if len(df) > limit:
            df = df.iloc[-limit:].reset_index(drop=True)
    return df


def get_bars_panel(
    db: Session,
    symbols: list[str],
    timeframe: str = DEFAULT_TIMEFRAME,
    limit: int = DEFAULT_BACKFILL_LIMIT,
    min_bars: int = 60,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Aligned daily close panel (index=timestamps, columns=symbols) + per-symbol coverage metadata."""
    frames: dict[str, pd.Series] = {}
    coverage: dict[str, Any] = {}
    for sym in symbols:
        df = get_bars_df(db, sym, timeframe=timeframe, limit=limit)
        if df.empty or len(df) < min_bars:
            coverage[sym] = {"bars": len(df) if not df.empty else 0, "status": "insufficient"}
            continue
        provider_row = (
            db.query(domain.Asset.data_provider)
            .filter(domain.Asset.symbol == sym)
            .first()
        )
        provider = provider_row[0] if provider_row else "unknown"
        coverage[sym] = {
            "bars": len(df),
            "status": "ok",
            "provider": provider,
            "period_start": df["timestamp"].iloc[0].isoformat(),
            "period_end": df["timestamp"].iloc[-1].isoformat(),
        }
        frames[sym] = df.set_index("timestamp")["close"].astype(float)

    if not frames:
        return pd.DataFrame(), coverage

    panel = pd.DataFrame(frames).sort_index()
    panel = panel.dropna(how="any")
    coverage["_aligned"] = {
        "rows": len(panel),
        "symbols": list(panel.columns),
        "period_start": panel.index[0].isoformat() if len(panel) else None,
        "period_end": panel.index[-1].isoformat() if len(panel) else None,
    }
    return panel, coverage


def latest_close(db: Session, symbol: str, timeframe: str = DEFAULT_TIMEFRAME) -> Optional[float]:
    row = (
        db.query(domain.MarketBar.close)
        .filter(domain.MarketBar.symbol == symbol, domain.MarketBar.timeframe == timeframe)
        .order_by(domain.MarketBar.timestamp.desc())
        .first()
    )
    return float(row[0]) if row else None


# --- Background jobs -------------------------------------------------------

def run_market_ingestion(limit: int = 5):
    """Lightweight recurring ingestion: refresh the most-recent daily bars per asset."""
    db = SessionLocal()
    try:
        ingest_all(db, timeframe=DEFAULT_TIMEFRAME, limit=limit)
    except Exception as e:
        logger.error("Market ingestion job failed: %s", e, exc_info=True)
    finally:
        db.close()


def run_backfill(limit: int = DEFAULT_BACKFILL_LIMIT):
    """One-shot deeper history backfill (daily) across all active assets."""
    db = SessionLocal()
    try:
        total = ingest_all(db, timeframe=DEFAULT_TIMEFRAME, limit=limit)
        logger.info("Backfill complete: %d daily bars across active assets.", total)
    except Exception as e:
        logger.error("Backfill job failed: %s", e, exc_info=True)
    finally:
        db.close()
