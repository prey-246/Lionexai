import sys
import os
import logging
import pandas as pd

# Ensure backend modules can be imported
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.models import domain
from app.strategies import get_strategy

try:
    from app.engines.risk_engine import RiskEngine
except ImportError:
    RiskEngine = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_autonomous_execution():
    """
    Sprint 9: Autonomous Trading Engine
    Scans the Strategy Registry for active, assigned strategies.
    Fetches market data, runs the algo, and executes paper trades.
    """
    db = SessionLocal()
    try:
        # Find all active strategies that have been assigned to a portfolio
        strategies = db.query(domain.Strategy).filter(domain.Strategy.is_active == True).all()
        
        for strategy in strategies:
            portfolio_id = strategy.parameters.get('assigned_portfolio_id')
            if not portfolio_id:
                continue
                
            portfolio = db.query(domain.Portfolio).filter(domain.Portfolio.id == portfolio_id).first()
            if not portfolio:
                continue

            # For MVP, we simulate BTC/USDT.
            symbol = "BTC/USDT" 
            
            # Fetch recent market data for algorithm calculation
            query = db.query(
                domain.MarketDataOHLCV.timestamp,
                domain.MarketDataOHLCV.close,
            ).filter(domain.MarketDataOHLCV.symbol == symbol).order_by(domain.MarketDataOHLCV.timestamp.desc()).limit(100)
            
            df = pd.read_sql(query.statement, db.bind)
            if len(df) < 20:
                continue
            df = df.iloc[::-1].reset_index(drop=True) # Reverse back to chronological order

            # Run the quantitative algorithm
            strategy_type = strategy.parameters.get('strategy_type')
            if not strategy_type:
                continue
                
            strat_class = get_strategy(strategy_type)
            if not strat_class:
                continue
                
            strat_instance = strat_class(df, strategy.parameters)
            result_df = strat_instance.generate_signals()
            
            # Determine the current algorithmic signal (1 = BUY, -1 = SELL)
            latest_signal = result_df.iloc[-1]['signal']
            current_price = float(result_df.iloc[-1]['close'])
            
            # Determine current portfolio holding for this asset
            open_positions = db.query(domain.Trade).filter(
                domain.Trade.portfolio_id == portfolio.pk_id, domain.Trade.symbol == symbol, domain.Trade.status == 'OPEN'
            ).all()
            current_size = sum([t.size if t.side == 'BUY' else -t.size for t in open_positions])
            
            # State Machine: Compare algorithmic signal against current holdings
            trade_side = None
            if latest_signal == 1 and current_size <= 0:
                trade_side = 'BUY'
            elif latest_signal == -1 and current_size > 0:
                trade_side = 'SELL'
                
            if trade_side:
                trade_size = (portfolio.total_equity * 0.10) / current_price if trade_side == 'BUY' else current_size
                
                # --- ROUTE THROUGH NEXA RISK ENGINE ---
                if RiskEngine:
                    try:
                        risk_engine = RiskEngine(db)
                        # Evaluate trade (Handling both exception-based and tuple-based engine architectures)
                        result = risk_engine.evaluate_trade(portfolio, symbol, trade_side, trade_size, current_price)
                        if isinstance(result, tuple) and len(result) == 2 and not result[0]:
                            logger.warning(f"[RISK REJECTION] Autonomous trade blocked for {portfolio.id}: {result[1]}")
                            continue
                    except Exception as e:
                        logger.warning(f"[RISK REJECTION] Autonomous trade blocked for {portfolio.id}: {str(e)}")
                        continue
                # --------------------------------------
                
                logger.info(f"[AUTONOMOUS ENGINE] {strategy.name} generated {trade_side} {trade_size:.4f} {symbol} for {portfolio.id} at ${current_price:,.2f}")
                
                new_trade = domain.Trade(portfolio_id=portfolio.pk_id, symbol=symbol, side=trade_side, size=trade_size, entry_price=current_price, status='OPEN' if trade_side == 'BUY' else 'CLOSED', pnl=0.0)
                
                if trade_side == 'SELL' and open_positions:
                    buy_trade = open_positions[0]
                    pnl = (current_price - buy_trade.entry_price) * buy_trade.size
                    buy_trade.status, new_trade.pnl = 'CLOSED', pnl
                    portfolio.total_equity += pnl

                db.add(new_trade)
                db.add(domain.AuditLog(action_type="AUTONOMOUS_TRADE_EXECUTED", description=f"Strategy '{strategy.name}' autonomously executed {trade_side}.", metadata_json={"portfolio": portfolio.id}))
                db.commit()
    except Exception as e:
        logger.error(f"Failed to execute autonomous strategies: {e}")
        db.rollback()
    finally:
        db.close()