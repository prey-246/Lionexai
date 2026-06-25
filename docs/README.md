# NEXA Platform Documentation

Central index for all platform documentation. Last updated: **June 2026** (Phase 4–6 complete + production stability pass).

## Quick Links

| Document | Description |
|----------|-------------|
| **[PHASE6_INSTITUTIONAL_READINESS.md](./PHASE6_INSTITUTIONAL_READINESS.md)** | **Phase 6** — performance engine, live validation, treasury verification, LNX attribution, alpha evidence |
| **[PHASE5_AUDIT_REPORT.md](./PHASE5_AUDIT_REPORT.md)** | Phase 5 audit — demo vs validated, metric integrity |
| [PHASE5_ROADMAP.md](./PHASE5_ROADMAP.md) | Institutional readiness + Alpha evidence protocol (complete) |
| **[PHASE4_AUTONOMOUS_FUND_MANAGER.md](./PHASE4_AUTONOMOUS_FUND_MANAGER.md)** | Phase 4 complete reference — treasury, LNX, funds, productionization |
| [PHASE4_API_QUICK_REFERENCE.md](./PHASE4_API_QUICK_REFERENCE.md) | Phase 4 REST endpoints with request/response samples |
| [VALIDATION_ROADMAP_STATUS.md](./VALIDATION_ROADMAP_STATUS.md) | 5-stage institutional validation roadmap |
| [VALIDATION_REPORT.md](./VALIDATION_REPORT.md) | Validation framework, metrics, PDF reports |
| [API_REFERENCE.md](./API_REFERENCE.md) | Complete REST API endpoint catalog |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | System architecture, containers, core flows |
| [SYSTEM_ARCHITECTURE.md](./SYSTEM_ARCHITECTURE.md) | High-level diagrams and subsystem map |
| [EXECUTION_ARCHITECTURE.md](./EXECUTION_ARCHITECTURE.md) | Exchange adapters, autonomous executor |
| [DATABASE.md](./DATABASE.md) | Schema, tables, relationships, migrations |
| [DEMO_GUIDE.md](./DEMO_GUIDE.md) | Persona-driven demo scripts |
| [DEVELOPMENT.md](./DEVELOPMENT.md) | Local setup, tests, migrations, troubleshooting |
| [DEPLOYMENT.md](./DEPLOYMENT.md) | Production deployment guide |

## Archive

Historical phase reports live in [`archive/`](./archive/) and are not maintained for current features.

## Platform Status (June 2026)

| Area | Status |
|------|--------|
| **Phase 4 — Autonomous Multi-Asset Fund Manager** | ✅ Complete |
| **Phase 4 — LNX Treasury Economics & Settlement** | ✅ Complete |
| **Phase 5 — Validated performance layer** | ✅ Complete |
| **Phase 5 — Research Lab + Global Risk Engine** | ✅ Complete |
| **Phase 5 — Allocation integrity monitor** | ✅ Complete |
| **Phase 6 — Institutional metric engine** | ✅ Complete |
| **Phase 6 — Live validation + treasury verification** | ✅ Complete |
| **Phase 6 — Alpha Evidence Dashboard** | ✅ Complete |
| **Phase 6 — LNX attribution + execution lifecycle** | ✅ Complete |
| Institutional validation (Stages 1–5) | ✅ Complete |
| Autonomous paper trading (Binance + Bybit) | ✅ Wired |
| Institutional demo reset script | ✅ `reset_institutional_demo.py` |
| Fund target vs actual returns + provenance badges | ✅ `/fund-performance` |
| Intelligence Hub (coverage-aware sentiment) | ✅ `/intelligence` |
| Performance Reports (staff portfolio access) | ✅ `/reports` |

**Rollout note:** Phase 4 autonomous multi-asset execution is gated by `global_settings.autonomous_v2_enabled` (default `false`). Treasury settlement applies to `auto_managed` fund portfolios regardless. Seeded demo returns come from equity curves in Postgres — enable autonomous v2 for live execution.

## Data Provenance

Every performance surface labels its source:

| Label | Meaning |
|-------|---------|
| `DEMO` | Seeded institutional demo ledger |
| `VALIDATED_HISTORICAL` | Backtests / walk-forward / Monte Carlo on `market_bars` |
| `PAPER_LIVE` | Long-running autonomous paper trading |
| `LIVE_CAPITAL` | Reserved for future real-capital deployment |

## Demo Accounts

All demo users use password **`password123`** (after institutional reset):

| Email | Role | Portfolios |
|-------|------|------------|
| `client1@lionex.ai` | client | LNX-PRESERVE-001, LNX-BALANCED-001, LNX-ALPHA-001 |
| `client2@lionex.ai` | client | …-002 variants |
| `client3@lionex.ai` | client | …-003 variants |
| `admin@lionex.ai` | admin | Full access |
| `operator1@lionex.ai` | operator | Ops + validation + research lab |
| `risk1@lionex.ai` | risk_manager | Treasury + risk + research lab |

## Key UI Routes

### Client (Fund-First)

| Route | Purpose |
|-------|---------|
| `/dashboard` | Fund performance, treasury contributions, LNX |
| `/funds` | Invest; target weekly & monthly per fund |
| `/fund-performance` | Target vs actual returns + provenance badges |
| `/portfolios/{id}` | Returns, risk context, settlements, allocation, trades |
| `/allocation` | Live allocation engine weights |
| `/lnx` | LNX index, treasury NAV, reserve ratio (client-safe pool summary) |
| `/intelligence` | AI pulse with coverage-aware sentiment scores |
| `/market-intelligence` | Multi-asset pulse + news |
| `/simulator` | Growth projections from fund weekly targets |

### Operator / Risk / Admin

| Route | Purpose |
|-------|---------|
| `/research-lab` | Historical validation, global risk, alpha evidence |
| `/alpha-evidence` | Phase 6 Alpha 20% monthly evidence dashboard |
| `/treasury` | Treasury pools + analytics + routing ledger |
| `/validation` | Long-term validation (90D/180D/365D + Phase 4 metrics) |
| `/reports` | Weekly/monthly portfolio PDF reports |
| `/strategies` | Strategy registry + optimizer scores |
| `/execution-health` | Real-time execution monitoring |
| `/execution-monitor` | Per-exchange CCXT monitor |
| `/trade-explorer` | Historical trade search & filters |
| `/analytics/compare` | Portfolio & strategy comparison |
| `/stress-test` | Risk validation scenarios |
| `/audit` | Compliance audit trail (filter by category) |
| `/executive` | Admin executive summary |

## API Namespaces

| Prefix | Purpose | Roles |
|--------|---------|-------|
| `/api/funds/` | Fund invest, performance, institutional analytics | client + staff |
| `/api/validated/` | Research Lab — backtests, global risk, paper validation | operator, risk, admin |
| `/api/institutional/` | Phase 6 — live validation, treasury verify, alpha evidence, reports | mixed (see Swagger) |
| `/api/treasury/pools/summary` | Read-only pool balances for clients (LNX, dashboard) | all authenticated |
| `/api/treasury/pools` | Full pool management | admin, operator, risk_manager |
| `/api/intelligence/sentiment` | Batch AI pulse scores with coverage metadata | all authenticated |

Interactive docs: `http://localhost:8000/docs`

## Bootstrap & Demo Reset

```bash
docker compose -f docker-compose.prod.yml up --build -d
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head
docker compose -f docker-compose.prod.yml exec backend python scripts/seed_phase4.py

# Recommended for institutional demos (purges old demo data, re-seeds 9 portfolios)
docker compose -f docker-compose.prod.yml exec backend python scripts/reset_institutional_demo.py --confirm

docker compose -f docker-compose.prod.yml exec backend python -c \
  "from app.services.validation_service import update_validation_snapshots_job; update_validation_snapshots_job()"

# Refresh NLP sentiment (Intelligence Hub)
docker compose -f docker-compose.prod.yml exec backend python -c \
  "from app.services.nlp_service import run_nlp_analysis; run_nlp_analysis()"

# Rebuild frontend after UI changes (no hot-reload in prod compose)
docker compose -f docker-compose.prod.yml build frontend
docker compose -f docker-compose.prod.yml up -d frontend
```

Optional — enable live autonomous multi-asset manager:

```bash
docker compose -f docker-compose.prod.yml exec backend python scripts/reset_institutional_demo.py --confirm --enable-autonomous
```

## Known Integration Notes

1. **Portfolio list URL** — Use `GET /api/portfolios/` (trailing slash). Requests to `/api/portfolios` without a slash may drop the JWT on redirect; backend also exposes a no-slash alias.
2. **Treasury client access** — Clients must use `/api/treasury/pools/summary`, not `/api/treasury/pools`.
3. **Performance reports** — Staff (`admin`, `operator`, `risk_manager`) can generate reports for any portfolio; clients are scoped to their own.
4. **Intelligence sentiment** — Symbols without NLP news coverage show **NO DATA**, not synthetic 50% scores. WTI uses symbol `WTIUSD` in the pulse registry.
5. **Frontend rebuild** — Backend hot-reloads via volume mount; frontend requires `build frontend` after React changes.

## Data Sources (Summary)

| Type | Sources |
|------|---------|
| **Crypto prices** | Binance API (`binance` provider) |
| **Metals, energy, indices, FX** | yfinance (`yfinance` provider) |
| **Fallback** | Mock provider |
| **News** | CoinDesk RSS (hourly), Investing.com FX + Commodities RSS |
| **Macro (Phase 6)** | FRED API when `FRED_API_KEY` is set |
| **Portfolio returns** | Postgres `equity_curves` + `trades` (seeded in demo; live when autonomous runs) |

Details: [PHASE4 §14](./PHASE4_AUTONOMOUS_FUND_MANAGER.md#14-data-sources).
