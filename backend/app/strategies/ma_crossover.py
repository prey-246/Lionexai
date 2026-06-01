import pandas as pd
import numpy as np
from .base import BaseStrategy

class MACrossoverStrategy(BaseStrategy):
    """Moving Average Crossover Strategy."""

    def generate_signals(self) -> pd.DataFrame:
        short_window = int(self.params.get('short_window', 20))
        long_window = int(self.params.get('long_window', 50))

        self.df['short_ma'] = self.df['close'].rolling(window=short_window, min_periods=1).mean()
        self.df['long_ma'] = self.df['close'].rolling(window=long_window, min_periods=1).mean()
        
        self.df['signal'] = 0.0
        self.df.loc[long_window:, 'signal'] = np.where(self.df.loc[long_window:, 'short_ma'] > self.df.loc[long_window:, 'long_ma'], 1.0, 0.0)
        
        return self.df