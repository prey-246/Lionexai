# UnifyX / NEXA MVP

A production-grade quantitative wealth management platform for autonomous multi-asset fund management, institutional treasury economics, backtesting, paper-trading with risk controls, live exchange testnets (Binance, Bybit), and long-horizon validation through rolling metrics, PDF reports, and analytics tooling.

**Status**: Phase 4–6 Complete · Institutional Validation Platform · Production Stability Pass (June 2026) · Live Paper Trading on Binance Testnet & Bybit Demo

## What's New in Phase 4

Phase 4 delivers an **Autonomous Multi-Asset AI Fund Manager** with **LNX Treasury Economics**:

- **Three Lionex Funds** — Preserve (1%/wk · 4.33%/mo), Balance (2.5%/wk · 10.82%/mo), Alpha (5%/wk · 21.65%/mo)
- **Target vs actual returns** — `/fund-performance` and `GET /api/funds/` show equity-weighted realized weekly/monthly/inception returns alongside settlement targets
- **Weekly settlement engine** — guaranteed client NAV growth; excess profit routed to treasury pools (Yield, Growth, Reserve, Operations, LNX_INDEX)
- **Multi-asset universe** — crypto, gold (XAUUSD), FX, energy, indices via unified `market_bars` + provider layer
- **Autonomous allocation & execution** — regime-aware weights, AssetAdapter routing, central `PortfolioManager`
- **LNX Ecosystem Index** — backend-computed composite with treasury NAV, AUM, reserve ratio, daily snapshots
- **Expanded market intelligence** — CoinDesk + Investing.com RSS, Gold/FX NLP, `/market-intelligence` dashboard
- **Fund-first client UX** — `/funds`, `/fund-performance`, portfolio settlement history, treasury contributions on dashboard
- **Extended validation** — 90D / 180D / 365D periods + fund/treasury/LNX/yield-delivery metrics
- **Institutional demo reset** — `reset_institutional_demo.py` purges and re-seeds nine LNX portfolios with 13 weeks of activity

Full technical reference: **[docs/PHASE4_AUTONOMOUS_FUND_MANAGER.md](docs/PHASE4_AUTONOMOUS_FUND_MANAGER.md)**

## What's New in Phase 5 & 6

### Phase 5 — Institutional Readiness
- **Data provenance** — `DEMO`, `VALIDATED_HISTORICAL`, `PAPER_LIVE`, `LIVE_CAPITAL` badges on fund and validation surfaces
- **Research Lab** (`/research-lab`) — historical backtests, walk-forward, Monte Carlo; global risk score; alpha evidence evaluate
- **Global Risk Engine** — composite 0–100 score fusing macro, NLP sentiment, volatility, FRED inputs (`GET /api/validated/global-risk`)
- **Validated strategy runs** — persisted backtests in `validated_strategy_runs` (`POST /api/validated/strategy/run`)
- **Allocation integrity monitor** — hourly drift/solvency scan with alerts
- **Institutional fund analytics** — `GET /api/funds/{id}/institutional`

See **[docs/PHASE5_ROADMAP.md](docs/PHASE5_ROADMAP.md)** and **[docs/PHASE5_AUDIT_REPORT.md](docs/PHASE5_AUDIT_REPORT.md)**

### Phase 6 — Institutional Production Readiness
- **Performance engine** — equity-return Sharpe, Sortino, drawdown (not dollar PnL)
- **Live validation engine** — paper-live snapshots every 6 hours
- **Treasury verification** — solvency score, routing integrity, stress tests
- **LNX attribution** — explains index moves by component
- **Execution lifecycle** — trace trades signal → settlement → treasury
- **Alpha Evidence Dashboard** (`/alpha-evidence`) — objective 20% monthly verdict with historical + walk-forward + Monte Carlo + paper-live
- **Fund Analytics V2** — target vs realized vs validated on `/fund-performance`
- **FRED macro feeds** — VIX, yield curve, DXY when `FRED_API_KEY` is set

See **[docs/PHASE6_INSTITUTIONAL_READINESS.md](docs/PHASE6_INSTITUTIONAL_READINESS.md)**

### Alpha Optimization & Validation Hardening (June 2026)
- **Alpha Optimization Program** — grid search over allocation, regime, rebalancing, portfolio construction; best configs promoted to `SELECTED_BEST` runs ([docs/ALPHA_OPTIMIZATION_PROGRAM.md](docs/ALPHA_OPTIMIZATION_PROGRAM.md))
- **Institutional performance report** — honest post-optimization CAGR / Sharpe / drawdown on ~5yr aligned `market_bars` ([docs/INSTITUTIONAL_PERFORMANCE_REPORT.md](docs/INSTITUTIONAL_PERFORMANCE_REPORT.md))
- **Validated reference portfolios** — `LNX-PRESERVE-VALIDATED`, `LNX-BALANCE-VALIDATED`, `LNX-ALPHA-VALIDATED` owned by **`admin@google.com`**; regenerated from best backtest runs
- **Fund Performance** (`/fund-performance`) — primary view is **VALIDATED_HISTORICAL**; admin **Show demo comparison** adds a red Demo Ledger column (client portfolios only, excludes `*-VALIDATED`)
- **Long-Term Validation** (`/validation`) — defaults to **Validated Historical** backtests; **Demo Ledger** toggle for operational paper-trading snapshots
- **Metrics integrity** — validation Sharpe/drawdown computed from **equity curves** (not compounded per-trade returns); overflow values sanitized on API read
- **Demo accounts** — all seed scripts use **`@google.com`** emails (see Demo Accounts below)

### Stability Fixes (June 2026)
| Fix | Detail |
|-----|--------|
| Treasury client access | LNX uses `GET /api/treasury/pools/summary` (full `/pools` is staff-only) |
| Performance reports | Staff can generate reports for any portfolio; portfolio list URL trailing-slash fix |
| Research Lab | Global Risk Engine uses correct `timestamp` column on sentiment scores |
| Alpha evidence | Null-safe metric aggregation in evidence service |
| Intelligence Hub | Coverage-aware scores — **NO DATA** instead of synthetic 50%; `WTIUSD` symbol alignment |

## Productionization Highlights (June 2026)

| Area | What changed |
|------|----------------|
| **Demo reset** | `scripts/reset_institutional_demo.py --confirm` — purge + re-seed LNX-PRESERVE/BALANCED/ALPHA-001…003 |
| **Fund returns** | Target weekly/monthly aligned across `/funds` and `/fund-performance`; actual returns from equity curves |
| **Portfolio detail** | Total + 7D return badges; full-width risk context; settlement history panel |
| **Treasury** | Per-pool analytics (balance, contributions, withdrawals, growth) at `/treasury` |
| **Settlements** | Enriched API: starting NAV, trading PnL, target yield, treasury routed, LNX contribution |
| **Audit trail** | Categories (Trading, Treasury, Settlement, …); coalesced `EXCHANGE_RECONNECTED` events |
| **Validation** | 90D/180D/365D PDFs; Phase 4 extended metrics on dashboard |

See [docs/PHASE4_AUTONOMOUS_FUND_MANAGER.md §13](docs/PHASE4_AUTONOMOUS_FUND_MANAGER.md#13-productionization-pass-june-2026) for full detail.

## Features

### Phase 4 — Autonomous Fund Manager & Treasury
- **Lionex Funds**: Client invests in PRESERVE / BALANCE / ALPHA only; platform handles strategy, asset, and venue selection.
- **Treasury Economics**: Weekly `SettlementEngine` with solvency-capped top-ups from Yield + Reserve pools.
- **Profit Routing**: Configurable split to YIELD (40%), GROWTH (25%), RESERVE (15%), OPERATIONS (15%), LNX_INDEX (5%).
- **LNX Index**: `GET /api/lnx/index` + `/history`; daily cron; frontend chart at `/lnx`.
- **Portfolio Manager**: 60s orchestration loop (allocation → rebalance → execute → settlement on Mondays).
- **Alpha Strategies**: Momentum, trend following, vol breakout, cross-asset rotation, risk parity, sentiment overlay.
- **Strategy Optimizer**: Weekly composite scoring into `strategy_scores`.

### Core Platform
- **Secure Authentication**: JWT tokens stored in secure cookies with role-based access (`client`, `operator`, `risk_manager`, `admin`).
- **Multi-Container Architecture**: Docker Compose stack — FastAPI backend, Next.js frontend, PostgreSQL + TimescaleDB, Redis.
- **Production-Grade Local Setup**: `docker-compose.prod.yml` with uvicorn hot-reload for backend development.
- **CI/CD Pipeline**: GitHub Actions for testing, linting, security scanning, and builds.

### Portfolio & Paper Trading
- **Portfolio Management**: Manual portfolios (legacy) + auto-managed fund portfolios via invest flow.
- **Manual Paper Trading**: Simulated `BUY`/`SELL` execution with pre-trade risk validation.
- **Autonomous Execution**: 60-second cycle — legacy BTC executor or Phase 4 multi-asset manager (feature-flagged).
- **Full Trade Capture**: Every autonomous trade records `exchange`, `execution_latency_ms`, `strategy_name`, `rejection_reason`, and `trade_source`.
- **Real-time Updates**: Portfolio stats and trade lists update via WebSockets.

### Exchange Integration
- **Unified Exchange Layer**: CCXT-based adapters for Binance Spot Testnet and Bybit Demo Trading.
- **SimulatedAdapter**: Paper trading for metals, FX, and indices when not on LIVE crypto.
- **Execution Monitor**: Live exchange balances, open orders, and latency at `/execution-monitor`.
- **Execution Health**: Order throughput, fill/reject rates, and risk rejection breakdown at `/execution-health`.

### Risk Management
- **Version-Controlled Mandates**: Immutable risk contracts with automatic portfolio migration on update.
- **Pre-Trade Risk Validation**: Leverage, drawdown, margin, kill switch, AI sentiment, macro regime, gold crisis gate.
- **Stress Test Suite**: Five live validation scenarios at `/stress-test`.
- **Enhanced Audit Trail**: System-wide logs for privileged roles at `/audit`.

### Institutional Validation (Stages 1–5)
- **Rolling Snapshots**: TODAY, 7D, 14D, 30D, **90D, 180D, 365D**, and ALL — refreshed every 15 minutes.
- **Extended Metrics**: Fund performance, treasury growth, LNX growth, client yield delivery (in `chart_data.extended_metrics`).
- **Validation Dashboard**: KPI grid, cumulative PnL, rolling win rate/drawdown at `/validation`.
- **Daily Archive**: Append-only `validation_snapshot_history` with 730-day retention.
- **Institutional PDFs**: Investor-grade reports with embedded charts.

### Analytics & Explorer
- **Trade Explorer**: Paginated search at `/trade-explorer`.
- **Strategy Analytics**: Live win rate and PnL per algorithm.
- **Comparison Tools**: Side-by-side portfolio and strategy comparison at `/analytics/compare`.
- **Executive Dashboard**: Admin summary at `/executive`.

### Treasury & LNX
- **Ecosystem Treasury**: Six pools including LNX_INDEX; per-pool analytics via `GET /api/treasury/pools/analytics`.
- **Profit-Routing Ledger**: Ops view at `/treasury` + `GET /api/treasury/routing`.
- **Client Settlements**: Enriched `GET /api/portfolios/{id}/settlements` + UI panel on portfolio detail.
- **Fund Performance**: Target vs actual weekly/monthly/inception returns on `/fund-performance`.
- **Automated Yield Sweeper**: Legacy hourly sweep for non-auto-managed portfolios.

### Data Sources
- **Market prices**: Binance (crypto), yfinance (metals, energy, indices, FX), mock fallback.
- **News / intelligence**: CoinDesk RSS (hourly scraper), Investing.com FX + Commodities RSS (market intel job), demo seed articles when empty.
- **Portfolio returns**: Computed from DB equity curves and trades — **not** from news feeds. Demo data is seeded; live data requires autonomous execution.

### Strategy & Backtesting
- **Multi-Asset Backtesting**: Reads `market_bars` (daily) with fallback to legacy OHLCV.
- **Strategy Registry**: MA Crossover, RSI, plus Phase 4 alpha strategies.
- **Interactive Visualization**: TradingView Lightweight Charts.

### Reporting & Intelligence
- **Portfolio Reports**: Weekly/monthly PDF generation at `/reports` (staff access to all LNX portfolios).
- **NEXA Intelligence**: NLP on crypto, gold, FX, commodities; coverage-aware pulse at `/intelligence`; economic event scoring; `GLOBAL_RISK`.
- **Research Lab & Alpha Evidence**: Historical validation and objective Alpha 20% monthly verdict at `/research-lab` and `/alpha-evidence`.
- **Growth Simulator**: Fund-target-based projections at `/simulator`.

## Documentation

Full documentation lives in [`docs/`](docs/README.md):

| Document | Description |
|----------|-------------|
| **[docs/INSTITUTIONAL_PERFORMANCE_REPORT.md](docs/INSTITUTIONAL_PERFORMANCE_REPORT.md)** | Post-optimization validated fund results (honest metrics) |
| **[docs/ALPHA_OPTIMIZATION_PROGRAM.md](docs/ALPHA_OPTIMIZATION_PROGRAM.md)** | Alpha optimization phases 1–9 |
| **[docs/PHASE1_ALPHA_DIAGNOSTIC.md](docs/PHASE1_ALPHA_DIAGNOSTIC.md)** | Root-cause diagnostic (engines + backtests) |
| **[docs/BRAND_GUIDE.md](docs/BRAND_GUIDE.md)** | Logo-aligned colors & presentation theme |
| **[docs/HISTORICAL_VALIDATION_AUDIT.md](docs/HISTORICAL_VALIDATION_AUDIT.md)** | **Historical validation audit** — demo vs validated, fund backtest results |
| **[docs/PHASE6_INSTITUTIONAL_READINESS.md](docs/PHASE6_INSTITUTIONAL_READINESS.md)** | Phase 6 — institutional metric engine, alpha evidence |
| **[docs/PHASE5_AUDIT_REPORT.md](docs/PHASE5_AUDIT_REPORT.md)** | Phase 5 audit — demo vs live, metric integrity |
| [docs/PHASE5_ROADMAP.md](docs/PHASE5_ROADMAP.md) | Institutional readiness + Alpha evidence protocol |
| **[docs/PHASE4_AUTONOMOUS_FUND_MANAGER.md](docs/PHASE4_AUTONOMOUS_FUND_MANAGER.md)** | Phase 4 complete reference |
| [docs/PHASE4_API_QUICK_REFERENCE.md](docs/PHASE4_API_QUICK_REFERENCE.md) | Phase 4 API endpoints |
| [docs/README.md](docs/README.md) | Documentation index + platform status |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Architecture, Phase 5/6 modules, API namespaces |
| [docs/VALIDATION_ROADMAP_STATUS.md](docs/VALIDATION_ROADMAP_STATUS.md) | 5-stage roadmap completion |
| [docs/VALIDATION_REPORT.md](docs/VALIDATION_REPORT.md) | Validation framework & metrics |
| [docs/API_REFERENCE.md](docs/API_REFERENCE.md) | Complete REST endpoint catalog |
| [docs/SYSTEM_ARCHITECTURE.md](docs/SYSTEM_ARCHITECTURE.md) | High-level architecture diagrams |
| [docs/DEMO_GUIDE.md](docs/DEMO_GUIDE.md) | Persona-driven demo scripts |
| [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) | Local setup, migrations, background jobs |
| [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) | Production deployment guide |
| [docs/DATABASE.md](docs/DATABASE.md) | Schema reference |

## Tech Stack

### Backend
- **Framework**: FastAPI 0.110+ · Python 3.12
- **Database**: PostgreSQL 15 + TimescaleDB · Redis 7
- **ORM / Migrations**: SQLAlchemy 2.0 · Alembic
- **Market Data**: CCXT (Binance, Bybit) · yfinance · mock provider
- **PDF Generation**: WeasyPrint, Jinja2, matplotlib
- **Scheduling**: APScheduler (validation, settlement, LNX, market ingestion, strategy optimizer)

### Frontend
- **Framework**: Next.js 14 · TypeScript · Tailwind CSS
- **Charts**: TradingView Lightweight Charts · Recharts
- **Icons**: lucide-react

### DevOps
- Docker & Docker Compose · GitHub Actions · VPS-ready Nginx deployment

## Quick Start

### Prerequisites
- Docker & Docker Compose

### Run the Application

```bash
git clone <your-repo-url>
cd Lionexai
cp .env.example .env   # configure BINANCE/BYBIT testnet keys for autonomous trading

docker compose -f docker-compose.prod.yml up --build -d
```

**Access:**
- Frontend: `http://localhost:3000`
- API Docs: `http://localhost:8000/docs`

### Post-Setup (Phase 4)

```bash
# Apply all migrations (Phase 4–6)
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head

# Seed multi-asset universe, funds, treasury pools, market bars
docker compose -f docker-compose.prod.yml exec backend python scripts/seed_phase4.py

# Institutional demo (recommended for demos) — purges old demo data and re-seeds 9 LNX portfolios
docker compose -f docker-compose.prod.yml exec backend python scripts/reset_institutional_demo.py --confirm

# Regenerate validated reference portfolios (admin)
docker compose -f docker-compose.prod.yml exec backend python -c \
  "from app.core.database import SessionLocal; from app.validation.validated_institutional_regenerator import ValidatedInstitutionalRegenerator; db=SessionLocal(); print(ValidatedInstitutionalRegenerator(db).regenerate_all()); db.close()"

# Refresh operational demo validation snapshots (Demo Ledger mode)
docker compose -f docker-compose.prod.yml exec backend python -c \
  "from app.services.validation_service import update_validation_snapshots_job; update_validation_snapshots_job()"

# Optional: enable Phase 4 autonomous multi-asset manager (default is legacy executor)
docker compose -f docker-compose.prod.yml exec backend python scripts/seed_phase4.py --enable-autonomous
```

### Demo Accounts (password: `password123`)

| Email | Role | Seeded portfolios (after institutional reset) |
|-------|------|-----------------------------------------------|
| `client1@google.com` | client | LNX-PRESERVE-001, LNX-BALANCED-001, LNX-ALPHA-001 |
| `client2@google.com` | client | LNX-PRESERVE-002, LNX-BALANCED-002, LNX-ALPHA-002 |
| `client3@google.com` | client | LNX-PRESERVE-003, LNX-BALANCED-003, LNX-ALPHA-003 |
| `admin@google.com` | admin | Full platform access + `LNX-*-VALIDATED` reference portfolios |
| `operator1@google.com` | operator | System ops, validation, strategies |
| `risk1@google.com` | risk_manager | Treasury, validation, mandates |

After UI changes, rebuild the frontend:

```bash
docker compose -f docker-compose.prod.yml build frontend
docker compose -f docker-compose.prod.yml up -d frontend
```

## Key UI Routes

### Client (Fund-First)

| Route | Purpose |
|-------|---------|
| `/dashboard` | Fund metrics, treasury contributions, LNX index |
| `/funds` | Invest in Lionex Preserve / Balance / Alpha; **target weekly & monthly** |
| `/fund-performance` | **Validated historical** fund metrics; admin demo comparison toggle |
| `/portfolios/{id}` | Equity curve, returns, risk, settlements; **VALIDATED** portfolios show backtest-derived stats |
| `/allocation` | Live allocation engine view |
| `/lnx` | LNX index, treasury NAV, AUM, reserve ratio, history chart |
| `/intelligence` | AI pulse with coverage-aware sentiment scores |
| `/market-intelligence` | Global multi-asset intelligence dashboard |
| `/simulator` | Growth projections from fund targets |

### Operator / Risk / Admin

| Route | Purpose |
|-------|---------|
| `/research-lab` | Historical validation, global risk, alpha evidence evaluate |
| `/alpha-evidence` | Alpha 20% monthly evidence dashboard (Phase 6) |
| `/treasury` | Treasury pools + profit-routing ledger |
| `/validation` | Long-term validation — **Validated Historical** (default) or Demo Ledger toggle |
| `/trade-explorer` | Historical trade search & filters |
| `/analytics/compare` | Portfolio & strategy comparison |
| `/execution-monitor` | Live exchange status |
| `/execution-health` | Order throughput & rejections |
| `/strategies` | Strategy registry + optimizer scores |
| `/stress-test` | Risk validation scenarios |
| `/audit` | Compliance audit trail |
| `/executive` | Admin executive summary |
| `/reports` | Portfolio PDF reports |

## How to Test Phase 4

### 0. Institutional Demo (fastest path)
```bash
docker compose -f docker-compose.prod.yml exec backend python scripts/reset_institutional_demo.py --confirm
```
Log in as `client1@google.com` / `password123` → check `/fund-performance`, `/portfolios/LNX-PRESERVE-001`, `/lnx`, `/treasury` (as admin).

### 1. Fund Invest → Allocate → Execute
1. Log in as **client**, open `/funds`, invest in **ALPHA** (e.g. $50,000).
2. Open `/allocation` — confirm target weights appear.
3. Enable autonomous v2 (see Post-Setup) and wait 60–120s for execution cycle.
4. Check portfolio trades and `/audit` for autonomous events.

### 2. Weekly Settlement & Treasury
```bash
docker compose -f docker-compose.prod.yml exec backend python -c "
from app.core.database import SessionLocal
from app.services.settlement_engine import SettlementEngine
from app.engines.lnx_index import LNXIndexEngine
db = SessionLocal()
print('settlements:', SettlementEngine(db).run_weekly_settlement(force=True))
print('lnx:', LNXIndexEngine(db).compute(store=True).composite_index)
db.close()
"
```
View results at `/treasury` (routing ledger) and `/lnx`.

### 3. LNX & Market Intelligence
- `/lnx` — composite index, weekly/monthly change, historical curve
- `/market-intelligence` — asset pulse from registry, multi-region news

### 4. Validation (Extended Periods)
1. Navigate to `/validation`, select **90D**, **180D**, or **365D** tabs.
2. Review Phase 4 extended metrics (fund performance, treasury growth, client yield delivery).
3. Download PDF reports for long-horizon review.

### 5. Verify Returns Are Consistent

**Demo (seeded):** Returns on `/fund-performance` and `/portfolios/{id}` come from **equity curves in Postgres**, populated by `reset_institutional_demo.py`. They are internally consistent with seeded trades but not live market performance.

**Cross-check:**
```bash
docker compose -f docker-compose.prod.yml exec backend python -c "
from app.core.database import SessionLocal
from app.models import domain
db = SessionLocal()
p = db.query(domain.Portfolio).filter_by(id='LNX-PRESERVE-001').first()
trades = db.query(domain.Trade).filter_by(portfolio_id=p.pk_id, status='CLOSED').all()
pnl = sum(t.pnl or 0 for t in trades)
print('principal', p.principal, 'equity', p.total_equity, 'trade_pnl', pnl)
db.close()
"
```
Expect `equity ≈ principal + trade_pnl`. **Live returns** require `autonomous_v2_enabled=true` and real execution updating equity curves.

## API Overview

Interactive Swagger: `http://localhost:8000/docs` · Phase 4 quick ref: [docs/PHASE4_API_QUICK_REFERENCE.md](docs/PHASE4_API_QUICK_REFERENCE.md)

**Phase 4 — Funds & Treasury**
- `GET /api/funds/` — includes `target_*`, `actual_*`, and provenance
- `POST /api/funds/{id}/invest`
- `GET /api/portfolios/` — list portfolios (**use trailing slash**)
- `GET /api/portfolios/{id}/allocations` · `/settlements` · `/equity-curve`
- `GET /api/treasury/pools/summary` — client-safe pool balances
- `GET /api/treasury/pools/analytics` · `GET /api/treasury/routing`
- `GET /api/lnx/index` · `/history`
- `GET /api/market-intelligence/dashboard`

**Phase 5 — Validated Performance**
- `POST /api/validated/strategy/run` · `GET /api/validated/strategy/runs`
- `GET /api/validated/global-risk`
- `POST /api/validated/alpha/evidence`
- `GET /api/validated/allocation/alerts`

**Phase 6 — Institutional**
- `POST /api/institutional/alpha/evidence/full`
- `GET /api/institutional/performance/fund/{fund_id}`
- `GET /api/institutional/live-validation/snapshots`
- `GET /api/institutional/treasury/verify`
- `GET /api/institutional/lnx/attribution`
- `POST /api/institutional/reports/monthly-fund`

**Intelligence**
- `GET /api/intelligence/sentiment?limit=12` — batch pulse for Intelligence Hub
- `GET /api/intelligence/news` · `/economic-events`

**Validation**
- `GET /api/validation/snapshots?period=90D&data_source=validated` (default) or `data_source=demo`
- `GET /api/validation/report/pdf?period=30D`

**Validated funds (Research Lab / Fund Performance)**
- `GET /api/validated/fund/latest/{fund_id}?include_demo=true` — admin demo comparison block
- `POST /api/validated/optimization/run` — full alpha optimization program
- `POST /api/validated/fund/run-all` — baseline historical backtests

**Analytics & Trades**
- `GET /api/analytics/strategies` · `GET /api/trades/`

**Exchange & Execution**
- `GET /api/exchange/{binance|bybit}/status`
- `GET /api/execution/health-stats`

**WebSockets:** `/ws/market` · `/ws/portfolio` · `/ws/alerts`

## Project Structure

```
Lionexai/
├── backend/
│   ├── app/
│   │   ├── assets/                 # AssetAdapter (crypto vs simulated)
│   │   ├── analytics/performance_engine.py
│   │   ├── engines/
│   │   │   ├── allocation_engine.py
│   │   │   ├── global_risk_engine.py
│   │   │   ├── lnx_index.py
│   │   │   ├── regime_engine.py
│   │   │   └── macro_intelligence.py
│   │   ├── services/
│   │   │   ├── alpha_evidence_service.py
│   │   │   ├── live_validation_engine.py
│   │   │   ├── treasury_verification_engine.py
│   │   │   ├── lnx_attribution_engine.py
│   │   │   ├── sentiment_service.py
│   │   │   ├── portfolio_manager.py
│   │   │   ├── settlement_engine.py
│   │   │   └── validation_service.py
│   │   ├── validation/real_strategy_validation.py
│   │   ├── api/routes/
│   │   │   ├── institutional.py, validated_performance.py
│   │   │   ├── funds.py, treasury.py, lnx.py, intelligence.py
│   │   │   └── validation.py, reports.py
│   │   └── main.py
│   ├── scripts/
│   │   ├── seed_phase4.py
│   │   └── reset_institutional_demo.py
│   └── alembic/versions/
│       ├── d5f3a1b9c204_phase4_autonomous_fund_manager.py
│       ├── a1b2c3d4e5f6_p5_validated.py
│       └── b2c3d4e5f6a7_p6_institutional.py
├── frontend/src/app/
│   ├── funds/, fund-performance/, allocation/
│   ├── research-lab/, alpha-evidence/
│   ├── lnx/, treasury/, intelligence/, market-intelligence/
│   ├── dashboard/, simulator/, validation/, reports/
│   └── ...
├── docs/
│   ├── PHASE4_AUTONOMOUS_FUND_MANAGER.md
│   ├── PHASE5_ROADMAP.md, PHASE5_AUDIT_REPORT.md
│   └── PHASE6_INSTITUTIONAL_READINESS.md
├── docker-compose.prod.yml
└── README.md
```

## Database Schema

**Phase 4:** `assets`, `market_bars`, `funds`, `portfolio_allocations`, `client_settlements`, `lnx_index_snapshots`

**Phase 5:** `validated_strategy_runs`, `validated_fund_runs`, `paper_trading_validation_snapshots`, `allocation_integrity_alerts`

**Phase 6:** `live_validation_snapshots`, `treasury_verification_runs`, `lnx_attribution_snapshots`, `execution_lifecycle_events`, `institutional_reports`, `macro_data_snapshots`

**Core:** `users`, `mandates`, `portfolios`, `trades`, `strategies`, `global_settings`

**Validation:** `validation_snapshots`, `validation_snapshot_history`

**Treasury:** `treasury_pools`, `treasury_transactions`

**Intelligence:** `market_news_articles`, `nlp_sentiments`, `market_sensitivity_scores`, `economic_events`

See [docs/PHASE4_AUTONOMOUS_FUND_MANAGER.md §4](docs/PHASE4_AUTONOMOUS_FUND_MANAGER.md#4-database--migrations) and [docs/DATABASE.md](docs/DATABASE.md).

## Configuration

```env
# Infrastructure
POSTGRES_USER=nexa_admin
POSTGRES_PASSWORD=nexa_secure_pass
POSTGRES_DB=nexa_mvp
REDIS_HOST=redis

# Security
SECRET_KEY=<your-secure-key>

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000

# Exchange testnet keys (required for live crypto autonomous validation)
BINANCE_API_KEY=...
BINANCE_SECRET_KEY=...
BYBIT_API_KEY=...
BYBIT_SECRET_KEY=...
# Optional: FRED macro feeds (Phase 6 Global Risk V2)
FRED_API_KEY=...

ENVIRONMENT_STATE=PAPER
```

**Feature flags:** `global_settings.autonomous_v2_enabled` — set via seed script or `PUT /api/system/settings`.

## Troubleshooting

```bash
# Backend logs
docker compose -f docker-compose.prod.yml logs -f backend

# Health check
curl http://localhost:8000/api/system/health

# Re-run Phase 4 seed
docker compose -f docker-compose.prod.yml exec backend python scripts/seed_phase4.py

# Rebuild after code changes
docker compose -f docker-compose.prod.yml build backend frontend
docker compose -f docker-compose.prod.yml up -d
```

**Validation metrics show zeros or absurd percentages?**
- Use **`/validation`** with **Validated Historical** (default) for institutional backtests.
- For **Demo Ledger** mode, refresh snapshots: `update_validation_snapshots_job()`.
- Metrics are equity-based; legacy overflow from compounded trade returns was fixed June 2026.

**Validation metrics show zeros (demo mode only)?** Requires autonomous trades (`trade_source = AUTONOMOUS`), valid exchange keys, and active strategies — or Phase 4 auto-managed portfolios with `autonomous_v2_enabled`.

**Settlement not running?** Scheduled Mondays 01:00 UTC; force via `SettlementEngine.run_weekly_settlement(force=True)` for testing.

**Research Lab blank / 500 on global risk?** Ensure backend has latest code; Global Risk Engine orders sentiment by `timestamp`.

**Reports "portfolio not found"?** Use `GET /api/portfolios/` with trailing slash; rebuild frontend after updates.

**Intelligence scores all zero or NO DATA?** Run NLP analysis (see Post-Setup); symbols without matching news correctly show NO DATA.

**Treasury 403 on LNX?** Clients must use `/api/treasury/pools/summary`, not `/api/treasury/pools`.

```bash
# Refresh NLP sentiment
docker compose -f docker-compose.prod.yml exec backend python -c \
  "from app.services.nlp_service import run_nlp_analysis; run_nlp_analysis()"
```

## Testing

```bash
# Backend
docker compose -f docker-compose.prod.yml exec backend pytest

# Frontend typecheck
docker compose -f docker-compose.prod.yml exec frontend npx tsc --noEmit
```

## Roadmap

### Completed
- [x] **Institutional Validation** — Stages 1–5
- [x] **Phase 4** — Multi-asset, treasury, LNX, intelligence, fund-first UX, productionization
- [x] **Phase 5** — Validated historical performance, Research Lab, global risk, allocation integrity, provenance
- [x] **Phase 6** — Institutional metric engine, live validation, treasury verification, LNX attribution, alpha evidence ([docs/PHASE6_INSTITUTIONAL_READINESS.md](docs/PHASE6_INSTITUTIONAL_READINESS.md))
- [x] **Production stability pass** — Treasury client access, reports, sentiment coverage, API URL fixes

### Future
- Enable `autonomous_v2_enabled` for extended paper-live validation period
- Live trading migration (paper → live)
- On-chain LNX tokenization (Phase 2 Web3)
- ML prediction layer · Real-time alerts (email, Slack)
- Refactor operational validation Sharpe/drawdown to equity-return series throughout

## Architecture

See [docs/PHASE6_INSTITUTIONAL_READINESS.md](docs/PHASE6_INSTITUTIONAL_READINESS.md), [docs/PHASE4_AUTONOMOUS_FUND_MANAGER.md](docs/PHASE4_AUTONOMOUS_FUND_MANAGER.md), [docs/SYSTEM_ARCHITECTURE.md](docs/SYSTEM_ARCHITECTURE.md), and [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

---

**Built with ❤️ by Preyash Shah**
