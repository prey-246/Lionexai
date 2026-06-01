from .base import BaseStrategy
from .ma_crossover import MACrossoverStrategy
from .rsi_mean_reversion import RsiMeanReversionStrategy


STRATEGY_MAP = {
    "MA_CROSSOVER": MACrossoverStrategy,
    "RSI_MEAN_REVERSION": RsiMeanReversionStrategy,
}

def get_strategy(strategy_name: str):
    strategy_class = STRATEGY_MAP.get(strategy_name)
    return strategy_class