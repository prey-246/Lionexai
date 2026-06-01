from fastapi import APIRouter, Depends, HTTPException
import random
import time
import ccxt
import pandas as pd
import numpy as np

from app.models import schemas
from app.api.deps import get_current_user
from app.models import domain
from app.strategies import get_strategy

router = APIRouter()

@router.post("/run", response_model=schemas.BacktestResponse)
def run_backtest(
    backtest_in: schemas.BacktestRequest,
    current_user: domain.User = Depends(get_current_user)
):
    """
    Runs a simplified, simulated backtest.
    In a real system, this would fetch historical data and run a complex simulation.
    """
    # 1. Fetch historical data using ccxt, using the requested timeframe
    exchange = ccxt.binance()
    # Fetch 500 candles to have enough data for the selected timeframe
    try:
        ohlcv = exchange.fetch_ohlcv(backtest_in.symbol, backtest_in.timeframe, limit=500)
        if len(ohlcv) < 50: # Not enough data to be meaningful
            raise ValueError("Not enough historical data for this symbol/timeframe combination.")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch market data: {e}")

    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

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

    # Correctly simulate portfolio value - This is a vectorized backtest approach
    positions[backtest_in.symbol] = df['signal'] # Hold 1 unit of the asset when signal is 1
    portfolio['holdings'] = positions[backtest_in.symbol] * df['close']
    portfolio['cash'] = initial_capital - (df['position'] * df['close']).cumsum()
    portfolio['total'] = portfolio['cash'] + portfolio['holdings'] # Corrected from 'positions' to 'holdings'
    portfolio['returns'] = portfolio['total'].pct_change()

    # 5. Prepare Equity Curve data for charting
    equity_curve_data = []
    for _, row in portfolio.iterrows():
        equity_curve_data.append(schemas.EquityDataPoint(time=int(row['timestamp'].timestamp()), value=row['total']))

    # 4. Calculate final metrics
    final_capital = portfolio['total'].iloc[-1]
    total_return_pct = (final_capital - initial_capital) / initial_capital * 100
    
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
        final_capital=round(final_capital, 2),
        total_return_pct=round(total_return_pct, 2),
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