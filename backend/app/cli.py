import typer
import asyncio
from datetime import datetime, timedelta

from app.services.historical_data import HistoricalDataService
from app.core.database import SessionLocal

app = typer.Typer(add_completion=False, help="NEXA Platform command-line utilities.")

async def _backfill(symbol: str, days: int):
    db = SessionLocal()
    service = HistoricalDataService()
    
    since = service.exchange.parse8601((datetime.now() - timedelta(days=days)).isoformat())
    
    print(f"Starting backfill for {symbol} for the last {days} days...")
    
    await service.fetch_and_store_ohlcv(db, symbol, '1d', since=since, limit=days + 5)
    
    await service.close_exchange()
    db.close()
    print("Backfill complete.")

@app.command()
def backfill_market_data(
    symbol: str = typer.Option("BTC/USDT", help="The trading symbol to backfill."),
    days: int = typer.Option(365, help="Number of past days to fetch data for.")
):
    """Backfills historical OHLCV daily data for a given symbol."""
    asyncio.run(_backfill(symbol, days))

if __name__ == "__main__":
    app()