# NEXA Platform Architecture

This document provides an overview of the system architecture, database relationships, and core execution flows within the NEXA platform.

## System Overview

NEXA operates on a decoupled client-server architecture utilizing **FastAPI** (Python) for the backend and **Next.js** (TypeScript/React) for the frontend, communicating via REST and WebSockets.

### Container Layout
1. **nexa_backend_prod**: Gunicorn ASGI server running FastAPI. Handles all execution, risk logic, and AI scheduled tasks.
2. **nexa_frontend_prod**: Next.js production server. Handles SSR and client-side rendering.
3. **nexa_db_prod**: PostgreSQL + TimescaleDB. Handles relational data and time-series tick data.
4. **nexa_redis_prod**: Redis 7. Handles cache and high-speed pub/sub for WebSocket broadcasting.

---

## Database Schema (Domain Models)

The platform utilizes SQLAlchemy 2.0. The schema is highly relational, relying on integer Primary Keys (`pk_id`) for foreign-key mapping to ensure high performance, while exposing string `id`s (e.g., `PORT-1234`) to the frontend for security and readability.

### 1. Identity & Governance
- **User**: Contains authentication data and `role_tier` (`admin`, `operator`, `risk_manager`, `client`).
- **Mandate**: Version-controlled risk parameters (`max_leverage`, `max_drawdown_pct`, `daily_loss_limit_pct`). Linked to Portfolios.
- **GlobalSettings**: Stores singleton configuration data applied platform-wide (e.g., global kill switch, AI bearish threshold, environment state, default backtest variables).

### 2. Execution & Accounting
- **Portfolio**: Represents an isolated trading account. Tracks `total_equity` and `available_margin`.
- **Trade**: Represents individual paper trades. Tracks entry/exit prices, sizing, and realized `pnl`.
- **EquityCurve**: Time-series snapshots of portfolio equity, used for charting.
- **Strategy**: JSON-parameterized algorithmic models (e.g., MA Crossover, RSI) saved to the registry.

### 3. Macro-Financials (Treasury & Yield)
- **TreasuryPool**: Macro-capital accounts (Reserve, Yield, Growth) dictating overall platform health.
- **TreasuryTransaction**: Immutable ledger logging all capital transfers and yield sweeps.

### 4. NEXA Intelligence (Alt-Data Layer)
- **MarketNewsArticle**: Scraped news articles from external sources (e.g., CoinDesk).
- **NLPSentiment**: The result of text analysis on a news article. Tracks `sentiment_score` (-1.0 to 1.0) and `sentiment_label` (Bullish/Bearish).
- **MarketSensitivityScore**: Aggregated AI score for a specific asset (e.g., `BTC/USDT`), heavily utilized by the Risk Gatekeeper.

---

## Core Execution Flows

### 1. Trade Execution & Risk Validation
When a user submits a trade via the Terminal:
1. The request hits `POST /api/trading/{portfolio_id}/execute`.
2. The **Risk Engine** (`risk_engine.py`) is instantiated. It evaluates the trade against:
   - **Kill Switch**: Is the `global_kill_switch_active` flag set in `GlobalSettings`, or is the specific mandate halted?
   - **Leverage/Margin**: Does the trade exceed available margin or mandate leverage limits?
   - **Drawdown Limits**: Has the portfolio breached its daily or maximum drawdown ceilings?
   - **Market Sentiment**: If it's a `BUY` order, is the AI `MarketSensitivityScore` extremely bearish (<= -0.5)?
3. If rejected, an `AuditLog` is created, a `RiskEvent` is saved, and a 403 Forbidden is returned.
4. If approved, the trade executes, margin is adjusted, an `EquityCurve` point is injected, and WebSockets broadcast the update to the UI.

### 2. Role-Based Access Control (RBAC)
- **Backend Protection**: API endpoints utilize `Dependencies` (e.g., `Depends(require_role(["admin"]))`) which parse the JWT token and validate the user's role against the required array.
- **Frontend Protection**: The Next.js `middleware.ts` runs on the edge. It reads the `user_role` cookie and redirects users to their specific workspaces (`/dashboard` for clients, `/` for operators, `/risk` for risk managers) before a page can render.

### 3. Historical Backtesting
The backtesting engine operates via a highly optimized vectorized approach:
1. Uses `pandas.read_sql` to pull historical OHLCV data directly from the local PostgreSQL instance.
2. Calculates entry/exit signals across the entire timeframe instantly using array mathematics.
3. Accurately deducts simulated `commission_pct` and `slippage_pct` costs (fetching defaults from `GlobalSettings` if not provided) on every position change to generate realistic `net_return_pct` metrics.

### 4. Autonomous Paper Trading
The `algo_executor.py` background task awakens every 60 seconds. It scans the `Strategy Registry` for algorithms assigned to active `Portfolios`. It executes the mathematical models against the live market state. If a signal triggers, it routes the trade directly through the **Risk Engine**. If the Risk Engine approves, the paper trade executes entirely autonomously without human intervention.

### 5. Background Scheduled Tasks
FastAPI's `asyncio` loop manages continuous background services:
- **Market Data Streamer**: Replays historical database ticks to the frontend WebSockets, injecting micro-volatility to simulate live markets.
- **Price Updater**: Fetches live hourly closing prices from CCXT to ensure the execution terminal prices are accurate.
- **News Scraper**: Pulls RSS feeds from crypto news outlets every hour.
- **NLP Analyzer**: Scans unprocessed news articles every 10 minutes, generates sentiment scores, and updates the global `MarketSensitivityScore`.nexa_backend_prod   |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
- **Yield Sweeper**: Automatically calculates total platform realized PnL and executes a 10% ledger sweep to the Treasury Yield Pool.
- **Algo Executor**: Evaluates assigned quantitative strategies and executes autonomous paper trades.
nexa_backend_prod   |   File "/usr/local/lib/python3.12/site-packages/fastapi/applications.py", line 1159, in __call__
nexa_backend_prod   |     await super().__call__(scope, receive, send)
nexa_backend_prod   |   File "/usr/local/lib/python3.12/site-packages/starlette/applications.py", line 90, in __call__
nexa_backend_prod   |     await self.middleware_stack(scope, receive, send)
nexa_backend_prod   |   File "/usr/local/lib/python3.12/site-packages/starlette/middleware/errors.py", line 186, in __call__
nexa_backend_prod   |     raise exc
nexa_backend_prod   |   File "/usr/local/lib/python3.12/site-packages/starlette/middleware/errors.py", line 164, in __call__
nexa_backend_prod   |     await self.app(scope, receive, _send)
nexa_backend_prod   |   File "/usr/local/lib/python3.12/site-packages/starlette/middleware/cors.py", line 96, in __call__
nexa_backend_prod   |     await self.simple_response(scope, receive, send, request_headers=headers)
nexa_backend_prod   |   File "/usr/local/lib/python3.12/site-packages/starlette/middleware/cors.py", line 154, in simple_response
nexa_backend_prod   |     await self.app(scope, receive, send)
nexa_backend_prod   |   File "/usr/local/lib/python3.12/site-packages/starlette/middleware/exceptions.py", line 63, in __call__
nexa_backend_prod   |     await wrap_app_handling_exceptions(self.app, conn)(scope, receive, send)
nexa_backend_prod   |   File "/usr/local/lib/python3.12/site-packages/starlette/_exception_handler.py", line 53, in wrapped_app
nexa_backend_prod   |     raise exc
nexa_backend_prod   |   File "/usr/local/lib/python3.12/site-packages/starlette/_exception_handler.py", line 42, in wrapped_app
nexa_backend_prod   |     await app(scope, receive, sender)
nexa_backend_prod   |   File "/usr/local/lib/python3.12/site-packages/fastapi/middleware/asyncexitstack.py", line 18, in __call__
nexa_backend_prod   |     await self.app(scope, receive, send)
nexa_backend_prod   |   File "/usr/local/lib/python3.12/site-packages/starlette/routing.py", line 660, in __call__
nexa_backend_prod   |     await self.middleware_stack(scope, receive, send)
nexa_backend_prod   |   File "/usr/local/lib/python3.12/site-packages/starlette/routing.py", line 680, in app
nexa_backend_prod   |     await route.handle(scope, receive, send)
nexa_backend_prod   |   File "/usr/local/lib/python3.12/site-packages/starlette/routing.py", line 276, in handle
nexa_backend_prod   |     await self.app(scope, receive, send)
nexa_backend_prod   |   File "/usr/local/lib/python3.12/site-packages/fastapi/routing.py", line 134, in app
nexa_backend_prod   |     await wrap_app_handling_exceptions(app, request)(scope, receive, send)
nexa_backend_prod   |   File "/usr/local/lib/python3.12/site-packages/starlette/_exception_handler.py", line 53, in wrapped_app
nexa_backend_prod   |     raise exc
nexa_backend_prod   |   File "/usr/local/lib/python3.12/site-packages/starlette/_exception_handler.py", line 42, in wrapped_app
nexa_backend_prod   |     await app(scope, receive, sender)
nexa_backend_prod   |   File "/usr/local/lib/python3.12/site-packages/fastapi/routing.py", line 120, in app
nexa_backend_prod   |     response = await f(request)
nexa_backend_prod   |                ^^^^^^^^^^^^^^^^
nexa_backend_prod   |   File "/usr/local/lib/python3.12/site-packages/fastapi/routing.py", line 674, in app
nexa_backend_prod   |     raw_response = await run_endpoint_function(
nexa_backend_prod   |                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
nexa_backend_prod   |   File "/usr/local/lib/python3.12/site-packages/fastapi/routing.py", line 330, in run_endpoint_function
nexa_backend_prod   |     return await run_in_threadpool(dependant.call, **values)
nexa_backend_prod   |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
nexa_backend_prod   |   File "/usr/local/lib/python3.12/site-packages/starlette/concurrency.py", line 32, in run_in_threadpool
nexa_backend_prod   |     return await anyio.to_thread.run_sync(func)
nexa_backend_prod   |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
nexa_backend_prod   |   File "/usr/local/lib/python3.12/site-packages/anyio/to_thread.py", line 63, in run_sync
nexa_backend_prod   |     return await get_async_backend().run_sync_in_worker_thread(
nexa_backend_prod   |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
nexa_backend_prod   |   File "/usr/local/lib/python3.12/site-packages/anyio/_backends/_asyncio.py", line 2518, in run_sync_in_worker_thread
nexa_backend_prod   |     return await future
nexa_backend_prod   |            ^^^^^^^^^^^^
nexa_backend_prod   |   File "/usr/local/lib/python3.12/site-packages/anyio/_backends/_asyncio.py", line 1002, in run
nexa_backend_prod   |     result = context.run(func, *args)
nexa_backend_prod   |              ^^^^^^^^^^^^^^^^^^^^^^^^
nexa_backend_prod   |   File "/code/app/api/routes/mandates.py", line 151, in update_mandate
nexa_backend_prod   |     new_mandate = domain.Mandate(
nexa_backend_prod   |                   ^^^^^^^^^^^^^^^
nexa_backend_prod   | TypeError: app.models.domain.Mandate() got multiple values for keyword argument 'version'