# Phase 6 — Institutional Production Readiness

**Status:** ✅ Complete (June 2026)

Phase 6 transitions LionexAI from a demo platform to an **institutional validation platform** where every performance number can be explained, verified, and defended.

## Data Provenance Model

| Label | Meaning |
|-------|---------|
| `DEMO` | Simulated exchange / seeded institutional demo ledger |
| `VALIDATED_HISTORICAL` | Backtests, walk-forward, Monte Carlo on market bars |
| `PAPER_LIVE` | Long-running autonomous paper trading (non-simulated venue when enabled) |
| `LIVE_CAPITAL` | Reserved for future real-capital deployment |

All dashboards display provenance badges. Metrics never mix provenance without explicit labeling.

**June 2026 additions:**
- `/fund-performance` — VALIDATED_HISTORICAL primary; admin **Show demo comparison** for client demo ledgers only
- `/validation` — **Validated Historical** default (`data_source=validated`); **Demo Ledger** toggle for ops
- `LNX-*-VALIDATED` reference portfolios on `admin@google.com` — see [INSTITUTIONAL_PERFORMANCE_REPORT.md](./INSTITUTIONAL_PERFORMANCE_REPORT.md)

## Deliverables

### 1. Performance Engine (`backend/app/analytics/performance_engine.py`)
Single source of truth for Sharpe, Sortino, drawdown, volatility, Calmar — **equity returns, not dollar PnL**.

### 2. Live Validation Engine (`backend/app/services/live_validation_engine.py`)
Paper-live snapshots: daily/weekly/monthly returns, rolling Sharpe/Sortino/drawdown, exposure, allocation drift, treasury contributions.

- `GET /api/institutional/live-validation/snapshots`
- `POST /api/institutional/live-validation/refresh`

### 3. Treasury Verification Engine (`backend/app/services/treasury_verification_engine.py`)
Validates routing integrity, settlement coverage, pool balance; stress tests; **Treasury Solvency Score**.

- `GET /api/institutional/treasury/verify?persist=true`
- `GET /api/institutional/treasury/verification-runs`

### 4. LNX Attribution Engine (`backend/app/services/lnx_attribution_engine.py`)
Explains index movements by treasury NAV, AUM, reserve, yield delivery, strategy performance.

- `GET /api/institutional/lnx/attribution`
- `GET /api/institutional/lnx/attribution/history`

### 5. Execution Lifecycle (`backend/app/services/execution_lifecycle_service.py`)
Trace: signal → allocation → order → fill → position → settlement → treasury.

- `GET /api/institutional/execution/trace/{trade_id}`
- `GET /api/institutional/execution/events`

### 6. Multi-Asset Classification (`backend/app/services/asset_classification.py`)
Bonds, sector ETFs, vol products, commodity baskets with region, risk tier, liquidity/volatility scores.

- `POST /api/institutional/assets/seed-extended`
- `GET /api/institutional/assets/{symbol}/classification`

### 7. Market Intelligence V2
FRED provider (`backend/app/services/providers/fred_provider.py`); GlobalRiskEngine extended with VIX, yield curve, DXY, inflation expectations.

Set `FRED_API_KEY` for live macro feeds.

- `GET /api/institutional/macro/snapshot`

### 8. Fund Analytics V2
Target vs Realized vs Validated columns on `/fund-performance`.

- `GET /api/institutional/performance/fund/{fund_id}`

### 9. Institutional Reporting
Monthly fund reports with JSON/CSV export.

- `POST /api/institutional/reports/monthly-fund`
- `GET /api/institutional/reports/institutional`
- `GET /api/institutional/reports/institutional/{id}/export/json|csv`

### 10. Alpha Evidence Dashboard
Combines historical, walk-forward, Monte Carlo, paper-live with SUPPORTED / PARTIALLY_SUPPORTED / NOT_SUPPORTED verdict.

- **API:** `POST /api/institutional/alpha/evidence/full`
- **UI:** `/alpha-evidence`, `/research-lab`

## Frontend Surfaces

| Route | Audience | Purpose |
|-------|----------|---------|
| `/alpha-evidence` | operator, risk, admin | Full Alpha 20% evidence dashboard |
| `/research-lab` | operator, risk, admin | Run backtests + inline alpha evaluate + global risk |
| `/fund-performance` | all | Provenance badges + validated columns |
| `/intelligence` | client + staff | Coverage-aware AI pulse (NO DATA when no NLP coverage) |
| `/lnx` | client + staff | Uses `/api/treasury/pools/summary` (not staff-only pools) |
| `/reports` | operator, risk, admin | Portfolio PDF reports; staff can report on any portfolio |

## Migration

```bash
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head
```

Creates Phase 5 + Phase 6 tables:

- `live_validation_snapshots`
- `execution_lifecycle_events`
- `lnx_attribution_snapshots`
- `treasury_verification_runs`
- `institutional_reports`
- `macro_data_snapshots`
- Asset classification columns on `assets`

Revisions: `a1b2c3d4e5f6_p5_validated`, `b2c3d4e5f6a7_p6_institutional`

## Schedulers

| Job | Interval |
|-----|----------|
| Live validation snapshots | 6 hours |
| Paper validation snapshots | 6 hours |
| Validation operational snapshots | 15 minutes |
| Allocation integrity scan | 1 hour |
| NLP sentiment analysis | 10 minutes |

## Enabling Paper-Live

1. Set `autonomous_v2_enabled=true` in global settings
2. Configure exchange API keys (non-simulated venue)
3. Allow system to run — live validation labels `PAPER_LIVE` when simulated trade ratio drops

## Production Stability Fixes (June 2026)

| Issue | Fix |
|-------|-----|
| Alpha evidence `TypeError` on null metrics | `_safe_avg()` in `alpha_evidence_service.py` |
| Global Risk Engine crash in Research Lab | Use `MarketSensitivityScore.timestamp` not `computed_at` |
| Treasury 403 on LNX for clients | `GET /api/treasury/pools/summary` + frontend switch |
| Reports "portfolio not found" for admin | `portfolio_access.py` staff access + portfolio list URL fix |
| Intelligence fake 50% scores | Coverage metadata; show NO DATA when `coverage=NONE` |
| WTI pulse symbol mismatch | Registry uses `WTIUSD` consistently |
| JWT lost on portfolio list | Trailing slash + no-slash alias on `GET /api/portfolios` |

## Backward Compatibility

- All Phase 6 APIs are additive under `/api/institutional/*`
- Existing `/api/validation`, `/api/funds`, `/api/lnx` routes unchanged
- No breaking schema changes to existing tables (asset columns nullable)
- Phase 5 `/api/validated/alpha/evidence` remains; Phase 6 full evidence preferred

## Related Docs

- [PHASE5_ROADMAP.md](./PHASE5_ROADMAP.md) — Research Lab bootstrap
- [PHASE5_AUDIT_REPORT.md](./PHASE5_AUDIT_REPORT.md) — Pre-Phase-5 audit
- [ARCHITECTURE.md](./ARCHITECTURE.md) — System overview
- [README.md](../README.md) — Quick start and demo accounts
