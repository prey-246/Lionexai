import ccxt.async_support as ccxt
import ccxt as ccxt_sync
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
from datetime import datetime, timezone
import logging

from app.models import domain

logger = logging.getLogger(__name__)

class HistoricalDataService:
    def __init__(self):
        self.exchange = ccxt.binance({'enableRateLimit': True})

    async def close_exchange(self):
        await self.exchange.close()

    async def fetch_and_store_ohlcv(self, db: Session, symbol: str, timeframe: str = '1d', since: int | None = None, limit: int = 1000):
        """
        Fetches OHLCV data from the exchange and stores it in the database.
        Uses ON CONFLICT DO NOTHING to prevent duplicate entries.
        """
        logger.info(f"Fetching {limit} bars of {symbol} {timeframe} data...")
        try:
            ohlcv = await self.exchange.fetch_ohlcv(symbol, timeframe, since, limit)
            if not ohlcv:
                logger.warning(f"No data returned for {symbol}")
                return 0

            data_to_insert = [
                {
                    'timestamp': datetime.fromtimestamp(row[0] / 1000, tz=timezone.utc),
                    'symbol': symbol,
                    'open': row[1],
                    'high': row[2],
                    'low': row[3],
                    'close': row[4],
                    'volume': row[5],
                } for row in ohlcv
            ]
            
            if data_to_insert:
                stmt = insert(domain.MarketDataOHLCV).values(data_to_insert)
                stmt = stmt.on_conflict_do_nothing(index_elements=['timestamp', 'symbol'])
                db.execute(stmt)
                db.commit()
                logger.info(f"Successfully inserted/updated {len(data_to_insert)} records for {symbol}.")
                return len(data_to_insert)
            
            return 0
        except Exception as e:
            logger.error(f"An error occurred while fetching data for {symbol}: {e}", exc_info=True)
            db.rollback()
            return 0

    def fetch_and_store_ohlcv_sync(self, db: Session, symbol: str, timeframe: str = '1d', since: int | None = None, limit: int = 1000):
        """
        Synchronous version of fetch_and_store_ohlcv for background tasks.
        """
        sync_exchange = ccxt_sync.binance({'enableRateLimit': True})
        logger.info(f"SYNC: Fetching {limit} bars of {symbol} {timeframe} data...")
        try:
            ohlcv = sync_exchange.fetch_ohlcv(symbol, timeframe, since, limit)
            if not ohlcv:
                logger.warning(f"SYNC: No data returned for {symbol}")
                return 0

            data_to_insert = [
                {
                    'timestamp': datetime.fromtimestamp(row[0] / 1000, tz=timezone.utc),
                    'symbol': symbol,
                    'open': row[1],
                    'high': row[2],
                    'low': row[3],
                    'close': row[4],
                    'volume': row[5],
                } for row in ohlcv
            ]
            
            if data_to_insert:
                stmt = insert(domain.MarketDataOHLCV).values(data_to_insert)
                stmt = stmt.on_conflict_do_nothing(index_elements=['timestamp', 'symbol'])
                db.execute(stmt)
                db.commit()
                logger.info(f"SYNC: Successfully inserted/updated {len(data_to_insert)} records for {symbol}.")
                return len(data_to_insert)
            
            return 0
        except Exception as e:
            logger.error(f"An error occurred while fetching data for {symbol}: {e}", exc_info=True)
            db.rollback()
            return 0
        finally:
            # The synchronous ccxt exchange object does not need to be closed.
            pass