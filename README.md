# UnifyX / NEXA MVP

A quantitative trading intelligence and portfolio orchestration platform supporting backtesting, paper trading, risk management, portfolio simulation, dashboard monitoring, audit logging, and reporting.

**Status**: MVP in development  
**Demo**: See [Setup Guide](#setup--quick-start) below

## Features

### Core Capabilities
- **Backtesting Engine**: Historical replay with multiple strategies (MA Crossover, RSI Mean Reversion, ATR)
- **Paper Trading**: Simulated execution with full risk validation
- **Risk Management**: Institutional-grade risk gatekeeper with kill switches
- **Portfolio Orchestration**: Real-time margin tracking and position management
- **Dashboards**: Client portfolio dashboard + Operations monitoring console
- **Reporting**: Weekly/monthly performance analysis with PDF export
- **Audit Trail**: Immutable logging of all critical system events
- **WebSocket Streaming**: Real-time market data and portfolio updates

### Risk Engine Validations
- Kill switch (system halt on critical breaches)
- Daily loss limits
- Weekly loss limits
- Max drawdown enforcement
- Leverage limits
- Position sizing constraints
- Asset whitelisting
- Stale data detection
- Trade frequency limits
- Stop loss validation

## Tech Stack

### Backend
- **Framework**: FastAPI 0.110+
- **Language**: Python 3.12
- **Database**: PostgreSQL 15 + TimescaleDB
- **Cache**: Redis 7
- **ORM**: SQLAlchemy 2.0
- **Migrations**: Alembic
- **Market Data**: CCXT
- **WebSockets**: python-websockets

### Frontend
- **Framework**: Next.js 15
- **Language**: TypeScript
- **Styling**: Tailwind CSS 4
- **Charts**: TradingView Lightweight Charts
- **State**: Zustand
- **Data Fetching**: React Query
- **Animations**: Framer Motion
- **Component Library**: shadcn/ui + custom

### DevOps
- **Containerization**: Docker & Docker Compose
- **CI/CD**: GitHub Actions
- **Database**: TimescaleDB for time-series
- **Deployment**: VPS-ready configuration

## Setup & Quick Start

### Prerequisites
- Docker & Docker Compose
- Node.js 20+ (for local frontend development)
- Python 3.12+ (for local backend development)
- PostgreSQL 15+ (if running without Docker)

### Option 1: Docker Compose (Recommended)

```bash
# Clone the repository
git clone <your-repo-url>
cd Lionexai

# Setup environment
cp .env.example .env  # If provided, or use existing .env

# Start all services
docker-compose up -d

# Services will be available at:
# - Frontend: http://localhost:3000
# - Backend API: http://localhost:8000
# - Database: localhost:5432
# - Redis: localhost:6379
# - API Docs: http://localhost:8000/docs
```

### Option 2: Local Development

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Frontend:**
```bash
cd frontend
pnpm install
pnpm dev  # Starts on http://localhost:3000
```

**Database (Optional - use Docker for local PostgreSQL):**
```bash
docker run -d \
  --name nexa_db \
  -e POSTGRES_USER=nexa_admin \
  -e POSTGRES_PASSWORD=nexa_secure_pass \
  -e POSTGRES_DB=nexa_mvp \
  -p 5432:5432 \
  timescale/timescaledb:latest-pg15
```

## API Documentation

### Endpoints

**Health & System**
- `GET /health` - Engine status
- `GET /api/mandates` - List risk mandates
- `GET /api/mandates/{id}` - Get mandate details

**Portfolio Management**
- `GET /api/portfolios` - List all portfolios
- `GET /api/portfolios/{id}` - Get portfolio details
- `GET /api/portfolios/{id}/stats` - Portfolio statistics
- `GET /api/portfolios/{id}/trades` - Get trades
- `GET /api/portfolios/{id}/equity-curve` - Equity curve history
- `GET /api/portfolios/{id}/risk-events` - Risk events

**Trading Execution**
- `POST /api/trading/execute` - Execute paper order (with risk validation)
- `GET /api/trading/portfolio` - Get active portfolio

**Backtesting**
- `POST /api/backtest/run` - Run strategy backtest

**Reporting**
- `POST /api/reports/generate` - Generate performance report
- `GET /api/reports/{portfolio_id}` - Get reports

**Audit & Risk**
- `GET /api/audit` - Get audit logs
- `GET /api/audit/events/risk-rejections` - Risk rejections
- `GET /api/audit/events/kill-switch` - Kill switch events

**Strategies**
- `POST /api/strategies` - Create strategy
- `GET /api/strategies` - List strategies
- `PUT /api/strategies/{id}` - Update strategy

### WebSocket Streams
- `/ws/market` - Live market data
- `/ws/portfolio` - Portfolio updates
- `/ws/alerts` - Risk alerts

**Interactive API Docs**: http://localhost:8000/docs

## Database Schema

### Core Tables
- `users` - User accounts and roles
- `mandates` - Risk parameter sets
- `portfolios` - Trading portfolios
- `trades` - Trade history
- `strategies` - Strategy definitions
- `backtest_results` - Backtest results

### Monitoring Tables
- `audit_logs` - Immutable event log
- `equity_curves` - Portfolio equity snapshots
- `risk_events` - Risk trigger events
- `reports` - Performance reports

### Migrations
```bash
# Apply migrations (automatic on startup)
cd backend
alembic upgrade head

# Create new migration
alembic revision --autogenerate -m "Add new column"
```

## Dashboard Features

### Operations Dashboard (Home `/`)
- Engine status
- Active portfolios count
- Kill switch breaches (24h)
- Database connection status
- Risk mandate parameters table

### Client Dashboard (`/dashboard`)
- Current equity
- Available margin
- Total return %
- Win rate
- Current drawdown
- Recent trades table

### Execution Terminal (`/trade`)
- Order entry form
- Asset selection (with whitelist enforcement)
- Side (BUY/SELL)
- Position sizing
- Real-time margin impact

### Strategy Engine (`/backtest`)
- Asset selection (BTC/USDT, ETH/USDT, SOL/USDT)
- Timeframe selection (1h, 4h, 1d)
- Strategy selection (currently MA Crossover)
- Performance metrics output

### Reports (`/reports`)
- Weekly/monthly report generation
- Performance metrics
- Win rate analysis
- Trade summary

### Risk Monitoring (`/risk`)
- Real-time risk events
- Risk rejection audit trail
- Kill switch event history

## Configuration

### Environment Variables (.env)

```env
# Infrastructure
ENVIRONMENT=development
PROJECT_NAME="UnifyX NEXA MVP"

# Database
POSTGRES_USER=nexa_admin
POSTGRES_PASSWORD=nexa_secure_pass
POSTGRES_DB=nexa_mvp
POSTGRES_HOST=db
POSTGRES_PORT=5432

# Redis
REDIS_HOST=redis
REDIS_PORT=6379

# Security
SECRET_KEY=<your-secure-key>
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Project Structure

```
Lionexai/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── routes/
│   │   │       ├── mandates.py
│   │   │       ├── trading.py
│   │   │       ├── backtest.py
│   │   │       ├── portfolios.py
│   │   │       ├── audit.py
│   │   │       ├── reports.py
│   │   │       ├── strategies.py
│   │   │       └── stream.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── database.py
│   │   │   └── sockets.py
│   │   ├── engines/
│   │   │   ├── backtester.py
│   │   │   └── risk_engine.py
│   │   ├── models/
│   │   │   └── domain.py
│   │   ├── services/
│   │   │   └── market_data.py
│   │   └── main.py
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx
│   │   │   ├── layout.tsx
│   │   │   ├── dashboard/
│   │   │   ├── trade/
│   │   │   ├── backtest/
│   │   │   ├── reports/
│   │   │   └── risk/
│   │   ├── components/
│   │   │   └── ui/
│   │   └── lib/
│   │       └── api.ts
│   ├── package.json
│   └── Dockerfile
├── .github/
│   └── workflows/
│       └── ci-cd.yml
├── docker-compose.yml
├── .env
└── README.md
```

## Monitoring & Observability

### Health Checks
- Backend: `GET /health` - Returns engine status and database connection
- Frontend: Accessible at http://localhost:3000
- Database: PostgreSQL healthcheck via Docker

### Logging
- Backend logs to stdout with structured format
- Risk engine logs all rejections to audit_logs table
- Kill switch events logged to audit trail

### Metrics
All performance metrics available via:
- Portfolio stats endpoint
- Backtest results
- Reports API

## Testing

### Backend Tests
```bash
cd backend
pytest                          # Run all tests
pytest --cov=app               # With coverage
pytest -v                       # Verbose output
```

### Frontend Tests
```bash
cd frontend
pnpm lint                       # ESLint
pnpm build                      # Build check
```

## Deployment

### Docker Compose (Production)
```bash
docker-compose -f docker-compose.yml up -d
```

### VPS Deployment
1. Install Docker & Docker Compose
2. Clone repository
3. Configure `.env` with production values
4. Run `docker-compose up -d`
5. Configure reverse proxy (nginx/Caddy)
6. Set up SSL/TLS certificates

### Environment-Specific Configuration
- **Development**: Use `ENVIRONMENT=development` in `.env`
- **Production**: Use `ENVIRONMENT=production` with secured values

## Troubleshooting

### Backend won't start
```bash
# Check logs
docker logs nexa_backend

# Verify database connection
docker logs nexa_db

# Rebuild container
docker-compose build --no-cache backend
```

### Frontend won't build
```bash
# Clear cache and reinstall
cd frontend
rm -rf node_modules pnpm-lock.yaml
pnpm install
pnpm build
```

### Database connection issues
```bash
# Reset database (WARNING: loses all data)
docker-compose down -v
docker-compose up -d
```

## Contributing

1. Create feature branch: `git checkout -b feature/description`
2. Commit changes: `git commit -am "Add feature description"`
3. Push to branch: `git push origin feature/description`
4. Submit pull request

## License

Proprietary - All rights reserved

## Support

For issues and questions:
1. Check existing GitHub issues
2. Review API documentation at `http://localhost:8000/docs`
3. Check logs: `docker-compose logs -f`

## Roadmap

### Phase 2
- Live trading integration (paper->live migration)
- Advanced strategy builder UI
- Machine learning prediction layer
- Real-time alerts (email, Slack, SMS)
- Mobile app

### Phase 3
- Multi-asset support (forex, commodities)
- Advanced charting with TradingView integration
- Collaborative portfolio management
- Algorithmic rebalancing
- Tax reporting

## Architecture Overview

See `docs/ARCHITECTURE.md` for detailed system design.

---

**Built with ❤️ by the UnifyX team**
