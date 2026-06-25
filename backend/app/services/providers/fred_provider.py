"""FRED macro data provider — bond yields, inflation expectations, VIX proxy."""

from __future__ import annotations

import json
import logging
import os
import urllib.parse
import urllib.request
from datetime import datetime
from typing import Any

logger = logging.getLogger("nexa.fred_provider")

FRED_BASE = "https://api.stlouisfed.org/fred/series/observations"
DEFAULT_SERIES = {
    "DGS10": "10Y Treasury Yield",
    "DGS2": "2Y Treasury Yield",
    "T10Y2Y": "10Y-2Y Spread",
    "T10YIE": "10Y Breakeven Inflation",
    "VIXCLS": "VIX",
    "DTWEXBGS": "Trade Weighted USD Index",
}


def fetch_fred_series(series_id: str, limit: int = 5) -> list[dict[str, Any]]:
    api_key = os.environ.get("FRED_API_KEY", "")
    if not api_key:
        logger.debug("FRED_API_KEY not set — skipping %s", series_id)
        return []
    try:
        params = urllib.parse.urlencode({
            "series_id": series_id,
            "api_key": api_key,
            "file_type": "json",
            "sort_order": "desc",
            "limit": limit,
        })
        url = f"{FRED_BASE}?{params}"
        with urllib.request.urlopen(url, timeout=15) as resp:
            data = json.loads(resp.read().decode())
        return [
            {"date": o["date"], "value": float(o["value"]) if o["value"] != "." else None}
            for o in data.get("observations", [])
            if o.get("value") != "."
        ]
    except Exception as e:
        logger.warning("FRED fetch failed for %s: %s", series_id, e)
        return []


def fetch_macro_snapshot() -> dict[str, Any]:
    """Fetch latest macro indicators; returns empty values when API key absent."""
    snapshot: dict[str, Any] = {
        "source": "FRED",
        "fetched_at": datetime.utcnow().isoformat(),
        "series": {},
        "data_available": False,
    }
    for series_id, label in DEFAULT_SERIES.items():
        obs = fetch_fred_series(series_id, limit=1)
        if obs:
            snapshot["series"][series_id] = {
                "label": label,
                "latest": obs[0],
            }
            snapshot["data_available"] = True
    if snapshot["series"].get("DGS10") and snapshot["series"].get("DGS2"):
        y10 = snapshot["series"]["DGS10"]["latest"]["value"]
        y2 = snapshot["series"]["DGS2"]["latest"]["value"]
        if y10 is not None and y2 is not None:
            snapshot["yield_curve_inverted"] = y2 > y10
    return snapshot
