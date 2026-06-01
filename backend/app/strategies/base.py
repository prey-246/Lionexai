from abc import ABC, abstractmethod
import pandas as pd
from typing import Dict, Any

class BaseStrategy(ABC):
    """Abstract base class for all trading strategies."""

    def __init__(self, df: pd.DataFrame, params: Dict[str, Any]):
        self.df = df
        self.params = params

    @abstractmethod
    def generate_signals(self) -> pd.DataFrame:
        """Generates trading signals and returns the DataFrame."""
        pass