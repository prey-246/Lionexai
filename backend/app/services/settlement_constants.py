"""Configuration for weekly client settlement and treasury profit routing."""

# Default weekly target returns by fund id (percent, e.g. 1.0 = 1% per week)
DEFAULT_FUND_WEEKLY_TARGETS = {
    "PRESERVE": 1.0,
    "BALANCE": 2.5,
    "ALPHA": 5.0,
}

# How excess profit is split across treasury pools (must sum to 100)
PROFIT_ROUTING_SPLIT = {
    "YIELD": 40.0,
    "GROWTH": 25.0,
    "RESERVE": 15.0,
    "OPERATIONS": 15.0,
    "LNX_INDEX": 5.0,
}

# Order to draw from when topping up client shortfalls (Yield first, then Reserve)
TOPUP_POOL_ORDER = ("YIELD", "RESERVE")
