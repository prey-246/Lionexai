"""Shared constants for paper-trading validation metrics."""

EXECUTED_ACTIONS = (
    "AUTONOMOUS_TRADE_EXECUTED_BINANCE",
    "AUTONOMOUS_TRADE_EXECUTED_BYBIT",
    "AUTONOMOUS_TRADE_EXECUTED_VIA_BINANCE",
    "AUTONOMOUS_TRADE_EXECUTED_VIA_BYBIT",
    "ORDER_FILLED",
)

REJECTED_ACTIONS = (
    "RISK_REJECTION",
    "ORDER_REJECTED",
)

PAPER_TRADE_SOURCE = "AUTONOMOUS"

# period_label, period_spec ("today" | int days | None for all-time)
SNAPSHOT_PERIODS = (
    ("TODAY", "today"),
    ("7D", 7),
    ("14D", 14),
    ("30D", 30),
    ("ALL", None),
)

ROLLING_WINDOW_DAYS = 7

# Portfolio/strategy snapshots use these rolling windows (excludes TODAY)
SCOPED_SNAPSHOT_PERIODS = (
    ("7D", 7),
    ("14D", 14),
    ("30D", 30),
    ("ALL", None),
)

HISTORY_RETENTION_DAYS = 730

METRIC_TIMESERIES_FIELDS = (
    "win_rate_pct",
    "max_drawdown_pct",
    "total_pnl",
    "sharpe_ratio",
    "avg_return_pct",
    "fill_rate_pct",
)
