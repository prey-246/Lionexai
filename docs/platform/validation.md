# Validation Framework

Institutional validation separates **historical backtests** from **operational demo ledger** data.

---

## Data Sources

| Mode | API | UI | Provenance |
|------|-----|-----|------------|
| **Validated Historical** (default) | `?data_source=validated` | `/validation` toggle | `VALIDATED_HISTORICAL` |
| **Demo Ledger** | `?data_source=demo` | `/validation` toggle | `DEMO` |

Never mix without explicit admin toggle.

---

## Metrics (Equity-Based)

Computed via `PerformanceEngine` on equity curves — not multiplicative compounding of individual trade returns.

| Metric | Description |
|--------|-------------|
| Sharpe / Sortino | Daily returns, annualized √252 |
| Max Drawdown | Peak-to-trough on equity curve |
| Win Rate | Closed trades or rebalance periods (validated) |
| Profit Factor | Gross wins / gross losses |
| Fill Rate / Latency | Demo mode only (from audit logs) |

---

## Rolling Periods

TODAY, 7D, 14D, 30D, 90D, 180D, 365D, ALL — refreshed every **15 minutes** + daily archive at 00:05 UTC.

---

## Research Lab

`/research-lab` — strategy backtests, walk-forward, Monte Carlo on `market_bars`.

- `POST /api/validated/strategy/run`
- Results in `validated_strategy_runs`

---

## Alpha Evidence

`/alpha-evidence` — objective verdict on ALPHA 20% monthly target combining historical, walk-forward, Monte Carlo, and paper-live checks.

---

## Live Validation

`live_validation_snapshots` updated every 6 hours. Provenance `PAPER_LIVE` or `DEMO` based on trade exchange mix.

---

## PDF Reports

`GET /api/validation/report/{period}` — institutional PDF with charts.

---

## Related

- [Platform Pages Guide](../guides/platform_pages.md) — full metric formulas per page
- [Archive: Validation Report](../archive/VALIDATION_REPORT.md) — extended operational metrics reference
