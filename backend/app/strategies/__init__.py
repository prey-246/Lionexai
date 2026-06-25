from .base import BaseStrategy
from .ma_crossover import MACrossoverStrategy
from .rsi_mean_reversion import RsiMeanReversionStrategy
from .alpha_strategies import (
    MomentumStrategy, TrendFollowingStrategy, VolatilityBreakoutStrategy,
    CrossAssetRotationStrategy, RiskParityStrategy, SentimentOverlayStrategy,
    RelativeStrengthStrategy, VolatilityTargetingStrategy,
)


STRATEGY_MAP = {
    "MA_CROSSOVER": MACrossoverStrategy,
    "MEAN_REVERSION": RsiMeanReversionStrategy,
    "MOMENTUM": MomentumStrategy,
    "TREND_FOLLOWING": TrendFollowingStrategy,
    "VOL_BREAKOUT": VolatilityBreakoutStrategy,
    "CROSS_ASSET_ROTATION": CrossAssetRotationStrategy,
    "RISK_PARITY": RiskParityStrategy,
    "SENTIMENT_OVERLAY": SentimentOverlayStrategy,
    "RELATIVE_STRENGTH": RelativeStrengthStrategy,
    "VOLATILITY_TARGETING": VolatilityTargetingStrategy,
    "DYNAMIC_POSITION_SIZING": VolatilityTargetingStrategy,
    "ADAPTIVE_REGIME_SWITCHING": CrossAssetRotationStrategy,
}

def get_strategy(strategy_name: str):
    strategy_class = STRATEGY_MAP.get(strategy_name.upper())
    return strategy_class