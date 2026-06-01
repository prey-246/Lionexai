import pandas as pd
import numpy as np
from typing import Dict, Any

class BacktestEngine:
    def __init__(self, initial_capital: float = 100000.0):
        self.initial_capital = initial_capital
        
    def run_moving_average_crossover(self, df: pd.DataFrame, short_window: int = 20, long_window: int = 50) -> Dict[str, Any]:
        """
        A standard structural strategy to validate the engine physics.
        """
        data = df.copy()
        data['SMA_Short'] = data['close'].rolling(window=short_window).mean()
        data['SMA_Long'] = data['close'].rolling(window=long_window).mean()
        
        # 1 = Buy Signal, -1 = Sell Signal
        data['Signal'] = 0.0
        data['Signal'][short_window:] = np.where(data['SMA_Short'][short_window:] > data['SMA_Long'][short_window:], 1.0, 0.0)
        data['Position'] = data['Signal'].diff()
        
        # Calculate daily returns
        data['Market_Returns'] = data['close'].pct_change()
        data['Strategy_Returns'] = data['Market_Returns'] * data['Signal'].shift(1)
        
        return self._calculate_metrics(data)
        
    def _calculate_metrics(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Generates the institutional reporting metrics required by the MVP."""
        data['Cumulative_Returns'] = (1 + data['Strategy_Returns']).cumprod()
        data['Cumulative_Max'] = data['Cumulative_Returns'].cummax()
        data['Drawdown'] = data['Cumulative_Max'] - data['Cumulative_Returns']
        data['Drawdown_Pct'] = data['Drawdown'] / data['Cumulative_Max']
        
        total_return = data['Cumulative_Returns'].iloc[-1] - 1 if not pd.isna(data['Cumulative_Returns'].iloc[-1]) else 0
        max_drawdown = data['Drawdown_Pct'].max()
        
        # Win rate approximation (days with positive returns vs total active days)
        winning_days = len(data[data['Strategy_Returns'] > 0])
        losing_days = len(data[data['Strategy_Returns'] < 0])
        total_trades = winning_days + losing_days
        win_rate = winning_days / total_trades if total_trades > 0 else 0
        
        # Sharpe Ratio (Assuming Risk Free Rate = 0 for Crypto)
        daily_volatility = data['Strategy_Returns'].std()
        sharpe_ratio = (data['Strategy_Returns'].mean() / daily_volatility) * np.sqrt(365) if daily_volatility > 0 else 0

        return {
            "final_capital": self.initial_capital * (1 + total_return),
            "total_return_pct": round(total_return * 100, 2),
            "max_drawdown_pct": round(max_drawdown * 100, 2),
            "win_rate_pct": round(win_rate * 100, 2),
            "sharpe_ratio": round(sharpe_ratio, 2),
            "total_trades_simulated": total_trades
        }