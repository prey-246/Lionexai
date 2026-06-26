# NEXA Platform Architecture

This document provides a deep dive into the system architecture, database schema, API reference, and core execution flows within the NEXA platform.

**Last updated:** June 2026 — Phase 4–6 complete + Alpha Optimization + validation hardening.

---

## 1. System Overview

NEXA operates on a decoupled client-server architecture utilizing **FastAPI** (Python) for the backend and **Next.js** (TypeScript/React) for the frontend, communicating via REST and WebSockets.

### 1.1. Container Topology

1. **nexa_backend_prod**: Uvicorn ASGI server running FastAPI. Handles execution, risk logic, validation, treasury, and scheduled AI tasks. Hot-reloads via volume mount in `docker-compose.prod.yml`.
2. **nexa_frontend_prod**: Next.js production server. Requires rebuild after UI changes (no volume mount).
3. **nexa_db_prod**: PostgreSQL + TimescaleDB. Relational data and time-series tick data.
4. **nexa_redis_prod**: Redis 7. Cache and pub/sub for WebSocket broadcasting.

### 1.2. Phase Overview

| Phase | Focus |
|-------|-------|
| **Phase 4** | Autonomous multi-asset fund manager, treasury economics, LNX index, settlements |
| **Phase 5** | Validated historical performance, Research Lab, global risk, allocation integrity, provenance |
| **Phase 6** | Institutional metric engine, live validation, treasury verification, alpha evidence, reporting |
| **Alpha Optimization** | Grid search, best configs in `validated_fund_runs`, `LNX-*-VALIDATED` portfolios |

---

## 2. Database Schema (Domain Models)

The platform utilizes SQLAlchemy 2.0. Integer primary keys (`pk_id`) power foreign keys; string `id`s (e.g. `LNX-ALPHA-001`) are exposed to the frontend.

### 2.1. Governance & Security

- **User**: Authentication + `role_tier` (`admin`, `operator`, `risk_manager`, `client`).
- **Mandate**: Version-controlled risk parameters linked to portfolios.
- **GlobalSettings**: Singleton (`id="default"`). `environment_state`, kill switch, fees, `autonomous_v2_enabled`.
- **AuditLog**: Immutable ledger with `action_type`, `description`, `metadata_json`.

### 2.2. Capital & Trading

- **Portfolio**: Trading account with `total_equity`, `auto_managed`, `fund_pk_id`.
- **Trade**: Full execution metadata — `exchange`, `execution_latency_ms`, `strategy_name`, `trade_source`.
- **EquityCurve**: Time-series equity snapshots.
- **PortfolioAllocation**: Target and current weights for auto-managed portfolios.
- **ClientSettlement**: Weekly settlement records with treasury routing breakdown.

### 2.3. Phase 4 — Funds & Treasury

- **Fund**: PRESERVE / BALANCE / ALPHA with target weekly/monthly returns.
- **Asset**, **MarketBar**: Multi-asset universe and OHLCV storage.
- **TreasuryPool**, **TreasuryTransaction**: Six pools + immutable ledger.
- **LNXIndexSnapshot**: Daily composite index snapshots.
- **MarketRegime**, **GlobalMarketState**, **StrategyScore**: Regime and optimizer outputs.

### 2.4. Phase 5 — Validated Performance

- **ValidatedStrategyRun**: Backtest / walk-forward / Monte Carlo results with `metrics` JSON.
- **PaperTradingValidationSnapshot**: Paper-live rolling metrics by period.
- **AllocationIntegrityAlert**: Drift and solvency alerts from hourly scan.

### 2.5. Phase 6 — Institutional Readiness

- **LiveValidationSnapshot**: Paper-live validation with provenance.
- **TreasuryVerificationRun**: Solvency score and routing integrity checks.
- **LNXAttributionSnapshot**: Index movement decomposition.
- **ExecutionLifecycleEvent**: Signal → fill → settlement trace events.
- **InstitutionalReport**: Monthly fund reports with JSON/CSV export.
- **MacroDataSnapshot**: FRED macro series cache.

### 2.6. NEXA Intelligence (Alt-Data Layer)

- **MarketNewsArticle**: Scraped RSS articles.
- **NLPSentiment**: Per-article sentiment (-1.0 to 1.0).
- **MarketSensitivityScore**: Aggregated AI score per symbol. Uses column **`timestamp`** (not `computed_at`). Coverage metadata in `contributing_factors`: `DIRECT`, `ASSET_CLASS_PROXY`, or `NONE`.
- **EconomicEvent**: Macro calendar events scored into `GLOBAL_RISK`.

---

## 3. Core Execution Flows

### 3.1. Autonomous Portfolio Manager (Phase 4)

When `autonomous_v2_enabled=true`, `PortfolioManager` runs every 60 seconds:

```
RegimeEngine → AllocationEngine → Rebalance → AssetAdapter → Exchange/Simulated
    ↓
SettlementEngine (Mondays) → Treasury pools → LNXIndexEngine snapshot
```

### 3.2. Risk Engine Pipeline

Strict gatekeeper before any trade (manual or autonomous):

1. Global kill switch
2. Mandate kill switch
3. Capital / leverage / drawdown limits
4. AI sentiment gate on BUY orders (`MarketSensitivityScore` vs `extreme_bearish_threshold`)

### 3.3. Institutional Validation Pipeline

```
Autonomous Trades (trade_source=AUTONOMOUS)
    ↓
validation_service.compute_metrics()          ← operational dashboard
performance_engine.py                         ← equity-return Sharpe/Sortino (Phase 6)
live_validation_engine.py                     ← paper-live snapshots (Phase 6)
    ↓
validation_snapshots + live_validation_snapshots
    ↓
/validation UI + PDF reports + /api/institutional/*
```

### 3.4. Alpha Evidence Pipeline (Phase 6)

```
ValidatedStrategyRun (WALK_FORWARD, MONTE_CARLO, BACKTEST)
    + RealStrategyValidator historical test
    + live_validation_engine paper-live metrics
    ↓
AlphaEvidenceService.evaluate()
    ↓
verdict: SUPPORTED | PARTIALLY_SUPPORTED | NOT_SUPPORTED
    ↓
/research-lab + /alpha-evidence UI
```

### 3.5. Background Scheduled Tasks

| Job | Interval | Module |
|-----|----------|--------|
| Portfolio manager / algo executor | 60s | `portfolio_manager.py` / `algo_executor.py` |
| Validation snapshots | 15 min | `validation_service` |
| Live validation snapshots | 6 h | `live_validation_engine` |
| Paper validation snapshots | 6 h | `paper_trading_validation_service` |
| Allocation integrity scan | 1 h | `allocation_integrity_monitor` |
| Market bar ingestion | scheduled | `market_data_service` |
| News scraper | 1 h | `scrape_news.py` |
| NLP analyzer | 10 min | `nlp_service.run_nlp_analysis()` |
| Weekly settlement | Mon 01:00 UTC | `settlement_engine` |
| LNX snapshot | daily | `lnx_index.py` |
| Strategy optimizer | weekly | `strategy_optimizer.py` |

---

## 4. API Reference

Interactive Swagger: `http://localhost:8000/docs`

### 4.1. Core Endpoints

**Authentication**
- `POST /api/auth/token` — OAuth2 form login (username = email)
- `GET /api/users/me` — Current user profile

**Portfolio & Capital**
- `GET /api/portfolios/` — List portfolios (use trailing slash; no-slash alias available)
- `GET /api/portfolios/{id}/allocations` · `/settlements` · `/equity-curve`
- `POST /api/reports/generate` — Portfolio PDF reports (staff can access any portfolio via `portfolio_access.py`)

**Funds & Treasury**
- `GET /api/funds/` — Target + actual returns with provenance
- `POST /api/funds/{id}/invest`
- `GET /api/treasury/pools/summary` — Client-safe pool balances
- `GET /api/treasury/pools` — Full pool detail (staff only)
- `GET /api/treasury/pools/analytics` · `GET /api/treasury/routing`
- `GET /api/lnx/index` · `/history`

### 4.2. Phase 5 — Validated Performance (`/api/validated/`)

- `POST /api/validated/strategy/run` — Backtest / walk-forward / Monte Carlo
- `GET /api/validated/strategy/runs`
- `GET /api/validated/global-risk` — Global Risk Engine 0–100 composite
- `POST /api/validated/alpha/evidence` — Alpha target evaluation (legacy shape)
- `GET /api/validated/allocation/alerts`
- `POST /api/validated/paper/refresh` · `GET /api/validated/paper/snapshots`

### 4.3. Phase 6 — Institutional (`/api/institutional/`)

- `GET /api/institutional/performance/fund/{fund_id}` — Fund Analytics V2
- `GET /api/institutional/live-validation/snapshots`
- `GET /api/institutional/treasury/verify`
- `GET /api/institutional/lnx/attribution`
- `GET /api/institutional/execution/trace/{trade_id}`
- `GET /api/institutional/macro/snapshot`
- `POST /api/institutional/alpha/evidence/full` — Full evidence with verdict
- `POST /api/institutional/reports/monthly-fund`

### 4.4. Intelligence

- `GET /api/intelligence/news`
- `GET /api/intelligence/sentiment?limit=12` — Batch pulse scores (Intelligence Hub)
- `GET /api/intelligence/sentiment/{symbol}` — Single symbol with proxy/neutral fallback
- `GET /api/intelligence/economic-events`

### 4.5. WebSocket Streams

- `/ws/market` — Live market ticks
- `/ws/portfolio` — Portfolio updates
- `/ws/alerts` — System and risk alerts

See [API Reference](../api/api_reference.md) and [PHASE4_API_QUICK_REFERENCE.md](./PHASE4_API_QUICK_REFERENCE.md) for the full catalog.

---

## 5. Frontend Architecture

- **Next.js App Router** under `frontend/src/app/`
- **Role-based middleware** (`middleware.ts`) — deny-by-default route allow-list per role
- **API client** (`frontend/src/lib/api.ts`) — JWT from cookie, centralized fetch wrapper
- **Provenance badges** on fund performance and validation surfaces

### Role → Route Access (summary)

| Role | Notable routes |
|------|----------------|
| client | `/dashboard`, `/funds`, `/lnx`, `/intelligence`, `/allocation` |
| operator | + `/research-lab`, `/alpha-evidence`, `/reports`, `/validation`, `/treasury` |
| risk_manager | + `/research-lab`, `/alpha-evidence`, `/stress-test`, `/mandates` |
| admin | All routes |

---

## 6. Key Backend Modules

```
backend/app/
├── analytics/performance_engine.py      # Phase 6 equity-return metrics
├── engines/
│   ├── allocation_engine.py
│   ├── global_risk_engine.py            # Composite 0–100 risk score
│   ├── lnx_index.py
│   ├── regime_engine.py
│   └── macro_intelligence.py
├── services/
│   ├── alpha_evidence_service.py
│   ├── live_validation_engine.py
│   ├── treasury_verification_engine.py
│   ├── lnx_attribution_engine.py
│   ├── sentiment_service.py             # Coverage-aware pulse resolution
│   ├── portfolio_manager.py
│   └── settlement_engine.py
├── validation/real_strategy_validation.py
└── api/
    ├── portfolio_access.py              # Staff portfolio access helper
    └── routes/
        ├── institutional.py
        ├── validated_performance.py
        └── treasury.py
```
