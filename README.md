# UnifyX / NEXA MVP

A production-grade quantitative wealth management platform for backtesting strategies, managing paper-trading portfolios with institutional-grade risk controls, connecting to live exchange testnets (Binance, Bybit), and validating autonomous execution through rolling metrics, PDF reports, and analytics tooling.

**Status**: Institutional Validation Roadmap ~92% Complete · Live Paper Trading on Binance Testnet & Bybit Demo

## Features

### Core Platform
- **Secure Authentication**: JWT tokens stored in secure cookies with role-based access (`client`, `operator`, `risk_manager`, `admin`).
- **Multi-Container Architecture**: Docker Compose stack — FastAPI backend, Next.js frontend, PostgreSQL + TimescaleDB, Redis.
- **Production-Grade Local Setup**: `docker-compose.prod.yml` with uvicorn hot-reload for backend development.
- **CI/CD Pipeline**: GitHub Actions for testing, linting, security scanning, and builds.

### Portfolio & Paper Trading
- **Portfolio Management**: Create, view, and delete portfolios with customizable IDs, mandates, and initial capital.
- **Manual Paper Trading**: Simulated `BUY`/`SELL` execution with pre-trade risk validation.
- **Autonomous Execution**: 60-second algo executor runs assigned strategies through the Risk Engine to Binance/Bybit testnets.
- **Full Trade Capture**: Every autonomous trade records `exchange`, `execution_latency_ms`, `strategy_name`, `rejection_reason`, and `trade_source` (`AUTONOMOUS` / `MANUAL` / `SEED`).
- **Real-time Updates**: Portfolio stats and trade lists update via WebSockets.

### Exchange Integration
- **Unified Exchange Layer**: CCXT-based adapters for Binance Spot Testnet and Bybit Demo Trading.
- **Execution Monitor**: Live exchange balances, open orders, and latency at `/execution-monitor`.
- **Execution Health**: Order throughput, fill/reject rates, and risk rejection breakdown at `/execution-health`.

### Risk Management
- **Version-Controlled Mandates**: Immutable risk contracts with automatic portfolio migration on update.
- **Pre-Trade Risk Validation**: Leverage, drawdown, margin, kill switch, and AI sentiment gatekeeper checks.
- **Stress Test Suite**: Five live validation scenarios at `/stress-test` (leverage, AI gate, mandate/global kill switch, daily loss).
- **Enhanced Audit Trail**: System-wide logs for privileged roles with search, exchange, and date filters at `/audit`.

### Institutional Validation (Stages 1–4)
- **Rolling Snapshots**: Pre-calculated metrics for TODAY, 7D, 14D, 30D, and ALL — refreshed every 15 minutes.
- **Validation Dashboard**: KPI grid, cumulative PnL, daily returns, rolling win rate/drawdown, weekly/monthly PnL at `/validation`.
- **Scope**: Metrics computed from autonomous paper trades only (`trade_source = AUTONOMOUS`).
- **Daily Archive**: Append-only `validation_snapshot_history` with 730-day retention and metric time-series API.
- **Institutional PDFs**: 11-section investor-grade reports with embedded matplotlib charts (weekly, monthly, parametric periods).

### Analytics & Explorer (Stage 5)
- **Trade Explorer**: Paginated search with filters for portfolio, symbol, strategy, exchange, status, and date range at `/trade-explorer`.
- **Strategy Analytics**: Live win rate and PnL per algorithm on `/strategies` and via `GET /api/analytics/strategies`.
- **Comparison Tools**: Side-by-side portfolio and strategy comparison at `/analytics/compare`.
- **Executive Dashboard**: Admin summary at `/executive`.

### Treasury & Yield
- **Ecosystem Treasury**: Macro-capital pools (Reserve, Yield, Growth).
- **LNX Digital Asset**: Internal ecosystem index derived from treasury accounting.
- **Automated Yield Sweeper**: Background sweep of winning trade PnL into the Yield pool.

### Strategy & Backtesting
- **Vectorized Backtesting**: MA Crossover and RSI Mean Reversion against TimescaleDB OHLCV data.
- **Strategy Registry**: Save, assign to portfolios, and route to Binance or Bybit for autonomous execution.
- **Interactive Visualization**: TradingView Lightweight Charts with trade logs.

### Reporting & Intelligence
- **Portfolio Reports**: Weekly/monthly PDF generation per portfolio at `/reports`.
- **NEXA Intelligence**: NLP sentiment analysis on scraped crypto news with AI risk gatekeeper integration.
- **Growth Simulator**: Client-facing projection PDF at `/simulator`.

## Documentation

Full documentation lives in [`docs/`](docs/README.md):

| Document | Description |
|----------|-------------|
| [docs/README.md](docs/README.md) | Documentation index |
| [docs/VALIDATION_ROADMAP_STATUS.md](docs/VALIDATION_ROADMAP_STATUS.md) | 5-stage roadmap completion (~92%) |
| [docs/VALIDATION_REPORT.md](docs/VALIDATION_REPORT.md) | Validation framework & metrics |
| [docs/API_REFERENCE.md](docs/API_REFERENCE.md) | Complete REST endpoint catalog |
| [docs/SYSTEM_ARCHITECTURE.md](docs/SYSTEM_ARCHITECTURE.md) | High-level architecture diagrams |
| [docs/DEMO_GUIDE.md](docs/DEMO_GUIDE.md) | Persona-driven demo scripts (A–D) |
| [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) | Local setup, migrations, background jobs |
| [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) | Production deployment guide |

## Tech Stack

### Backend
- **Framework**: FastAPI 0.110+ · Python 3.12
- **Database**: PostgreSQL 15 + TimescaleDB · Redis 7
- **ORM / Migrations**: SQLAlchemy 2.0 · Alembic
- **Market Data / Exchanges**: CCXT (Binance, Bybit)
- **PDF Generation**: WeasyPrint, Jinja2, matplotlib (validation chart embedding)
- **Scheduling**: APScheduler (validation snapshots, news, NLP, yield sweep)

### Frontend
- **Framework**: Next.js 15 · TypeScript · Tailwind CSS 4
- **Charts**: TradingView Lightweight Charts · Recharts (validation dashboard)
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

### Post-Setup (Recommended)

```bash
# Apply migrations (validation tables + extended trade fields)
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head

# Seed demo data
docker compose -f docker-compose.prod.yml exec backend python scripts/seed_demo_environment.py

# Refresh validation snapshots
docker compose -f docker-compose.prod.yml exec backend python -c \
  "from app.services.validation_service import update_validation_snapshots_job; update_validation_snapshots_job()"
```

After UI changes, rebuild the frontend:

```bash
docker compose -f docker-compose.prod.yml build frontend
docker compose -f docker-compose.prod.yml up -d frontend
```

## Key UI Routes

| Route | Purpose |
|-------|---------|
| `/validation` | Institutional validation dashboard |
| `/trade-explorer` | Historical trade search & filters |
| `/analytics/compare` | Portfolio & strategy comparison |
| `/execution-monitor` | Live exchange status (Binance/Bybit) |
| `/execution-health` | Order throughput & rejections |
| `/strategies` | Strategy registry + live performance |
| `/stress-test` | Risk validation scenarios |
| `/audit` | Enhanced compliance audit trail |
| `/executive` | Admin executive summary |
| `/reports` | Portfolio PDF reports |
| `/simulator` | Client growth projections |

## How to Test

### 1. Authentication
Register at `/register`, log in, and confirm redirect to the dashboard.

### 2. Autonomous Paper Trading
1. Assign a strategy to a portfolio with `execution_exchange: binance` (or `bybit`).
2. Set `is_active: true` on the strategy.
3. Wait 60–120 seconds for the algo executor cycle.
4. Check `/execution-monitor` and `/audit` for `AUTONOMOUS_TRADE_EXECUTED_*` events.

### 3. Institutional Validation
1. Navigate to `/validation` and switch period tabs (Today → 30D → All Time).
2. Download a PDF via the report buttons.
3. After multiple days of operation, historical win rate/drawdown charts populate from the daily archive.

### 4. Trade Explorer & Analytics
1. Open `/trade-explorer` — filter by `trade_source`, exchange, or strategy.
2. Open `/analytics/compare` — select 2+ portfolios or strategies for side-by-side view.
3. Open `/strategies` — review live performance table.

### 5. Risk Validation
Run all five scenarios at `/stress-test`. Each should return REJECTED with an audit log entry.

## API Overview

Interactive Swagger: `http://localhost:8000/docs` · Full catalog: [docs/API_REFERENCE.md](docs/API_REFERENCE.md)

**Validation**
- `GET /api/validation/snapshots` — Rolling metrics (TODAY / 7D / 14D / 30D / ALL)
- `GET /api/validation/history` — Daily snapshot archive
- `GET /api/validation/history/metrics` — Metric time-series
- `GET /api/validation/report/pdf?period=30D` — Institutional PDF

**Analytics & Trades**
- `GET /api/analytics/strategies` — Live strategy performance
- `GET /api/analytics/portfolios/compare?ids=...` — Portfolio comparison
- `GET /api/trades/` — Trade explorer with filters

**Exchange & Execution**
- `GET /api/exchange/{binance|bybit}/status` — Exchange health
- `GET /api/execution/health-stats` — Execution dashboard data

**Core**
- `POST /api/trading/{portfolio_id}/execute` — Manual paper trade
- `POST /api/backtest/run` — Run backtest
- `GET /api/audit/` — Audit trail (enhanced filters for privileged roles)

**WebSockets:** `/ws/market` · `/ws/portfolio` · `/ws/alerts`

## Project Structure

```
Lionexai/
├── backend/
│   ├── app/
│   │   ├── api/routes/
│   │   │   ├── validation.py      # Snapshots, history, PDF reports
│   │   │   ├── analytics.py       # Strategy/portfolio compare
│   │   │   ├── trades.py          # Trade explorer
│   │   │   ├── exchange.py        # Binance/Bybit adapters
│   │   │   ├── execution_health.py
│   │   │   └── ...
│   │   ├── exchange/              # CCXT adapter layer
│   │   ├── services/
│   │   │   ├── validation_service.py
│   │   │   ├── validation_report_service.py
│   │   │   ├── chart_image_service.py
│   │   │   └── analytics_service.py
│   │   ├── templates/
│   │   │   ├── validation_report.html
│   │   │   └── report.html
│   │   └── main.py
│   ├── scripts/algo_executor.py
│   └── alembic/versions/
├── frontend/src/app/
│   ├── validation/
│   ├── trade-explorer/
│   ├── analytics/compare/
│   ├── execution-monitor/
│   ├── execution-health/
│   ├── stress-test/
│   └── ...
├── docs/                          # Full platform documentation
├── docker-compose.prod.yml
└── README.md
```

## Database Schema

**Core:** `users`, `mandates`, `portfolios`, `trades`, `strategies`, `global_settings`, `backtest_results`

**Validation:** `validation_snapshots` (live rolling cache), `validation_snapshot_history` (daily archive, 730-day retention)

**Monitoring:** `audit_logs`, `equity_curves`, `risk_events`, `reports`, `market_news_articles`, `nlp_sentiments`, `market_sensitivity_scores`, `market_data_ohlcv`

**Trade extensions** (migration `b7c3e1a42f90`, `4a92414eca12`): `exchange`, `execution_latency_ms`, `strategy_name`, `rejection_reason`, `trade_source`. Snapshot tables now have first-class columns for all metadata.

See [docs/DATABASE.md](docs/DATABASE.md) for full schema.

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

# Exchange testnet keys (required for autonomous validation metrics)
BINANCE_API_KEY=...
BINANCE_SECRET_KEY=...
BYBIT_API_KEY=...
BYBIT_SECRET_KEY=...
ENVIRONMENT_STATE=PAPER
```

## Troubleshooting

```bash
# Backend logs
docker compose -f docker-compose.prod.yml logs -f nexa_backend_prod

# Health check
curl http://localhost:8000/api/system/health

# Rebuild after code changes
docker compose -f docker-compose.prod.yml build backend frontend
docker compose -f docker-compose.prod.yml up -d

# Reset stack (WARNING: deletes all data)
docker compose -f docker-compose.prod.yml down -v
docker compose -f docker-compose.prod.yml up --build -d
```

**Validation metrics show zeros?** Autonomous validation requires valid exchange API keys, an active strategy assigned to a portfolio with `execution_exchange` set, and at least one algo executor cycle (~60s). Seed/manual trades are excluded from validation by design.

## Testing

```bash
# Backend
docker compose -f docker-compose.prod.yml exec backend pytest

# Frontend
docker compose -f docker-compose.prod.yml exec frontend pnpm lint
docker compose -f docker-compose.prod.yml exec frontend pnpm build
```

## Roadmap

### Completed (Institutional Validation)
- [x] **Stage 1** — Trade capture + rolling validation stats
- [x] **Stage 2** — Validation dashboard (periods, charts, KPIs)
- [x] **Stage 3** — Institutional PDF reports with embedded charts
- [x] **Stage 4** — Continuous engine + daily snapshot archive
- [x] **Stage 5** — Trade explorer, analytics compare, enhanced audit

### Remaining Polish (~5%)
- UI for on-demand date range reports in `/reports`
- Backtest results on strategies page UI
- Risk events on portfolio detail page

### Future Phases
- Live trading migration (paper → live)
- Advanced strategy builder UI
- ML prediction layer
- Real-time alerts (email, Slack)
- Multi-asset support (forex, commodities)

## Architecture

See [docs/SYSTEM_ARCHITECTURE.md](docs/SYSTEM_ARCHITECTURE.md) and [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed system design, execution flows, and validation pipeline.

---

**Built with ❤️ by Preyash Shah**
