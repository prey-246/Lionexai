# LionexAI

Autonomous multi-asset fund management platform with institutional treasury economics, validated historical performance, market intelligence, and role-based client/admin separation.

**Stack:** Next.js · FastAPI · PostgreSQL/TimescaleDB · Redis · Docker

---

## Project Overview

### What it is

LionexAI is a quantitative wealth platform where clients invest in **AI-managed fund products** (Preserve, Balance, Alpha). The platform autonomously allocates across crypto, metals, FX, indices, and energy; manages risk via mandates and regime-aware engines; routes excess profit to institutional treasury pools; and validates strategy performance on historical market data separately from the operational demo ledger.

### Problem it solves

- Fragmented manual trading across asset classes
- Lack of transparent fund-level yield targets and settlement accounting
- Mixing backtest results with live/demo ledger (addressed via **data provenance**)
- Need for institutional validation, treasury solvency checks, and audit trails

### Vision

A production-grade autonomous fund manager with honest validated metrics, operational treasury integrity, and clear separation between historical evidence and live paper trading.

---

## Platform Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Next.js Frontend (role-based UI, WebSocket market ticks)   │
└───────────────────────────┬─────────────────────────────────┘
                            │ REST + WS
┌───────────────────────────▼─────────────────────────────────┐
│  FastAPI Backend                                            │
│  ├── API Routes (funds, portfolios, validation, treasury)   │
│  ├── Engines (allocation, regime, macro, risk, LNX)         │
│  ├── Services (settlement, validation, NLP, market data)    │
│  └── Schedulers + async loops (ingestion, NLP, algo 60s)    │
└───────────┬─────────────────────────────┬───────────────────┘
            │                             │
   ┌────────▼────────┐           ┌────────▼────────┐
   │ PostgreSQL +    │           │ Redis           │
   │ TimescaleDB     │           │ cache / pubsub  │
   └────────┬────────┘           └─────────────────┘
            │
   ┌────────▼────────────────────────────────────────┐
   │ External: Binance, yfinance, RSS, FRED (optional)│
   └──────────────────────────────────────────────────┘
```

| Layer | Docs |
|-------|------|
| System overview | [docs/architecture/system_architecture.md](docs/architecture/system_architecture.md) |
| Backend | [docs/architecture/backend.md](docs/architecture/backend.md) |
| Frontend | [docs/architecture/frontend.md](docs/architecture/frontend.md) |
| Database | [docs/architecture/database.md](docs/architecture/database.md) |
| AI pipeline | [docs/architecture/ai_pipeline.md](docs/architecture/ai_pipeline.md) |

---

## Core Features

| Feature | Description |
|---------|-------------|
| **AI-managed funds** | PRESERVE / BALANCE / ALPHA with weekly yield targets |
| **Portfolio management** | Auto-managed client portfolios + validated reference portfolios |
| **Treasury routing** | Weekly settlement, profit pools, solvency verification |
| **Validation framework** | Validated historical + demo ledger toggles |
| **Market intelligence** | News, NLP sentiment, economic events, global risk widget |
| **Risk engine** | Macro score (hourly) + Global Risk v2 (explainable) |
| **Research Lab** | Strategy backtests, walk-forward, Monte Carlo |
| **Alpha evidence** | Objective verdict on monthly return targets |
| **Institutional reporting** | PDF validation reports, live validation snapshots |
| **LNX ecosystem** | Composite index, treasury NAV, attribution |
| **Growth simulator** | Forward projections from fund target rates |
| **Autonomous execution** | Multi-asset algo cycle (feature-flagged) |
| **Role separation** | Client / operator / risk_manager / admin workspaces |

Platform details: [docs/platform/](docs/platform/)

---

## Technology Stack

| Area | Technology |
|------|------------|
| Frontend | Next.js 14, React, TypeScript, Tailwind CSS, lightweight-charts |
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.0, APScheduler |
| Database | PostgreSQL 15, TimescaleDB, Alembic migrations |
| Cache | Redis 7 |
| Auth | JWT (Bearer), bcrypt passwords, cookie storage |
| Deployment | Docker Compose, Nginx (production) |
| ORM | SQLAlchemy 2.0 mapped models |
| Charts | lightweight-charts, matplotlib (PDF reports) |
| Scheduling | APScheduler + asyncio background loops |

---

## Data Sources

| Asset class | Provider | Storage |
|-------------|----------|---------|
| Crypto | Binance (testnet/live), mock | `market_bars` |
| Metals, FX, indices, energy | yfinance | `market_bars` |
| News | RSS (CoinDesk, Investing.com) | `market_news_articles` |
| Sentiment | Heuristic NLP | `market_sensitivity_scores` |
| Macro | FRED (optional `FRED_API_KEY`) | `macro_data_snapshots` |
| Validation | Historical OHLCV backtests | `validated_fund_runs`, `validated_strategy_runs` |
| Operational | Demo seed + autonomous trades | `trades`, `equity_curves`, `client_settlements` |

---

## AI Decision Pipeline

```
Market Intelligence → Risk Engine → Regime Detection → Asset Ranking
        → Allocation Engine → Rebalancing → Execution
        → Settlement → Treasury Routing → LNX Index → Validation Layer
```

Full diagram: [docs/architecture/ai_pipeline.md](docs/architecture/ai_pipeline.md)

---

## Data Provenance

| Label | Use |
|-------|-----|
| `VALIDATED_HISTORICAL` | Fund/strategy backtests on real bars |
| `DEMO` | Seeded operational paper ledger |
| `PAPER_LIVE` | Autonomous non-simulated trades |
| `OPERATIONAL_LEDGER` | Treasury pools and settlements |

`/fund-performance` and `/validation` default to validated mode. Admin toggles expose demo comparison.

---

## Project Structure

```
Lionexai/
├── backend/
│   ├── app/
│   │   ├── api/routes/      # REST endpoints
│   │   ├── engines/         # Allocation, regime, risk, LNX
│   │   ├── services/        # Settlement, validation, treasury
│   │   ├── models/          # SQLAlchemy domain
│   │   └── validation/      # Historical simulators
│   ├── alembic/             # Migrations
│   └── scripts/             # Seed, reset, optimization
├── frontend/
│   └── src/app/             # Next.js routes
├── docs/
│   ├── architecture/
│   ├── platform/
│   ├── deployment/
│   ├── api/
│   ├── guides/
│   └── archive/             # Historical phase docs
├── docker-compose.yml
└── docker-compose.prod.yml
```

---

## Running Locally

### Prerequisites

Docker and Docker Compose.

### Quick start

```bash
git clone <repository-url>
cd Lionexai
cp .env.example .env
docker compose up --build -d
docker compose exec backend alembic upgrade head
docker compose exec backend python scripts/seed_phase4.py
docker compose exec backend python scripts/reset_institutional_demo.py --confirm
```

| URL | Service |
|-----|---------|
| http://localhost:3000 | Frontend |
| http://localhost:8000/docs | API (Swagger) |

### Demo accounts

Password: **`password123`**

| Email | Role |
|-------|------|
| `admin@google.com` | admin |
| `client1@google.com` | client |
| `operator1@google.com` | operator |
| `risk1@google.com` | risk_manager |

Full guide: [docs/guides/developer_setup.md](docs/guides/developer_setup.md)

---

## Production Deployment

```bash
docker compose -f docker-compose.prod.yml up --build -d
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head
```

Nginx + TLS setup: [docs/deployment/deployment.md](docs/deployment/deployment.md)  
Docker reference: [docs/deployment/docker.md](docs/deployment/docker.md)

---

## Documentation

| Document | Description |
|----------|-------------|
| [docs/README.md](docs/README.md) | Documentation index |
| [Platform Pages Guide](docs/guides/platform_pages.md) | Every UI page, metrics, data sources |
| [API Reference](docs/api/api_reference.md) | REST endpoints |
| [Demo Guide](docs/guides/demo_guide.md) | Persona demo scripts |
| [Brand Guide](docs/guides/brand_guide.md) | Colors for slides/UI |
| [Contribution](docs/guides/contribution.md) | Contributor guidelines |
| [Archive](docs/archive/) | Historical phase reports |

---

## License

Proprietary — Ewealthtech / LionexAI.
