import pandas as pd
import numpy as np
from .base import BaseStrategy

class RsiMeanReversionStrategy(BaseStrategy):
    """RSI Mean Reversion Strategy."""

    def generate_signals(self) -> pd.DataFrame:
        rsi_period = int(self.params.get('rsi_period', 14))
        oversold_level = int(self.params.get('oversold_level', 30))
        overbought_level = int(self.params.get('overbought_level', 70))

        delta = self.df['close'].diff(1)
        gain = delta.where(delta > 0, 0).rolling(window=rsi_period, min_periods=1).mean()
        loss = -delta.where(delta < 0, 0).rolling(window=rsi_period, min_periods=1).mean()
        
        rs = gain / loss
        self.df['rsi'] = 100 - (100 / (1 + rs))
        self.df['rsi'] = self.df['rsi'].fillna(50)

        in_position = False
        self.df['signal'] = 0.0
        for i, row in self.df.iterrows():
            if row['rsi'] < oversold_level and not in_position:
                in_position = True
            elif row['rsi'] > overbought_level and in_position:
                in_position = False
            if in_position:
                self.df.loc[i, 'signal'] = 1.0
        
        return self.df