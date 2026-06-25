"""Phase 5 — Real strategy validation (historical / walk-forward / Monte Carlo).

Separate from demo operational metrics in validation_service.py.
"""

from .real_strategy_validation import RealStrategyValidator, ValidationRunResult

__all__ = ["RealStrategyValidator", "ValidationRunResult"]
