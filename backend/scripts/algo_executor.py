import sys
import os
import logging
import asyncio
import time
import uuid
from typing import Dict
from datetime import datetime

import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.models import domain
from app.services.audit_service import create_audit_log, log_exchange_reconnect, log_exchange_disconnect
from app.strategies import get_strategy
from app.exchange import get_exchange_adapter, ExchangeAdapter

try:
    from app.engines.risk_engine import RiskEngine, RiskRejectionError
except ImportError:
    RiskEngine = None
    RiskRejectionError = Exception

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

AUDIT_ACTIONS = {
    "binance": "AUTONOMOUS_TRADE_EXECUTED_BINANCE",
    "bybit": "AUTONOMOUS_TRADE_EXECUTED_BYBIT",
}


def _audit_action_for_exchange(exchange: str) -> str:
    return AUDIT_ACTIONS.get(exchange.lower(), f"AUTONOMOUS_TRADE_EXECUTED_{exchange.upper()}")


async def run_autonomous_execution():
    """
    Autonomous Trading Engine: Signal → Risk Engine → Exchange Adapter → Testnet Order → Audit → Portfolio.
    """
    db = SessionLocal()
    adapters: Dict[str, ExchangeAdapter] = {}

    try:
        strategies = db.query(domain.Strategy).filter(domain.Strategy.is_active == True).all()

        for strategy in strategies:
            portfolio_id = strategy.parameters.get("assigned_portfolio_id")
            if not portfolio_id:
                continue

            portfolio = db.query(domain.Portfolio).filter(domain.Portfolio.id == portfolio_id).first()
            if not portfolio:
                continue

            mandate = db.query(domain.Mandate).filter(domain.Mandate.pk_id == portfolio.mandate_pk_id).first()
            if not mandate:
                continue

            execution_exchange = strategy.parameters.get("execution_exchange", "binance").lower()
            exchange_adapter = adapters.get(execution_exchange)

            if not exchange_adapter:
                api_key = os.environ.get(f"{execution_exchange.upper()}_API_KEY")
                secret_key = os.environ.get(f"{execution_exchange.upper()}_SECRET_KEY")

                if not api_key or "YOUR_" in api_key:
                    logger.warning(
                        f"API keys for {execution_exchange.upper()} not configured. "
                        f"Skipping strategy {strategy.name}."
                    )
                    continue

                try:
                    exchange_adapter = get_exchange_adapter(execution_exchange, api_key, secret_key)
                    await exchange_adapter.connect()
                    adapters[execution_exchange] = exchange_adapter
                    log_exchange_reconnect(db, execution_exchange)
                    db.commit()
                    logger.info(f"Adapter for {execution_exchange.upper()} initialized for this run.")
                except Exception as e:
                    logger.error(f"Could not connect adapter for {execution_exchange}: {e}")
                    log_exchange_disconnect(db, execution_exchange, str(e))
                    db.commit()
                    continue

            symbol = "BTC/USDT"

            query = db.query(
                domain.MarketDataOHLCV.timestamp,
                domain.MarketDataOHLCV.close,
            ).filter(domain.MarketDataOHLCV.symbol == symbol).order_by(
                domain.MarketDataOHLCV.timestamp.desc()
            ).limit(100)

            df = pd.read_sql(query.statement, db.bind)
            if len(df) < 20:
                continue
            df = df.iloc[::-1].reset_index(drop=True)

            strategy_type = strategy.parameters.get("strategy_type")
            if not strategy_type:
                continue

            strat_class = get_strategy(strategy_type)
            if not strat_class:
                continue

            strat_instance = strat_class(df, strategy.parameters)
            result_df = strat_instance.generate_signals()
            latest_signal = result_df.iloc[-1]["signal"]
            current_price = float(result_df.iloc[-1]["close"])

            open_positions = db.query(domain.Trade).filter(
                domain.Trade.portfolio_id == portfolio.pk_id,
                domain.Trade.symbol == symbol,
                domain.Trade.status == "OPEN",
            ).all()
            current_size = sum(t.quantity if t.side == "BUY" else -t.quantity for t in open_positions)

            trade_side = None
            if latest_signal == 1 and current_size <= 0:
                trade_side = "BUY"
            elif latest_signal == -1 and current_size > 0:
                trade_side = "SELL"

            if not trade_side:
                continue

            trade_size = (
                (portfolio.total_equity * 0.10) / current_price
                if trade_side == "BUY"
                else current_size
            )

            order_details = {
                "symbol": symbol,
                "size": trade_size,
                "current_price": current_price,
                "side": trade_side,
                "stop_loss": current_price * 0.95 if trade_side == "BUY" else current_price * 1.05,
            }

            if RiskEngine:
                try:
                    risk_engine = RiskEngine(db)
                    risk_engine.evaluate_pre_trade(portfolio, mandate, order_details)
                except RiskRejectionError as e:
                    logger.warning(f"[RISK REJECTION] Autonomous trade blocked for {portfolio.id}: {e}")
                    db.add(domain.Trade(
                        id=f"trd_{uuid.uuid4().hex[:12]}",
                        portfolio_id=portfolio.pk_id,
                        symbol=symbol,
                        side=trade_side,
                        quantity=trade_size,
                        entry_price=current_price,
                        status="REJECTED",
                        pnl=0.0,
                        exchange=execution_exchange,
                        strategy_name=strategy.name,
                        rejection_reason=str(e),
                        trade_source="AUTONOMOUS",
                        created_at=datetime.utcnow(),
                        closed_at=datetime.utcnow(),
                    ))
                    db.add(domain.AuditLog(
                        action_type="ORDER_REJECTED",
                        description=str(e),
                        metadata_json={
                            "portfolio": portfolio.id,
                            "exchange": execution_exchange,
                            "symbol": symbol,
                            "side": trade_side,
                            "quantity": trade_size,
                            "reason": "RISK_ENGINE",
                            "strategy": strategy.name,
                        },
                    ))
                    db.commit()
                    continue
                except Exception as e:
                    logger.warning(f"[RISK REJECTION] Autonomous trade blocked for {portfolio.id}: {e}")
                    continue

            try:
                placement_start = time.time()
                exchange_order = await exchange_adapter.place_market_order(
                    symbol=symbol,
                    side=trade_side.lower(),  # type: ignore[arg-type]
                    amount=trade_size,
                )
                latency_ms = round((time.time() - placement_start) * 1000, 2)

                fill_status = exchange_order.status or "unknown"
                filled_qty = exchange_order.filled or exchange_order.amount
                fill_price = exchange_order.price or current_price

                logger.info(
                    f"[AUTONOMOUS ENGINE] {execution_exchange.upper()} order {exchange_order.id}: "
                    f"{exchange_order.symbol} {filled_qty} @ {fill_price} ({fill_status})"
                )

                audit_metadata = {
                    "portfolio": portfolio.id,
                    "exchange": execution_exchange,
                    "exchange_order_id": exchange_order.id,
                    "symbol": symbol,
                    "side": trade_side,
                    "quantity": filled_qty,
                    "price": fill_price,
                    "fill_status": fill_status,
                    "latency_ms": latency_ms,
                    "strategy": strategy.name,
                    "timestamp": datetime.utcnow().isoformat(),
                }

                db.add(domain.AuditLog(
                    action_type=_audit_action_for_exchange(execution_exchange),
                    description=(
                        f"Strategy '{strategy.name}' executed {trade_side} on "
                        f"{execution_exchange.upper()} testnet."
                    ),
                    metadata_json=audit_metadata,
                ))

                if fill_status in ("closed", "filled"):
                    db.add(domain.AuditLog(
                        action_type="ORDER_FILLED",
                        description=f"Order {exchange_order.id} filled on {execution_exchange.upper()}.",
                        metadata_json=audit_metadata,
                    ))

                new_trade = domain.Trade(
                    id=f"trd_{uuid.uuid4().hex[:12]}",
                    portfolio_id=portfolio.pk_id,
                    symbol=exchange_order.symbol,
                    side=exchange_order.side.upper(),
                    quantity=filled_qty,
                    entry_price=fill_price,
                    status="OPEN" if exchange_order.side.upper() == "BUY" else "CLOSED",
                    pnl=0.0,
                    exchange=execution_exchange,
                    execution_latency_ms=latency_ms,
                    strategy_name=strategy.name,
                    trade_source="AUTONOMOUS",
                )

                if new_trade.side == "SELL" and open_positions:
                    buy_trade = open_positions[0]
                    pnl = (fill_price - buy_trade.entry_price) * buy_trade.quantity
                    buy_trade.status = "CLOSED"
                    buy_trade.closed_at = datetime.utcnow()
                    buy_trade.exit_price = fill_price
                    buy_trade.pnl = pnl
                    new_trade.pnl = pnl
                    new_trade.closed_at = datetime.utcnow()
                    portfolio.total_equity += pnl

                db.add(new_trade)
                db.commit()

            except Exception as e:
                logger.error(
                    f"[AUTONOMOUS ENGINE] Failed to place order on {execution_exchange.upper()} "
                    f"for {portfolio.id}: {e}"
                )
                db.add(domain.AuditLog(
                    action_type="ORDER_REJECTED",
                    description=f"Exchange order failed: {e}",
                    metadata_json={
                        "portfolio": portfolio.id,
                        "exchange": execution_exchange,
                        "symbol": symbol,
                        "side": trade_side,
                        "quantity": trade_size,
                        "reason": "EXCHANGE_ERROR",
                        "strategy": strategy.name,
                        "error": str(e),
                    },
                ))
                db.add(domain.Trade(
                    id=f"trd_{uuid.uuid4().hex[:12]}",
                    portfolio_id=portfolio.pk_id,
                    symbol=symbol,
                    side=trade_side,
                    quantity=trade_size,
                    entry_price=current_price,
                    status="REJECTED",
                    pnl=0.0,
                    exchange=execution_exchange,
                    strategy_name=strategy.name,
                    rejection_reason=f"EXCHANGE_ERROR: {e}",
                    trade_source="AUTONOMOUS",
                    created_at=datetime.utcnow(),
                    closed_at=datetime.utcnow(),
                ))
                db.commit()

    except Exception as e:
        logger.error(f"Failed to execute autonomous strategies: {e}")
        db.rollback()
    finally:
        for exchange_id, adapter in adapters.items():
            logger.info(f"Closing adapter for {exchange_id.upper()}.")
            await adapter.close()
        db.close()


if __name__ == "__main__":
    asyncio.run(run_autonomous_execution())
