# Architecture Overview

## System Design

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         NEXA Platform                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────────┐         ┌──────────────────────┐      │
│  │   Frontend      │         │   Backend FastAPI    │      │
│  │  (Next.js)      │◄────────│   Risk Engine        │      │
│  │                 │         │   Backtest Engine    │      │
│  │ ┌───────────┐   │         │                      │      │
│  │ │Operations │   │         │ ┌─────────────────┐ │      │
│  │ │Dashboard  │   │         │ │  Risk Engine    │ │      │
│  │ ├───────────┤   │         │ │  - Validation   │ │      │
│  │ │Client     │   │         │ │  - Kill Switch  │ │      │
│  │ │Dashboard  │   │         │ │  - Audit Log    │ │      │
│  │ ├───────────┤   │         │ └─────────────────┘ │      │
│  │ │Execution  │   │         │ ┌─────────────────┐ │      │
│  │ │Terminal   │   │         │ │   Backtester   │ │      │
│  │ ├───────────┤   │         │ │  - MA Crossover│ │      │
│  │ │Reports    │   │         │ │  - Metrics     │ │      │
│  │ ├───────────┤   │         │ └─────────────────┘ │      │
│  │ │Risk       │   │         │ ┌─────────────────┐ │      │
│  │ │Monitoring │   │         │ │Market Data Svc │ │      │
│  │ └───────────┘   │         │ └─────────────────┘ │      │
│  └─────────────────┘         └──────────────────────┘      │
│           ▲                              ▲                  │
│           │       WebSocket/REST        │                  │
│           └──────────────────────────────┘                  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         Persistent Data Layer                        │  │
│  │  ┌──────────────┐      ┌──────────────────────────┐  │  │
│  │  │ PostgreSQL   │      │ Redis Cache              │  │  │
│  │  │ + TimescaleDB│      │ - Sessions               │  │  │
│  │  │              │      │ - Market Data Cache      │  │  │
│  │  │ - Users      │      │ - Rate Limiting          │  │  │
│  │  │ - Portfolios │      │ - Queue Management       │  │  │
│  │  │ - Trades     │      └──────────────────────────┘  │  │
│  │  │ - Mandates   │                                    │  │
│  │  │ - Audit Logs │                                    │  │
│  │  │ - Reports    │                                    │  │
│  │  │ - Strategies │                                    │  │
│  │  │ - Risk Events│                                    │  │
│  │  └──────────────┘                                    │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │          External Data Sources                       │  │
│  │  ┌──────────────────────────────────────────────┐   │  │
│  │  │ CCXT Market Data                             │   │  │
│  │  │ - Binance, OANDA Demo, MT5 Demo Abstraction│   │  │
│  │  │ - Real-time tickers                         │   │  │
│  │  │ - Historical OHLCV                          │   │  │
│  │  └──────────────────────────────────────────────┘   │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Component Architecture

### Backend Layer

#### API Routes (`app/api/routes/`)
- **mandates.py**: Risk mandate management
- **trading.py**: Trade execution with risk validation
- **backtest.py**: Strategy backtesting
- **portfolios.py**: Portfolio management and analytics
- **audit.py**: Audit log retrieval
- **reports.py**: Report generation and retrieval
- **strategies.py**: Strategy CRUD operations
- **stream.py**: WebSocket connections

#### Core Services (`app/core/`)
- **config.py**: Environment configuration and settings
- **database.py**: SQLAlchemy setup and session management
- **sockets.py**: WebSocket connection management

#### Engines (`app/engines/`)
- **risk_engine.py**: Pre-trade risk validation
  - Kill switch enforcement
  - Drawdown limits
  - Leverage constraints
  - Daily/weekly loss limits
  - Asset whitelisting
  - Position sizing
  - Trade frequency limits
  
- **backtester.py**: Historical strategy simulation
  - OHLCV data ingestion
  - Technical indicator calculation
  - Performance metrics computation

#### Services (`app/services/`)
- **market_data.py**: CCXT integration and fallback handling

#### Models (`app/models/`)
- **domain.py**: SQLAlchemy ORM models

### Frontend Layer

#### App Structure (`src/app/`)
- **page.tsx**: Operations Dashboard (home)
- **dashboard/page.tsx**: Client Portfolio Dashboard
- **trade/page.tsx**: Execution Terminal
- **backtest/page.tsx**: Strategy Engine
- **reports/page.tsx**: Performance Reports
- **risk/page.tsx**: Risk Monitoring
- **layout.tsx**: Root layout with navigation

#### Components (`src/components/ui/`)
- **NavBar.tsx**: Main navigation
- **GlassCard.tsx**: Glass-morphism card component
- **MetricDisplay.tsx**: Key metric display

#### Libraries (`src/lib/`)
- **api.ts**: Centralized API client with typed interfaces

## Data Models

### Core Entities

**User**
- id (UUID)
- email (unique)
- role_tier (retail, ops_admin, quant)
- is_active (boolean)
- created_at (timestamp)
- portfolios (relationship)

**Mandate**
- id (string, primary key for lookup)
- name (display name)
- max_leverage (float)
- max_drawdown_pct (float)
- daily_loss_limit_pct (float)
- allowed_assets (JSON array)
- kill_switch_active (boolean)

**Portfolio**
- id (UUID)
- user_id (foreign key)
- mandate_id (foreign key)
- total_equity (float)
- available_margin (float)
- current_drawdown_pct (float)

**Trade**
- id (UUID)
- portfolio_id (foreign key)
- symbol (string, indexed)
- side (BUY/SELL)
- size (float)
- entry_price (float)
- exit_price (float, nullable)
- status (OPEN/CLOSED/REJECTED)
- pnl (float, computed)
- created_at (timestamp)
- closed_at (timestamp, nullable)

**Strategy**
- id (UUID)
- name (string)
- description (string, nullable)
- strategy_type (moving_average, rsi, atr, custom)
- parameters (JSON)
- is_active (boolean)
- created_at (timestamp)

**BacktestResult**
- id (UUID)
- strategy_id (foreign key)
- start_date (timestamp)
- end_date (timestamp)
- initial_capital (float)
- final_equity (float)
- total_return_pct (float)
- cagr (float)
- sharpe_ratio (float)
- sortino_ratio (float)
- max_drawdown_pct (float)
- win_rate (float)
- profit_factor (float)
- total_trades (integer)
- winning_trades (integer)
- created_at (timestamp)
- results_json (JSON, full results)

**AuditLog**
- id (UUID)
- timestamp (timestamp, indexed)
- action_type (RISK_REJECTION, KILL_SWITCH_TRIGGERED, etc.)
- description (string)
- metadata_json (JSON)

**EquityCurve**
- id (UUID)
- portfolio_id (foreign key, indexed)
- timestamp (timestamp, indexed)
- equity (float)
- drawdown_pct (float)

**RiskEvent**
- id (UUID)
- portfolio_id (foreign key, indexed)
- event_type (string)
- severity (INFO/WARNING/CRITICAL)
- description (string)
- triggered_at (timestamp)
- resolved (boolean)
- metadata_json (JSON)

**Report**
- id (UUID)
- portfolio_id (foreign key, indexed)
- report_type (WEEKLY/MONTHLY)
- period_start (timestamp)
- period_end (timestamp)
- performance_metrics (JSON)
- risk_metrics (JSON)
- trades_summary (JSON)
- html_content (string, nullable)
- pdf_content (string, nullable)
- created_at (timestamp)

## Risk Engine Flow

```
Trade Request
    │
    ├─► Risk Engine.evaluate_pre_trade()
    │
    ├─► Check 1: Kill Switch Active?
    │   └─► REJECT if active
    │
    ├─► Check 2: Asset in Whitelist?
    │   └─► REJECT if not whitelisted
    │
    ├─► Check 3: Max Drawdown Exceeded?
    │   ├─► REJECT + TRIGGER KILL SWITCH if exceeded
    │   └─► Log to RiskEvent table
    │
    ├─► Check 4: Daily Loss Limit Breached?
    │   ├─► REJECT + TRIGGER KILL SWITCH if breached
    │   └─► Log to AuditLog table
    │
    ├─► Check 5: Position Size Within Limits?
    │   └─► REJECT if too large
    │
    ├─► Check 6: Leverage Within Mandate?
    │   └─► REJECT if exceeds max_leverage
    │
    ├─► Check 7: Stale Data?
    │   └─► REJECT if market data >5min old
    │
    ├─► Check 8: Stop Loss Attached?
    │   └─► REJECT if missing
    │
    └─► All Checks Pass?
        ├─► APPROVE Trade
        ├─► Create Trade Record (status=OPEN)
        ├─► Update Portfolio Margin
        ├─► Log to AuditLog (action=TRADE_EXECUTED)
        └─► Broadcast via WebSocket
        
REJECT
    ├─► Log to AuditLog (action=RISK_REJECTION)
    ├─► Create RiskEvent (severity=WARNING)
    ├─► Return 403 Forbidden to client
    └─► Broadcast alert via WebSocket
```

## Request/Response Flow

### Paper Trade Execution Flow

```
Client                Backend              Database
  │                     │                     │
  ├─POST /api/trading/execute─────────────────►
  │  {                  │                     │
  │   symbol: "BTC/USDT"                      │
  │   side: "BUY"       │                     │
  │   size: 1.5         │                     │
  │  }                  │                     │
  │                     ├─1. Fetch live price─►
  │                     │   via CCXT          │
  │                     │                     │
  │                     ├─2. Risk Engine─────►
  │                     │   Validation        │
  │                     │                     │
  │                     ├─3. If PASS─────────►
  │                     │   - Insert Trade    │
  │                     │   - Update Portfolio│
  │                     │   - Log AuditLog    │
  │                     │◄─── Return rowcount─┤
  │                     │                     │
  │◄────── 200 OK ──────┤                     │
  │  {                  │                     │
  │   status: "FILLED"  │                     │
  │   trade_id: "..."   │                     │
  │   fill_price: 65123 │                     │
  │  }                  │                     │
  │                     │                     │
  │                     ├─4. Broadcast via WS─►
  │                     │   (other clients)   │
  │
  ├─If RISK REJECTION──────────────────────────►
  │                     ├─Log to AuditLog     │
  │                     │  (RISK_REJECTION)   │
  │◄────── 403 ─────────┤                     │
  │  {error: "..."}     │                     │
```

## Backtesting Flow

```
Client                Backend              Database
  │                     │                     │
  ├─POST /api/backtest/run─────────────────────►
  │  {                  │                     │
  │   symbol: "BTC/USDT"│                     │
  │   timeframe: "1d"   │                     │
  │   strategy: "MA_CROSSOVER"                │
  │  }                  │                     │
  │                     │                     │
  │                     ├─1. Fetch historical─►
  │                     │   OHLCV from CCXT   │
  │                     │   (500 candles)     │
  │                     │                     │
  │                     ├─2. Execute─────────►
  │                     │   BacktestEngine    │
  │                     │   .run_strategy()   │
  │                     │                     │
  │                     │   - Calculate SMA20 │
  │                     │   - Calculate SMA50 │
  │                     │   - Generate signals│
  │                     │   - Simulate fills  │
  │                     │   - Compute metrics │
  │                     │                     │
  │                     ├─3. Optional: Save──►
  │                     │   BacktestResult    │
  │                     │                     │
  │◄──────── 200 OK ────┤                     │
  │  {                  │                     │
  │   status: "success" │                     │
  │   symbol: "BTC/..." │                     │
  │   metrics: {        │                     │
  │     total_return: 12.5                    │
  │     max_drawdown: 8.2                     │
  │     sharpe_ratio: 1.8                     │
  │     win_rate: 58.3                        │
  │     ...             │                     │
  │   }                 │                     │
  │  }                  │                     │
```

## WebSocket Channels

### Market Data Stream (`/ws/market`)
```json
{
  "type": "MARKET_TICK",
  "data": {
    "BTC/USDT": 65123.45,
    "ETH/USDT": 3512.30,
    "timestamp": "2024-06-01T10:30:00Z"
  }
}
```

### Portfolio Updates (`/ws/portfolio`)
```json
{
  "type": "PORTFOLIO_UPDATE",
  "data": {
    "portfolio_id": "port_123",
    "total_equity": 102500,
    "available_margin": 51250,
    "unrealized_pnl": 2500,
    "timestamp": "2024-06-01T10:30:00Z"
  }
}
```

### Risk Alerts (`/ws/alerts`)
```json
{
  "type": "RISK_ALERT",
  "data": {
    "severity": "CRITICAL",
    "event_type": "DRAWDOWN_LIMIT_BREACHED",
    "description": "Max drawdown 10.5% >= limit 10.0%",
    "triggered_at": "2024-06-01T10:30:00Z"
  }
}
```

## Security Architecture

### Authentication
- JWT tokens for API access
- Session management via Redis
- Rate limiting per IP

### Authorization
- Role-based access control (RBAC)
- User tiers: retail, ops_admin, quant
- Mandate-based portfolio access

### Data Protection
- All passwords hashed with bcrypt
- HTTPS in production
- SQL injection prevention via SQLAlchemy ORM
- CORS configuration for frontend

### Audit Trail
- Immutable audit logs in database
- All critical actions logged
- Timestamp and user tracking
- Risk rejections captured with context

## Scalability Considerations

### Horizontal Scaling
- Stateless API servers
- Session storage in Redis (shared)
- Database connection pooling
- Load balancer in front

### Vertical Scaling
- Connection pooling (10-20 connections)
- Caching layer (Redis)
- Index optimization for audit logs
- Time-series compression via TimescaleDB

### Performance Optimization
- Pagination on list endpoints
- Query result caching
- Database query indexing
- Frontend asset bundling

## Deployment Architecture

### Docker Services
1. **PostgreSQL + TimescaleDB** - Persistent data storage
2. **Redis** - Caching and session management
3. **FastAPI Backend** - REST API and WebSocket server
4. **Next.js Frontend** - Client application

### Network
```
Internet
   │
   ▼
Reverse Proxy (nginx/Caddy)
   │
   ├──► http://backend:8000
   │    - REST API
   │    - WebSocket
   │
   └──► http://frontend:3000
        - Next.js Server
```

### Environment Variables
- Database credentials
- Redis connection
- API secrets
- Feature flags

## Monitoring & Observability

### Application Logs
- Structured logging format
- Severity levels (INFO, WARNING, ERROR, CRITICAL)
- Correlation IDs for request tracing

### Database Monitoring
- Connection pool metrics
- Query performance
- Long-running transactions
- Disk usage

### Frontend Monitoring
- Error tracking
- Performance metrics
- User analytics (optional)

### Health Checks
- API `/health` endpoint
- Database connectivity
- Redis connectivity
- External service availability (CCXT)

---

For deployment diagrams and additional technical details, see related documentation files.
