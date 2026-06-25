"""Audit action categories and infrastructure event consolidation."""

from __future__ import annotations

# Categories exposed in audit UI and API filters
AUDIT_CATEGORIES = (
    "Trading",
    "Treasury",
    "Settlement",
    "Allocation",
    "Rebalance",
    "Risk",
    "Infrastructure",
    "System",
)

# Map action_type prefix/exact match → category
_ACTION_CATEGORY_RULES: list[tuple[str, str]] = [
    ("WEEKLY_SETTLEMENT", "Settlement"),
    ("CLIENT_SETTLEMENT", "Settlement"),
    ("SETTLEMENT_", "Settlement"),
    ("PROFIT_ROUTING", "Treasury"),
    ("TREASURY_", "Treasury"),
    ("YIELD_SWEEP", "Treasury"),
    ("CLIENT_TOPUP", "Treasury"),
    ("ALLOCATION_", "Allocation"),
    ("REBALANCE_", "Rebalance"),
    ("RISK_", "Risk"),
    ("KILL_SWITCH", "Risk"),
    ("ORDER_REJECTED", "Risk"),
    ("EXCHANGE_", "Infrastructure"),
    ("INFRASTRUCTURE_", "Infrastructure"),
    ("AUTONOMOUS_TRADE", "Trading"),
    ("ORDER_FILLED", "Trading"),
    ("ORDER_CANCELLED", "Trading"),
    ("TRADE_EXECUTED", "Trading"),
    ("STRATEGY_", "System"),
    ("REPORT_", "System"),
    ("USER_", "System"),
    ("MANDATE_", "System"),
]


def categorize_action(action_type: str) -> str:
    upper = (action_type or "").upper()
    for prefix, category in _ACTION_CATEGORY_RULES:
        if upper.startswith(prefix) or upper == prefix.rstrip("_"):
            return category
    if "TRADE" in upper or "ORDER" in upper:
        return "Trading"
    return "System"


# Collapse noisy per-cycle reconnect logs into one summary action
INFRASTRUCTURE_SUMMARY_ACTION = "INFRASTRUCTURE_HEALTH_SUMMARY"
EXCHANGE_RECONNECT_ACTION = "EXCHANGE_RECONNECTED"
EXCHANGE_DISCONNECT_ACTION = "EXCHANGE_DISCONNECTED"
