from fastapi import APIRouter, Depends, HTTPException
import random
import time
import pandas as pd
import numpy as np
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone

from app.models import schemas
from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import domain
from app.strategies import get_strategy

router = APIRouter()

@router.post("/run", response_model=schemas.BacktestResponse)
def run_backtest(
    backtest_in: schemas.BacktestRequest,
    db: Session = Depends(get_db),
    current_user: domain.User = Depends(get_current_user)
):
    """
    Runs a backtest using historical daily data from the database.
    """
    # 1. Fetch historical data from the database
    # NOTE: This assumes `schemas.BacktestRequest` is updated with optional `start_date` and `end_date`.
    # Using getattr for safety in case the schema is not yet updated.
    end_date = getattr(backtest_in, 'end_date', None) or datetime.now(timezone.utc)
    start_date = getattr(backtest_in, 'start_date', None) or end_date - timedelta(days=365)

    # The backfilled data is daily, so we enforce the '1d' timeframe for now.
    if backtest_in.timeframe != '1d':
        raise HTTPException(
            status_code=400,
            detail=f"Only '1d' timeframe is supported for database backtests at the moment. Please backfill data for other timeframes if needed."
        )

    try:
        query = db.query(
            domain.MarketDataOHLCV.timestamp,
            domain.MarketDataOHLCV.open,
            domain.MarketDataOHLCV.high,
            domain.MarketDataOHLCV.low,
            domain.MarketDataOHLCV.close,
            domain.MarketDataOHLCV.volume
        ).filter(
            domain.MarketDataOHLCV.symbol == backtest_in.symbol,
            domain.MarketDataOHLCV.timestamp >= start_date,
            domain.MarketDataOHLCV.timestamp <= end_date
        ).order_by(domain.MarketDataOHLCV.timestamp.asc())
        
        df = pd.read_sql(query.statement, db.bind)

        if len(df) < 50:
            raise ValueError(f"Not enough historical data in the database for {backtest_in.symbol} between {start_date.date()} and {end_date.date()}. Please backfill more data.")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch market data from database: {e}")

    df['timestamp'] = pd.to_datetime(df['timestamp'])

    # 2. Select and run the strategy
    strategy_class = get_strategy(backtest_in.strategy)
    if not strategy_class:
        raise HTTPException(status_code=400, detail=f"Strategy '{backtest_in.strategy}' not implemented.")

    strategy = strategy_class(df, backtest_in.strategy_params or {})
    df = strategy.generate_signals()

    df['position'] = df['signal'].diff().fillna(0)

    # 3. Simulate trades and calculate performance
    initial_capital = backtest_in.initial_capital
    positions = pd.DataFrame(index=df.index).fillna(0.0)
    portfolio = pd.DataFrame(index=df.index).fillna(0.0)
    portfolio['timestamp'] = df['timestamp']

    # Cost parameters
    global_settings = db.query(domain.GlobalSettings).filter_by(id="default").first()
    default_comm = global_settings.default_commission_pct if global_settings else 0.1
    default_slip = global_settings.default_slippage_pct if global_settings else 0.1

    commission_pct = backtest_in.commission_pct if backtest_in.commission_pct is not None else default_comm
    slippage_pct = backtest_in.slippage_pct if backtest_in.slippage_pct is not None else default_slip

    # Vectorized backtest approach with realistic trading costs
    positions[backtest_in.symbol] = df['signal'] # Hold 1 unit of the asset when signal is 1
    portfolio['holdings'] = positions[backtest_in.symbol] * df['close']
    
    trade_notional_value = abs(df['position']) * df['close']
    fees = trade_notional_value * (commission_pct / 100)
    slippage = trade_notional_value * (slippage_pct / 100)
    total_costs = fees + slippage
    
    portfolio['cash'] = initial_capital - (df['position'] * df['close']).cumsum() - total_costs.cumsum()
    portfolio['total'] = portfolio['cash'] + portfolio['holdings']
    portfolio['returns'] = portfolio['total'].pct_change()

    # 5. Prepare Equity Curve data for charting
    equity_curve_data = []
    for _, row in portfolio.iterrows():
        equity_curve_data.append(schemas.EquityDataPoint(time=int(row['timestamp'].timestamp()), value=row['total']))

    # 4. Calculate final metrics
    final_net_capital = portfolio['total'].iloc[-1]
    final_gross_capital = (initial_capital - (df['position'] * df['close']).cumsum() + portfolio['holdings']).iloc[-1]
    
    gross_return_pct = (final_gross_capital - initial_capital) / initial_capital * 100
    net_return_pct = (final_net_capital - initial_capital) / initial_capital * 100
    total_fees_paid = fees.sum()
    slippage_impact = slippage.sum()
    
    # Calculate Drawdown
    rolling_max = portfolio['total'].cummax()
    daily_drawdown = portfolio['total']/rolling_max - 1.0
    max_drawdown_pct = daily_drawdown.min() * 100

    # Calculate Sharpe Ratio with correct annualization
    timeframe_map = {'1h': 24, '4h': 6, '1d': 1}
    periods_per_day = timeframe_map.get(backtest_in.timeframe, 1)
    annualization_factor = 365 * periods_per_day
    sharpe_ratio = portfolio['returns'].mean() / portfolio['returns'].std() * np.sqrt(annualization_factor) if portfolio['returns'].std() > 0 else 0.0

    # Calculate Win Rate and Total Trades more accurately (round-trip)
    trades = df[df['position'] != 0]
    trade_pnls = []
    
    # A round trip trade is a buy followed by a sell
    buy_signals = trades[trades['position'] == 1]
    sell_signals = trades[trades['position'] == -1]

    # Simple loop to match buys and sells
    for i in range(min(len(buy_signals), len(sell_signals))):
        buy_price = buy_signals['close'].iloc[i]
        sell_price = sell_signals['close'].iloc[i]
        trade_pnls.append(sell_price - buy_price)
    
    win_rate_pct = (len([p for p in trade_pnls if p > 0]) / len(trade_pnls) * 100) if len(trade_pnls) > 0 else 0.0
    total_trades_simulated = len(trade_pnls)
    
    metrics = schemas.BacktestMetrics(
        final_capital=round(final_net_capital, 2),
        total_return_pct=round(net_return_pct, 2), # Kept for backward compatibility
        gross_return_pct=round(gross_return_pct, 2),
        net_return_pct=round(net_return_pct, 2),
        total_fees_paid=round(total_fees_paid, 2),
        slippage_impact=round(slippage_impact, 2),
        max_drawdown_pct=round(abs(max_drawdown_pct), 2),
        win_rate_pct=round(win_rate_pct, 2),
        sharpe_ratio=round(sharpe_ratio, 2),
        total_trades_simulated=total_trades_simulated
    )

    return schemas.BacktestResponse(
        status="success",
        symbol=backtest_in.symbol,
        metrics=metrics,
        equity_curve=equity_curve_data
    )