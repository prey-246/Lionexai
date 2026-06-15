# NEXA Execution Architecture

## Overview

The NEXA execution layer routes autonomous strategy signals through institutional risk controls before placing paper trades on exchange testnets. All outcomes are recorded in the audit trail and reflected in portfolio state.

## Execution Pipeline

```
Strategy Signal
    ↓
Risk Engine (mandate checks)
    ↓
Exchange Adapter (Binance / Bybit)
    ↓
Testnet Order Placement
    ↓
Exchange Response (order id, fill, latency)
    ↓
Audit Log
    ↓
Portfolio Update (Trade record, equity)
```

## Exchange Abstraction Layer

**Location:** `backend/app/exchange/`

| Component | Role |
|-----------|------|
| `ExchangeAdapter` (ABC) | Unified interface for all exchanges |
| `BinanceAdapter` | Binance Spot Testnet via CCXT |
| `BybitAdapter` | Bybit Demo Trading via CCXT |
| `get_exchange_adapter()` | Factory — single entry point |

### Unified Interface

| Method | Purpose |
|--------|---------|
| `connect()` | Validate credentials and connectivity |
| `get_balance()` | Account balances |
| `get_positions()` | Open positions (empty for spot) |
| `get_order_history()` | Recent fills |
| `place_market_order()` | Market execution |
| `place_limit_order()` | Limit execution |
| `cancel_order()` | Cancel open order |
| `get_order_status()` | Single order lookup |
| `heartbeat()` | Lightweight connectivity check |
| `close()` | Release CCXT session |

## Strategy Assignment

Strategies store exchange and portfolio assignment in JSON `parameters`:

```json
{
  "assigned_portfolio_id": "PORT-1234",
  "execution_exchange": "binance",
  "strategy_type": "ma_crossover"
}
```

Assignment is performed via `PUT /api/strategies/{id}` from the Strategy Registry UI.

## Autonomous Executor

**Location:** `backend/scripts/algo_executor.py`  
**Schedule:** Every 60 seconds (background task in `main.py`)

Flow per active strategy:
1. Load assigned portfolio and exchange from parameters
2. Fetch OHLCV market data
3. Run registered strategy algorithm
4. Compare signal vs current holdings
5. Evaluate through `RiskEngine.evaluate_pre_trade()`
6. Place market order via exchange adapter
7. Write audit logs and internal trade records

## Audit Events

| Action Type | When |
|-------------|------|
| `AUTONOMOUS_TRADE_EXECUTED_BINANCE` | Successful Binance testnet order |
| `AUTONOMOUS_TRADE_EXECUTED_BYBIT` | Successful Bybit demo order |
| `ORDER_FILLED` | Order confirmed filled |
| `ORDER_REJECTED` | Risk or exchange rejection |
| `ORDER_CANCELLED` | Manual cancel via execution monitor |
| `EXCHANGE_CONNECTED` / `EXCHANGE_RECONNECTED` | Adapter connected |
| `EXCHANGE_DISCONNECTED` | Connection failure |

## API Endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /api/exchange/{id}/status` | Live exchange health + balances |
| `GET /api/exchange/{id}/heartbeat` | Connectivity ping |
| `DELETE /api/exchange/{id}/orders/{order_id}` | Cancel order |
| `GET /api/execution/health-stats` | Execution health dashboard |
| `GET /api/validation/summary` | Three-day validation metrics |
| `GET /api/validation/report/pdf` | Downloadable validation PDF |
| `POST /api/stress-test/{scenario_id}/run` | Risk validation scenarios |

## Environment Configuration

Set in `.env` / `docker-compose.prod.yml`:

```
BINANCE_API_KEY=...
BINANCE_SECRET_KEY=...
BYBIT_API_KEY=...
BYBIT_SECRET_KEY=...
ENVIRONMENT_STATE=PAPER
```

## Frontend Surfaces

| Page | Purpose |
|------|---------|
| `/execution-monitor` | Live exchange balances, orders, latency |
| `/execution-health` | Operational metrics and recent activity |
| `/validation` | Three-day validation framework |
| `/stress-test` | Institutional risk control validation |
| `/simulator` | Client-facing growth projections |
| `/strategies` | Strategy assignment to portfolio + exchange |

## Demo Data

Run once after mandates are seeded:

```bash
python scripts/seed_demo_environment.py
```

Targets: 12 portfolios, 6 strategies, 120+ trades, 280+ audit logs, 55+ risk events, 55+ news articles.
