# Phase 5 — Institutional Readiness Roadmap

**Status:** ✅ Complete (June 2026)

## Guiding Principle

**Never inflate numbers.** Provenance classes are enforced across UI and API:

| Provenance | Meaning | Where shown |
|------------|---------|-------------|
| `DEMO` | Seeded ledger (`reset_institutional_demo.py`) | Fund Performance badge |
| `PAPER_LIVE` | Autonomous trades on live prices, simulated fills | Paper / live validation snapshots |
| `VALIDATED_HISTORICAL` | Backtests on `market_bars` | Research Lab, `validated_strategy_runs` |

---

## Step 1 — Bootstrap ✅

```bash
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head
docker compose -f docker-compose.prod.yml exec backend python scripts/seed_phase4.py
docker compose -f docker-compose.prod.yml exec backend python scripts/reset_institutional_demo.py --confirm
```

Migration: `a1b2c3d4e5f6_p5_validated`

## Step 2 — Historical Validation (Research Lab) ✅

1. Log in as `operator1@google.com` or `admin@google.com`
2. Open `/research-lab`
3. Run backtests per strategy × symbol (BTC/USDT, XAUUSD, etc.)
4. Run **Alpha 20% Monthly Evidence** — uses Phase 6 institutional API

**API:**
```http
POST /api/validated/strategy/run
GET  /api/validated/strategy/runs
GET  /api/validated/global-risk
POST /api/institutional/alpha/evidence/full   # preferred (Phase 6)
POST /api/validated/alpha/evidence            # legacy alias
```

**UI:** Global Risk Engine card loads from `GET /api/validated/global-risk`. Requires `MarketSensitivityScore.timestamp` ordering (fixed June 2026).

## Step 3 — Allocation Integrity ✅

```http
POST /api/validated/allocation/integrity-scan
GET  /api/validated/allocation/alerts
```

Scheduled hourly when backend runs.

## Step 4 — Paper Trading Validation ✅

```http
POST /api/validated/paper/refresh
GET  /api/validated/paper/snapshots?period=90D
```

Phase 6 live validation extends this: `GET /api/institutional/live-validation/snapshots`

## Step 5 — Alpha 20% Monthly Evidence Protocol ✅

**Founder target:** 20%+ monthly compounded on Alpha fund.

**Framework (does not fake results):**

1. `POST /api/institutional/alpha/evidence/full` with `{ "fund_id": "ALPHA", "target_monthly_pct": 20 }`
2. Engine combines:
   - Historical validation (`RealStrategyValidator`)
   - Walk-forward and Monte Carlo from `validated_strategy_runs`
   - Paper-live metrics from auto-managed ALPHA portfolios
3. Returns `verdict`: `SUPPORTED` | `PARTIALLY_SUPPORTED` | `NOT_SUPPORTED` + `rationale`

**UI:** `/alpha-evidence` (dashboard) and `/research-lab` (inline evaluate button)

**Expected honest outcome:** Historical single-asset strategies on daily bars do not sustain 20% monthly compounded. Documented evidence replaces marketing claims.

## Step 6 — Client Experience ✅

Clients see: Fund, risk profile, yield, returns, treasury summary, LNX, allocation weights, Intelligence Hub.

Clients do **not** see: Research Lab, Alpha Evidence, validation internals, strategy keys.

## Step 7 — Provider Expansion (Partial) ✅

- FRED macro provider wired (`fred_provider.py`, `FRED_API_KEY`)
- RSS news: CoinDesk, Investing.com
- Planned: Reuters-style feeds, central bank calendars

---

## Deliverables Summary

| Deliverable | Path |
|-------------|------|
| Real strategy validation | `backend/app/validation/real_strategy_validation.py` |
| Validated runs table | `validated_strategy_runs` |
| Paper trading snapshots | `paper_trading_validation_snapshots` |
| Allocation alerts | `allocation_integrity_alerts` |
| Global risk engine | `backend/app/engines/global_risk_engine.py` |
| Research Lab UI | `/research-lab` |
| Institutional fund API | `GET /api/funds/{id}/institutional` |
| Validated API router | `backend/app/api/routes/validated_performance.py` |
| Provenance field | `data_provenance` on fund responses |

See [PHASE5_AUDIT_REPORT.md](./PHASE5_AUDIT_REPORT.md) for the pre-Phase-5 audit and [PHASE6_INSTITUTIONAL_READINESS.md](./PHASE6_INSTITUTIONAL_READINESS.md) for Phase 6 extensions.
