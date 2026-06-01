# API Documentation

## Base URL

```
http://localhost:8000
```

**Interactive API Docs**: http://localhost:8000/docs (Swagger UI)

## Authentication

Currently unauthenticated for MVP. Production deployment requires:
- Bearer token in `Authorization` header
- JWT token generation via login endpoint
- Session management with Redis

## Core Endpoints

### System Health

#### Get Engine Status
```
GET /health
```

**Response 200:**
```json
{
  "status": "online",
  "database": "connected"
}
```

---

### Risk Mandates

#### List All Mandates
```
GET /api/mandates
```

**Response 200:**
```json
[
  {
    "id": "PRESERVE",
    "name": "Capital Preservation",
    "max_leverage": 1.0,
    "max_drawdown_pct": 5.0,
    "daily_loss_limit_pct": 2.0,
    "allowed_assets": ["BTC/USDT", "ETH/USDT"],
    "kill_switch_active": false
  },
  {
    "id": "BALANCE",
    "name": "Balanced Growth",
    "max_leverage": 3.0,
    "max_drawdown_pct": 10.0,
    "daily_loss_limit_pct": 4.0,
    "allowed_assets": ["BTC/USDT", "ETH/USDT", "SOL/USDT"],
    "kill_switch_active": false
  }
]
```

#### Get Specific Mandate
```
GET /api/mandates/{mandate_id}
```

**Parameters:**
- `mandate_id` (path): Mandate ID (e.g., "PRESERVE")

**Response 200:**
```json
{
  "id": "PRESERVE",
  "name": "Capital Preservation",
  "max_leverage": 1.0,
  "max_drawdown_pct": 5.0,
  "daily_loss_limit_pct": 2.0,
  "allowed_assets": ["BTC/USDT", "ETH/USDT"],
  "kill_switch_active": false
}
```

---

### Portfolio Management

#### List All Portfolios
```
GET /api/portfolios
```

**Response 200:**
```json
[
  {
    "id": "port_123abc",
    "user_id": "user_456",
    "mandate_id": "BALANCE",
    "total_equity": 100000.0,
    "available_margin": 75000.0,
    "current_drawdown_pct": 2.5
  }
]
```

#### Get Portfolio Details
```
GET /api/portfolios/{portfolio_id}
```

**Parameters:**
- `portfolio_id` (path): Portfolio ID

**Response 200:**
```json
{
  "id": "port_123abc",
  "user_id": "user_456",
  "mandate_id": "BALANCE",
  "total_equity": 100000.0,
  "available_margin": 75000.0,
  "current_drawdown_pct": 2.5
}
```

#### Get Portfolio Statistics
```
GET /api/portfolios/{portfolio_id}/stats
```

**Response 200:**
```json
{
  "total_trades": 42,
  "winning_trades": 25,
  "win_rate": 59.5,
  "total_pnl": 2500.50,
  "current_equity": 102500.50,
  "available_margin": 71250.25,
  "current_drawdown_pct": 2.5
}
```

#### Get Portfolio Trades
```
GET /api/portfolios/{portfolio_id}/trades
```

**Query Parameters:**
- `status` (optional): Filter by status (OPEN, CLOSED, REJECTED)

**Response 200:**
```json
[
  {
    "id": "trade_789",
    "portfolio_id": "port_123abc",
    "symbol": "BTC/USDT",
    "side": "BUY",
    "size": 0.5,
    "entry_price": 65000.0,
    "exit_price": 66000.0,
    "status": "CLOSED",
    "pnl": 500.0,
    "created_at": "2024-06-01T10:00:00Z",
    "closed_at": "2024-06-01T11:30:00Z"
  }
]
```

#### Get Equity Curve
```
GET /api/portfolios/{portfolio_id}/equity-curve
```

**Query Parameters:**
- `limit` (optional, default: 100): Number of records

**Response 200:**
```json
[
  {
    "timestamp": "2024-06-01T09:00:00Z",
    "equity": 100000.0,
    "drawdown_pct": 0.0
  },
  {
    "timestamp": "2024-06-01T10:00:00Z",
    "equity": 101500.0,
    "drawdown_pct": 0.5
  }
]
```

#### Get Risk Events
```
GET /api/portfolios/{portfolio_id}/risk-events
```

**Query Parameters:**
- `limit` (optional, default: 50): Number of records

**Response 200:**
```json
[
  {
    "id": "event_123",
    "portfolio_id": "port_123abc",
    "event_type": "MARGIN_BREACH",
    "severity": "WARNING",
    "description": "Margin utilization exceeded 95%",
    "triggered_at": "2024-06-01T11:00:00Z",
    "resolved": false
  }
]
```

#### Update Portfolio
```
PUT /api/portfolios/{portfolio_id}
```

**Request Body:**
```json
{
  "mandate_id": "PRESERVE",
  "total_equity": 120000.0
}
```

**Response 200:** Updated portfolio object

---

### Trading Execution

#### Get Active Portfolio
```
GET /api/trading/portfolio
```

**Response 200:** Current portfolio object

#### Execute Trade
```
POST /api/trading/execute
```

**Request Body:**
```json
{
  "symbol": "BTC/USDT",
  "side": "BUY",
  "size": 1.5
}
```

**Response 200 (Accepted):**
```json
{
  "status": "FILLED",
  "trade_id": "trade_789xyz",
  "fill_price": 65123.45,
  "margin_impact": 32561.73
}
```

**Response 403 (Risk Rejection):**
```json
{
  "detail": "Leverage limit exceeded. Required margin: $32,561.73, Available: $25,000.00"
}
```

**Response 500 (Market Feed Error):**
```json
{
  "detail": "Market feed offline: [error details]"
}
```

---

### Backtesting

#### Run Backtest
```
POST /api/backtest/run
```

**Request Body:**
```json
{
  "symbol": "BTC/USDT",
  "timeframe": "1d",
  "strategy": "MA_CROSSOVER"
}
```

**Response 200:**
```json
{
  "status": "success",
  "symbol": "BTC/USDT",
  "metrics": {
    "final_capital": 112450.75,
    "total_return_pct": 12.45,
    "max_drawdown_pct": 8.25,
    "win_rate_pct": 58.3,
    "sharpe_ratio": 1.82,
    "total_trades_simulated": 47
  }
}
```

---

### Reporting

#### Generate Report
```
POST /api/reports/generate
```

**Request Body:**
```json
{
  "portfolio_id": "port_123abc",
  "report_type": "WEEKLY",
  "start_date": "2024-05-25T00:00:00Z",
  "end_date": "2024-06-01T23:59:59Z"
}
```

**Response 200:**
```json
{
  "id": "report_456",
  "portfolio_id": "port_123abc",
  "report_type": "WEEKLY",
  "period": {
    "start": "2024-05-25T00:00:00Z",
    "end": "2024-06-01T23:59:59Z"
  },
  "performance_metrics": {
    "total_return_pct": 3.25,
    "total_pnl": 3250.00,
    "winning_trades": 8,
    "losing_trades": 3,
    "win_rate": 72.7,
    "best_trade": 850.00,
    "worst_trade": -200.00,
    "avg_trade_pnl": 327.50
  },
  "risk_metrics": {
    "max_drawdown_pct": 2.5,
    "risk_events": 1
  },
  "trades_summary": {
    "total_trades": 11,
    "symbols_traded": ["BTC/USDT", "ETH/USDT"]
  }
}
```

#### List Reports
```
GET /api/reports/{portfolio_id}
```

**Query Parameters:**
- `report_type` (optional): Filter by WEEKLY or MONTHLY
- `limit` (optional, default: 10): Number of results

**Response 200:**
```json
[
  {
    "id": "report_456",
    "portfolio_id": "port_123abc",
    "report_type": "WEEKLY",
    "period_start": "2024-05-25T00:00:00Z",
    "period_end": "2024-06-01T23:59:59Z",
    "performance_metrics": {...},
    "risk_metrics": {...},
    "trades_summary": {...},
    "created_at": "2024-06-01T12:00:00Z"
  }
]
```

---

### Audit & Compliance

#### Get Audit Logs
```
GET /api/audit
```

**Query Parameters:**
- `action_type` (optional): Filter by action type
- `limit` (optional, default: 100): Number of results
- `offset` (optional, default: 0): Pagination offset

**Response 200:**
```json
{
  "total": 245,
  "limit": 100,
  "offset": 0,
  "logs": [
    {
      "id": "log_123",
      "timestamp": "2024-06-01T11:30:00Z",
      "action_type": "RISK_REJECTION",
      "description": "Leverage limit exceeded",
      "metadata_json": {
        "symbol": "BTC/USDT",
        "side": "BUY",
        "size": 5.0,
        "required_margin": 50000.00,
        "available_margin": 30000.00
      }
    }
  ]
}
```

#### Get Risk Rejections
```
GET /api/audit/events/risk-rejections
```

**Query Parameters:**
- `limit` (optional, default: 50): Number of results

**Response 200:**
```json
[
  {
    "id": "log_789",
    "timestamp": "2024-06-01T11:30:00Z",
    "action_type": "RISK_REJECTION",
    "description": "Asset not in whitelist",
    "metadata_json": {
      "symbol": "DOGE/USDT",
      "reason": "Asset not in whitelist"
    }
  }
]
```

#### Get Kill Switch Events
```
GET /api/audit/events/kill-switch
```

**Query Parameters:**
- `limit` (optional, default: 50): Number of results

**Response 200:**
```json
[
  {
    "id": "log_456",
    "timestamp": "2024-06-01T10:15:00Z",
    "action_type": "KILL_SWITCH_TRIGGERED",
    "description": "Max drawdown 10.5% >= 10.0%",
    "metadata_json": {
      "mandate_id": "BALANCE",
      "drawdown_pct": 10.5,
      "max_allowed": 10.0
    }
  }
]
```

---

### Strategies

#### Create Strategy
```
POST /api/strategies
```

**Request Body:**
```json
{
  "name": "Momentum Strategy",
  "description": "Trend-following momentum strategy",
  "strategy_type": "custom",
  "parameters": {
    "fast_ma": 10,
    "slow_ma": 50,
    "rsi_threshold": 70
  }
}
```

**Response 200:**
```json
{
  "id": "strat_123",
  "name": "Momentum Strategy",
  "description": "Trend-following momentum strategy",
  "strategy_type": "custom",
  "parameters": {
    "fast_ma": 10,
    "slow_ma": 50,
    "rsi_threshold": 70
  },
  "is_active": false,
  "created_at": "2024-06-01T12:00:00Z"
}
```

#### List Strategies
```
GET /api/strategies
```

**Query Parameters:**
- `active_only` (optional): If true, only return active strategies

**Response 200:**
```json
[
  {
    "id": "strat_123",
    "name": "Momentum Strategy",
    "description": "...",
    "strategy_type": "custom",
    "parameters": {...},
    "is_active": false,
    "created_at": "2024-06-01T12:00:00Z"
  }
]
```

#### Get Strategy Details
```
GET /api/strategies/{strategy_id}
```

**Response 200:** Strategy object

#### Update Strategy
```
PUT /api/strategies/{strategy_id}
```

**Request Body:**
```json
{
  "name": "Updated Name",
  "is_active": true,
  "parameters": {...}
}
```

**Response 200:** Updated strategy object

#### Delete Strategy
```
DELETE /api/strategies/{strategy_id}
```

**Response 200:**
```json
{
  "status": "deleted"
}
```

---

## WebSocket Endpoints

### Market Data Stream
```
ws://localhost:8000/ws/market
```

**Subscribe Message:**
```json
{
  "type": "SUBSCRIBE",
  "symbols": ["BTC/USDT", "ETH/USDT"]
}
```

**Data Messages:**
```json
{
  "type": "MARKET_TICK",
  "data": {
    "BTC/USDT": 65123.45,
    "ETH/USDT": 3512.30
  }
}
```

### Portfolio Updates Stream
```
ws://localhost:8000/ws/portfolio
```

**Update Message:**
```json
{
  "type": "PORTFOLIO_UPDATE",
  "data": {
    "portfolio_id": "port_123",
    "total_equity": 102500.0,
    "available_margin": 51250.0,
    "unrealized_pnl": 2500.0
  }
}
```

### Risk Alerts Stream
```
ws://localhost:8000/ws/alerts
```

**Alert Message:**
```json
{
  "type": "RISK_ALERT",
  "data": {
    "severity": "CRITICAL",
    "event_type": "KILL_SWITCH_TRIGGERED",
    "description": "Max drawdown exceeded",
    "triggered_at": "2024-06-01T11:00:00Z"
  }
}
```

---

## Error Responses

### 400 Bad Request
```json
{
  "detail": "Invalid request parameters"
}
```

### 403 Forbidden
```json
{
  "detail": "Risk validation failed: [specific reason]"
}
```

### 404 Not Found
```json
{
  "detail": "Resource not found"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Internal server error: [details]"
}
```

---

## Rate Limiting

Current MVP: No rate limiting  
Production: Implement via Redis with limits like:
- 100 requests/minute per IP
- 1000 trades/day per portfolio
- 10 requests/second per endpoint

---

## Pagination

List endpoints support pagination:

**Query Parameters:**
- `limit` (default: varies by endpoint)
- `offset` (default: 0)

**Response Format:**
```json
{
  "total": 500,
  "limit": 100,
  "offset": 0,
  "data": [...]
}
```

---

## Testing Endpoints

### Quick Health Check
```bash
curl -H "Authorization: Bearer <YOUR_TOKEN>" http://localhost:8000/api/health
```

### Get Mandates
```bash
curl http://localhost:8000/api/mandates
```

### Execute Trade (requires valid portfolio)
```bash
curl -X POST http://localhost:8000/api/trading/execute \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "BTC/USDT",
    "side": "BUY",
    "size": 0.1
  }'
```

### Run Backtest
```bash
curl -X POST http://localhost:8000/api/backtest/run \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "BTC/USDT",
    "timeframe": "1d",
    "strategy": "MA_CROSSOVER"
  }'
```

---

For interactive exploration, visit: **http://localhost:8000/docs**
