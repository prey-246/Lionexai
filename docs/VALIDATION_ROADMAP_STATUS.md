# NEXA Institutional Validation Roadmap — Completion Status

Last updated: June 2026 (validation hardening + alpha optimization)

## June 2026 Update

- **Validation dashboard** now defaults to **Validated Historical** backtests; Demo Ledger is an explicit admin toggle.
- **Fund Performance** shows validated metrics first; admin can enable demo comparison column.
- Operational demo snapshots (`validation_snapshots`) use equity-based metrics; overflow bug fixed.

## Executive Summary

| Stage | Focus | Completion | Status |
|-------|--------|------------|--------|
| **Stage 1** | Paper trading validation + trade capture + rolling stats | **100%** | Complete. Metrics are data-dependent. |
| **Stage 2** | 30-day validation dashboard | **100%** | Complete. |
| **Stage 3** | Institutional PDF reports | **100%** | Complete. Chart rendering is data-dependent. |
| **Stage 4** | Continuous validation engine + archival | **100%** | Complete. History grows daily. |
| **Stage 5** | Platform analytics & explorer tools | **95%** | Backend complete. Final UI pages pending. |

**Overall roadmap: ~99% complete.** The backend is feature-complete. Remaining work is on the frontend.

**Documentation index:** [docs/README.md](./README.md) · [API_REFERENCE.md](./API_REFERENCE.md) · [VALIDATION_REPORT.md](./VALIDATION_REPORT.md)

---

## Stage 1 — Extend Paper Trading Validation (100%)

### Done
- Trade model extended: `exchange`, `execution_latency_ms`, `strategy_name`, `rejection_reason`, `trade_source`
- Migration: `b7c3e1a42f90_extend_trade_validation_fields.py`
- Algo executor fills fields + creates rejection records
- Scheduler: 15-min interval + immediate startup run
- Rolling periods: TODAY, 7D, 14D, 30D, ALL
- Metrics: win rate, avg return, Sharpe, drawdown, profit factor, daily/weekly/monthly PnL
- Paper-only gate (`trade_source == AUTONOMOUS`)
- Legacy 3-day summary preserved

### Notes
- Metrics will show zeros until autonomous strategies are active and generate trade data. This is by design.

---

## Stage 2 — Validation Dashboard (100%)

### Done
- Period tabs: Today, 7D, 14D, 30D, All Time
- KPI grid: orders, best/worst portfolio/strategy, exchange split
- Charts: cumulative PnL, daily PnL/trades/returns, rolling win rate/drawdown, weekly/monthly PnL
- Winning/losing counts, largest win/loss on UI
- PDF download buttons (period, weekly, monthly)
- 3-day legacy summary panel
- Historical metric charts from daily archive

---

## Stage 3 — Institutional PDF Reports (100%)

### Done
- `validation_report_service.py` — full institutional context
- `chart_image_service.py` — matplotlib PNG → base64 embedding
- 11-section template: executive summary, capital/drawdown curves, risk, trade distribution, portfolio/strategy/exchange performance, top symbols, largest winners/losers, latency, risk events, system health
- Endpoints: `/report/pdf`, `/report/pdf/weekly`, `/report/pdf/monthly`, `/report/pdf/30-day`
- `reports.py` consolidated to shared `pdf_service.py`

### Notes
- Chart sections will populate once sufficient trade history is generated.

---

## Stage 4 — Continuous Validation Engine (100%)

### Done
- `validation_snapshot_history` append-only daily archive
- Migration: `c4d8e2f91a03_validation_snapshot_history.py`
- 730-day retention + auto purge
- Portfolio + strategy snapshot keys (`PORTFOLIO_*`, `STRATEGY_*`)
- Custom date-range API: `GET /api/validation/snapshots/range`
- History API: `GET /api/validation/history`
- Metric time-series: `GET /api/validation/history/metrics`
- Daily archive on each scheduler run + cron at 00:05 UTC
- Metadata fields promoted to first-class columns via migration `4a92414eca12`.

---

## Stage 5 — Outstanding Platform Features (95%)

### Done
| # | Requirement | Implementation |
|---|-------------|----------------|
| 1 | Strategy analytics | `GET /api/analytics/strategies` + live table on `/strategies` |
| 2 | Portfolio analytics | Existing per-portfolio stats + compare tool |
| 3 | Execution analytics | `/execution-health`, `/execution-monitor` (pre-existing) |
| 4 | Advanced reporting | Validation PDFs + `/reports` in sidebar |
| 5 | Investor dashboard metrics | `/executive` bug fixed (success rate metric) |
| 6 | Enhanced audit history | System-wide trail for admin/operator/risk; search + exchange filters |
| 7 | Historical trade explorer | `GET /api/trades/` + `/trade-explorer` page |
| 8 | Strategy comparison | `GET /api/analytics/strategies/compare` + `/analytics/compare` |
| 9 | Portfolio comparison | `GET /api/analytics/portfolios/compare` + `/analytics/compare` |
| 10 | Advanced search/filtering | Trade explorer + audit filters |

### Remaining Polish (~5%)
- UI for Trade Explorer and Analytics Comparison pages.
- Backtest results not wired to strategies page UI
- Risk events not shown on portfolio detail page

---

## API Reference (New Stage 4–5 Endpoints)

```
GET  /api/trades/                          Trade explorer (filters + pagination)
GET  /api/analytics/strategies             Live strategy performance
GET  /api/analytics/portfolios/compare     Portfolio side-by-side
GET  /api/analytics/strategies/compare     Strategy side-by-side
GET  /api/validation/history               Daily snapshot archive
GET  /api/validation/history/metrics       Rolling metric time-series
GET  /api/validation/snapshots/range       Custom date-range validation
GET  /api/audit/?search=&exchange=&start_date=  Enhanced audit trail
```

---

## Session TODO Audit

All session todos from Stages 1–5 were marked **completed**:

| Todo ID | Task | Status |
|---------|------|--------|
| s3-1 | Chart image service | ✅ |
| s3-2 | Validation report service | ✅ |
| s3-3 | Institutional PDF template | ✅ |
| s3-4 | PDF API endpoints | ✅ |
| s3-5 | Consolidate reports.py | ✅ |
| s3-6 | Frontend PDF downloads | ✅ |
| s4-1 | History model + migration | ✅ |
| s4-2 | Validation service refactor | ✅ |
| s4-3 | History/range API | ✅ |
| s4-4 | Scheduler + archival | ✅ |
| s4-5 | Frontend history API | ✅ |
| Stage 1 todos (1–5) | Trade model, executor, validation service, API, frontend | ✅ |

---

## Verification Checklist

```bash
# Apply migrations
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head

# Refresh validation snapshots + archive
docker compose -f docker-compose.prod.yml exec backend python -c \
  "from app.services.validation_service import update_validation_snapshots_job; update_validation_snapshots_job()"

# Rebuild frontend
docker compose -f docker-compose.prod.yml build frontend
docker compose -f docker-compose.prod.yml up -d frontend
```

**Pages to verify:** `/validation`, `/trade-explorer`, `/analytics/compare`, `/strategies`, `/audit`, `/executive`, `/reports`
