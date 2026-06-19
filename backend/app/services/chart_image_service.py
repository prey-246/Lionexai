"""Generate chart images as base64 PNG strings for PDF embedding."""

from __future__ import annotations

import base64
import io
from datetime import datetime, timezone

import matplotlib

matplotlib.use("Agg")

import matplotlib.dates as mdates
import matplotlib.pyplot as plt

NEXA_GOLD = "#D4AF37"
NEXA_TEAL = "#22d3ee"
NEXA_DARK = "#111827"
NEXA_RED = "#ef4444"
NEXA_GREEN = "#10b981"


def _fig_to_base64(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("ascii")


def _parse_times(series: list[dict]) -> tuple[list[datetime], list[float]]:
    times: list[datetime] = []
    values: list[float] = []
    for point in series:
        raw_time = point.get("time")
        if raw_time is None:
            continue
        if isinstance(raw_time, (int, float)):
            times.append(datetime.fromtimestamp(raw_time, tz=timezone.utc))
        else:
            times.append(datetime.fromisoformat(str(raw_time).replace("Z", "+00:00")))
        values.append(float(point["value"]))
    return times, values


def time_series_chart(
    series: list[dict] | None,
    title: str,
    ylabel: str,
    color: str = NEXA_GOLD,
) -> str | None:
    if not series or len(series) < 2:
        return None
    times, values = _parse_times(series)
    if len(times) < 2:
        return None

    fig, ax = plt.subplots(figsize=(7.2, 2.6))
    ax.plot(times, values, color=color, linewidth=1.8)
    ax.fill_between(times, values, 0, alpha=0.08, color=color)
    ax.set_title(title, fontsize=11, color=NEXA_DARK, fontweight="bold", pad=8)
    ax.set_ylabel(ylabel, fontsize=9)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))
    ax.grid(True, alpha=0.25, linestyle="--")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.autofmt_xdate(rotation=30)
    return _fig_to_base64(fig)


def bar_chart(
    series: list[dict] | None,
    title: str,
    ylabel: str,
    color: str = NEXA_GOLD,
    positive_negative: bool = False,
) -> str | None:
    if not series:
        return None
    times, values = _parse_times(series)
    if not times:
        return None

    fig, ax = plt.subplots(figsize=(7.2, 2.6))
    if positive_negative:
        bar_colors = [NEXA_GREEN if v >= 0 else NEXA_RED for v in values]
        ax.bar(times, values, color=bar_colors, width=0.8)
        ax.axhline(0, color="#9ca3af", linewidth=0.8)
    else:
        ax.bar(times, values, color=color, width=0.8, alpha=0.85)
    ax.set_title(title, fontsize=11, color=NEXA_DARK, fontweight="bold", pad=8)
    ax.set_ylabel(ylabel, fontsize=9)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))
    ax.grid(True, axis="y", alpha=0.25, linestyle="--")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.autofmt_xdate(rotation=30)
    return _fig_to_base64(fig)


def histogram_values(values: list[float], title: str, xlabel: str, bins: int = 12) -> str | None:
    if not values:
        return None
    fig, ax = plt.subplots(figsize=(7.2, 2.6))
    counts, edges, patches = ax.hist(values, bins=bins, color=NEXA_TEAL, edgecolor="white", alpha=0.85)
    for patch, left_edge in zip(patches, edges[:-1]):
        if left_edge < 0:
            patch.set_facecolor(NEXA_RED)
        elif left_edge >= 0:
            patch.set_facecolor(NEXA_GREEN)
    ax.set_title(title, fontsize=11, color=NEXA_DARK, fontweight="bold", pad=8)
    ax.set_xlabel(xlabel, fontsize=9)
    ax.set_ylabel("Count", fontsize=9)
    ax.grid(True, axis="y", alpha=0.25, linestyle="--")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    return _fig_to_base64(fig)


def pie_chart(labels: list[str], sizes: list[float], title: str) -> str | None:
    if not labels or not sizes or sum(sizes) <= 0:
        return None
    colors = [NEXA_GOLD, NEXA_TEAL, "#6366f1", "#f97316", "#a855f7"][: len(labels)]
    fig, ax = plt.subplots(figsize=(4.5, 3.2))
    ax.pie(
        sizes,
        labels=labels,
        autopct="%1.1f%%",
        startangle=90,
        colors=colors,
        textprops={"fontsize": 8},
    )
    ax.set_title(title, fontsize=11, color=NEXA_DARK, fontweight="bold", pad=8)
    return _fig_to_base64(fig)


def generate_validation_chart_images(chart_data: dict) -> dict[str, str | None]:
    chart_data = chart_data or {}
    cumulative = chart_data.get("cumulative_pnl") or chart_data.get("equity_curve")

    return {
        "capital_curve": time_series_chart(cumulative, "Capital Curve (Cumulative P&L)", "P&L ($)", NEXA_GOLD),
        "drawdown_curve": time_series_chart(chart_data.get("drawdown_series"), "Drawdown Curve", "Drawdown (%)", NEXA_RED),
        "daily_pnl": bar_chart(chart_data.get("daily_pnl"), "Daily P&L", "P&L ($)", positive_negative=True),
        "daily_trades": bar_chart(chart_data.get("daily_trades"), "Daily Trade Volume", "Trades", NEXA_TEAL),
        "daily_returns": time_series_chart(chart_data.get("daily_returns"), "Daily Returns", "Return (%)", NEXA_TEAL),
        "rolling_win_rate": time_series_chart(chart_data.get("rolling_win_rate"), "Rolling Win Rate (7D)", "Win Rate (%)", NEXA_GREEN),
        "rolling_drawdown": time_series_chart(chart_data.get("rolling_drawdown"), "Rolling Drawdown (7D)", "Drawdown (%)", NEXA_RED),
    }


def latency_histogram(latencies: list[float]) -> str | None:
    if len(latencies) < 2:
        return None
    return histogram_values(
        latencies,
        "Order Latency Distribution",
        "Latency (ms)",
        bins=min(12, max(5, len(latencies) // 3)),
    )


def pnl_histogram(trade_pnls: list[float]) -> str | None:
    if len(trade_pnls) < 2:
        return None
    return histogram_values(
        trade_pnls,
        "Trade P&L Distribution",
        "P&L ($)",
        bins=min(12, max(5, len(trade_pnls) // 2)),
    )
