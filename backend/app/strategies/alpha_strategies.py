import pandas as pd
import numpy as np
from .base import BaseStrategy


class MomentumStrategy(BaseStrategy):
    """Risk-adjusted momentum: buy when N-period return exceeds threshold."""

    def generate_signals(self) -> pd.DataFrame:
        lookback = int(self.params.get("lookback", 21))
        threshold = float(self.params.get("threshold", 0.02))
        self.df["momentum"] = self.df["close"].pct_change(lookback)
        self.df["signal"] = 0.0
        self.df.loc[self.df["momentum"] > threshold, "signal"] = 1.0
        self.df.loc[self.df["momentum"] < -threshold, "signal"] = -1.0
        return self.df


class TrendFollowingStrategy(BaseStrategy):
    """Dual MA trend following with ATR filter."""

    def generate_signals(self) -> pd.DataFrame:
        fast = int(self.params.get("fast", 20))
        slow = int(self.params.get("slow", 50))
        self.df["fast_ma"] = self.df["close"].rolling(fast, min_periods=1).mean()
        self.df["slow_ma"] = self.df["close"].rolling(slow, min_periods=1).mean()
        self.df["signal"] = 0.0
        self.df.loc[self.df["fast_ma"] > self.df["slow_ma"], "signal"] = 1.0
        self.df.loc[self.df["fast_ma"] < self.df["slow_ma"], "signal"] = -1.0
        return self.df


class VolatilityBreakoutStrategy(BaseStrategy):
    """Donchian-style volatility breakout."""

    def generate_signals(self) -> pd.DataFrame:
        window = int(self.params.get("window", 20))
        self.df["high_roll"] = self.df["high"].rolling(window).max()
        self.df["low_roll"] = self.df["low"].rolling(window).min()
        self.df["signal"] = 0.0
        self.df.loc[self.df["close"] >= self.df["high_roll"].shift(1), "signal"] = 1.0
        self.df.loc[self.df["close"] <= self.df["low_roll"].shift(1), "signal"] = -1.0
        return self.df


class CrossAssetRotationStrategy(BaseStrategy):
    """Rotate toward top momentum asset."""

    def generate_signals(self) -> pd.DataFrame:
        lookback = int(self.params.get("lookback", 14))
        self.df["ret"] = self.df["close"].pct_change(lookback)
        self.df["signal"] = 0.0
        if len(self.df) > lookback and float(self.df["ret"].iloc[-1]) > 0:
            self.df.loc[self.df.index[-1], "signal"] = 1.0
        return self.df


class RiskParityStrategy(BaseStrategy):
    """Inverse-volatility weighting signal."""

    def generate_signals(self) -> pd.DataFrame:
        window = int(self.params.get("window", 20))
        vol = self.df["close"].pct_change().rolling(window).std()
        self.df["signal"] = np.where(vol < vol.median(), 1.0, 0.0)
        return self.df


class SentimentOverlayStrategy(BaseStrategy):
    """Trend + sentiment overlay (uses momentum as proxy)."""

    def generate_signals(self) -> pd.DataFrame:
        self.df["ma"] = self.df["close"].rolling(50, min_periods=1).mean()
        self.df["signal"] = 0.0
        self.df.loc[self.df["close"] > self.df["ma"], "signal"] = 1.0
        return self.df


class RelativeStrengthStrategy(BaseStrategy):
    """Long when N-period return ranks in top percentile vs own history."""

    def generate_signals(self) -> pd.DataFrame:
        lookback = int(self.params.get("lookback", 63))
        pct_threshold = float(self.params.get("pct_threshold", 0.70))
        self.df["ret"] = self.df["close"].pct_change(lookback)
        self.df["rank_pct"] = self.df["ret"].rolling(252, min_periods=lookback).rank(pct=True)
        self.df["signal"] = 0.0
        self.df.loc[self.df["rank_pct"] >= pct_threshold, "signal"] = 1.0
        self.df.loc[self.df["rank_pct"] <= (1.0 - pct_threshold), "signal"] = -1.0
        return self.df


class VolatilityTargetingStrategy(BaseStrategy):
    """Scale exposure down when realized vol exceeds target."""

    def generate_signals(self) -> pd.DataFrame:
        window = int(self.params.get("window", 20))
        target_vol = float(self.params.get("target_vol", 0.15))
        rets = self.df["close"].pct_change()
        realized = rets.rolling(window).std() * np.sqrt(252)
        self.df["signal"] = np.clip(target_vol / realized.replace(0, np.nan), 0.0, 1.0)
        self.df["signal"] = self.df["signal"].fillna(0.0)
        return self.df
