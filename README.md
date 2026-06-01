# UnifyX / NEXA MVP

A production-grade quantitative trading intelligence and portfolio orchestration platform. It provides a full suite of tools for backtesting strategies, managing paper-trading portfolios with institutional-grade risk controls, and analyzing performance through comprehensive dashboards and exportable reports.

**Status**: MVP Complete

## Features

### Core Platform
- **Secure Authentication**: User registration and login system using JWT tokens stored in secure cookies.
- **Multi-Container Architecture**: Fully containerized using Docker for consistent development and production environments.
- **Production-Grade Local Setup**: Utilizes `gunicorn` and a dedicated production Docker Compose file for a stable and performant local environment.
- **CI/CD Pipeline**: Automated testing, linting, security scanning, and build pipeline using GitHub Actions.

### Portfolio & Paper Trading
- **Portfolio Management**: Create, view, and delete trading portfolios with customizable IDs and initial capital.
- **Paper Trading**: Simulated trade execution (`BUY`/`SELL`) against a portfolio.
- **Real-time Updates**: Portfolio statistics, equity, and trade lists update in real-time across all connected clients using WebSockets.

### Risk Management
- **Risk Mandates**: Pre-defined risk profiles (e.g., max drawdown, daily loss limits) that can be assigned to portfolios.
- **Pre-Trade Risk Validation**: The risk engine validates every trade against the portfolio's mandate before execution.
- **Kill Switch**: A mechanism to halt trading on a mandate if critical risk thresholds are breached.
- **Audit Trail**: Immutable logging of all critical system events, including trade executions and risk rejections.

### Analytics & Reporting
- **Portfolio Dashboards**: Detailed views of individual portfolio performance, including equity curves, P&L, and trade history.
- **System-Wide Summary**: A main dashboard summarizing the performance of all portfolios.
- **On-Demand Reporting**: Generate historical performance reports for any portfolio on a weekly or monthly basis.
- **PDF Export**: Download beautifully formatted PDF versions of generated performance reports for offline analysis and sharing.

### Strategy & Backtesting
- **Backtesting Engine**: A foundational engine to simulate strategy performance against historical market data.
- **Strategy Management**: API endpoints to create, list, and update trading strategies.

## Tech Stack

### Backend
- **Framework**: FastAPI 0.110+
- **Language**: Python 3.12
- **Database**: PostgreSQL 15 + TimescaleDB
- **Cache**: Redis 7
- **ORM**: SQLAlchemy 2.0
- **Migrations**: Alembic
- **Market Data**: CCXT
- **PDF Generation**: WeasyPrint & Jinja2
- **WebSockets**: python-websockets

### Frontend
- **Framework**: Next.js 15
- **Language**: TypeScript
- **Styling**: Tailwind CSS 4
- **Charts**: TradingView Lightweight Charts
- **State Management**: React Hooks (`useState`, `useEffect`)
- **Component Library**: Custom components with `lucide-react` for icons.

### DevOps
- **Containerization**: Docker & Docker Compose
- **CI/CD**: GitHub Actions
- **Database**: TimescaleDB for time-series
- **Deployment**: VPS-ready configuration

## Setup & Production-Grade Local Start

### Prerequisites
- Docker & Docker Compose

### Running the Application
```bash
# Clone the repository
git clone <your-repo-url>
cd Lionexai

# Ensure you have a .env file configured (you can copy .env.example)

# Build and start all services in production mode
docker-compose -f docker-compose.prod.yml up --build -d
```

Your application is now running and accessible:
- **Frontend**: `http://localhost:3000`
- **Backend API Docs**: `http://localhost:8000/docs`

## Feature Deep Dive & How to Test

### 1. User Authentication
- **To Test**: Navigate to `http://localhost:3000`. You will be redirected to the `/login` page. Use the link to `/register`, create a new account, and then log in. Upon successful login, you will be directed to the main dashboard.

### 2. Portfolio Creation with Custom Capital
- **To Test**: Go to the "Portfolios" page from the sidebar. Use the "Create New Portfolio" form. Enter a unique ID, select a risk mandate, and specify the "Initial Capital". Click "Create Portfolio" and it will appear in the list below.

### 3. Real-Time Updates with WebSockets
- **To Test**: Open two browser windows and navigate to the same portfolio detail page in both. In one window, execute a trade. Observe the "Recent Trades" list and portfolio stats update in the second window instantly, without needing a page refresh.

### 4. On-Demand PDF Reporting
- **To Test**: Navigate to the "Reports" page. Select a portfolio that has some closed trades. Click "Generate Weekly" or "Generate Monthly". A new report item will appear in the list. Hover over this item to reveal a download icon. Click it to download a professional PDF summary of the portfolio's performance.

### 5. Pre-Trade Risk Validation
- **To Test**: On a portfolio dashboard, attempt to execute a trade with a size that would violate the assigned risk mandate (e.g., a size far greater than the portfolio's equity). The API will reject the trade with an error message, and a "RISK_REJECTION" event will be logged in the audit trail.

## Development Journey & Key Learnings

This project involved overcoming several common but challenging real-world development hurdles.

1.  **Challenge**: A persistent redirect loop after user login.
    -   **Analysis**: We discovered a race condition between Next.js's fast client-side navigation (`router.push('/')`) and the browser setting the authentication cookie. The server-side middleware would check for the cookie before it was sent, see no user, and redirect back to login, creating a loop.
    -   **Solution**: We replaced the "soft" navigation with a "hard" page reload (`window.location.href = '/'`) after login. This forces the browser to perform a full refresh, guaranteeing that the newly set `auth_token` cookie is included in the request to the new page, which the middleware can then correctly validate.

2.  **Challenge**: The "Reports" page would crash with a `TypeError: Cannot read properties of undefined (reading 'toLocaleString')`.
    -   **Analysis**: The component was attempting to render data (e.g., `report.performance_metrics.total_pnl`) before the API call had finished or if a report had no trades and thus no performance metrics.
    -   **Solution**: We fortified the JSX by implementing **optional chaining (`?.`)** and **nullish coalescing (`??`)**. For example, `report.performance_metrics?.total_pnl?.toLocaleString() ?? '0.00'`. This makes the UI resilient by safely accessing nested properties and providing a default value if any part of the chain is `null` or `undefined`, preventing crashes.

3.  **Challenge**: Multiple errors during attempts to deploy to a PaaS (Render).
    -   **Analysis**: We encountered a series of platform-specific configuration errors in our `render.yaml` file, including `unknown type "psql"`, `field healthCheck not found`, and `field rewrites not found`. These were caused by subtle differences between the platform's Blueprint specification and our initial configuration.
    -   **Solution**: We reverted the cloud-specific changes to focus on a robust local production environment. We upgraded our `docker-compose.prod.yml` to use `gunicorn` for the backend, providing a more stable and performant setup. The key takeaway was the importance of meticulously following a specific cloud provider's Infrastructure as Code (IaC) schema and the value of a solid, production-like local environment for debugging.

## API Documentation

An interactive Swagger/OpenAPI documentation is available when the application is running.

**Interactive API Docs**: `http://localhost:8000/docs`

### Key Endpoints

... (existing endpoints) ...

**Reporting**
- `POST /api/reports/generate` - Generate performance report
- `GET /api/reports/{portfolio_id}` - Get reports for a portfolio
- `GET /api/reports/{report_id}/download` - Download a generated report as a PDF

... (existing endpoints) ...

## Project Structure

```
Lionexai/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── routes/
│   │   │       ├── auth.py
│   │   │       ├── audit.py
│   │   │       ├── backtest.py
│   │   │       ├── mandates.py
│   │   │       ├── portfolios.py
│   │   │       ├── reports.py
│   │   │       ├── strategies.py
│   │   │       └── trading.py
│   │   ├── core/
│   │   ├── engines/
│   │   ├── models/
│   │   ├── services/
│   │   ├── templates/
│   │   │   └── report.html  # PDF template
│   │   └── main.py
│   ├── alembic/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── (pages)/
│   │   ├── components/
│   │   └── lib/
│   │       ├── api.ts
│   │       └── types.ts
│   ├── package.json
│   └── Dockerfile
├── .github/
│   └── workflows/
│       └── ci-cd.yml
├── docs/
├── docker-compose.yml
├── docker-compose.prod.yml
├── .env
└── README.md
```

## Troubleshooting

### Backend won't start
```bash
# Check logs for errors
docker-compose -f docker-compose.prod.yml logs nexa_backend_prod

# Rebuild the container if code has changed significantly
docker-compose -f docker-compose.prod.yml build --no-cache backend
```

### Frontend shows API errors
```bash
# Ensure the backend is healthy
curl http://localhost:8000/api/health

# Check frontend logs
docker-compose -f docker-compose.prod.yml logs nexa_frontend_prod
```

### Database connection issues
```bash
# Reset the entire stack (WARNING: deletes all data)
docker-compose -f docker-compose.prod.yml down -v
docker-compose -f docker-compose.prod.yml up --build -d
```

... (rest of the file) ...
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
