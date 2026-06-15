# NEXA Platform Architecture

This document provides a deep dive into the system architecture, database schema, API reference, and core execution flows within the NEXA platform.

---

## 1. System Overview

NEXA operates on a decoupled client-server architecture utilizing **FastAPI** (Python) for the backend and **Next.js** (TypeScript/React) for the frontend, communicating via REST and WebSockets.

### 1.1. Container Topology
1.  **nexa_backend_prod**: Uvicorn ASGI server running FastAPI. Handles all execution, risk logic, and AI scheduled tasks.
2.  **nexa_frontend_prod**: Next.js production server. Handles SSR and client-side rendering.
3.  **nexa_db_prod**: PostgreSQL + TimescaleDB. Handles relational data and time-series tick data.
4.  **nexa_redis_prod**: Redis 7. Handles cache and high-speed pub/sub for WebSocket broadcasting.

---

## 2. Database Schema (Domain Models)

The platform utilizes SQLAlchemy 2.0. The schema is highly relational, relying on integer Primary Keys (`pk_id`) for foreign-key mapping to ensure high performance, while exposing a string `id`s (e.g., `PORT-1234`) to the frontend for security and readability.

### 2.1. Governance & Security
-   **User**: Contains authentication data and `role_tier` (`admin`, `operator`, `risk_manager`, `client`).
-   **Mandate**: Version-controlled risk parameters (`max_leverage`, `max_drawdown_pct`, `daily_loss_limit_pct`). Linked to Portfolios.
-   **GlobalSettings**: Singleton row (`id="default"`). Stores `environment_state`, `global_kill_switch_active`, `extreme_bearish_threshold`, and default trading fees.
-   **AuditLog**: Immutable ledger storing `action_type`, `description`, and `metadata_json`.

### 2.2. Capital & Trading
-   **Portfolio**: Represents an isolated trading account. Tracks `total_equity` and `available_margin`.
-   **Trade**: Represents individual paper trades. Tracks entry/exit prices, sizing, and realized `pnl`.
-   **EquityCurve**: Time-series snapshots of portfolio equity, used for charting.
-   **Strategy**: JSON-parameterized algorithmic models (e.g., MA Crossover, RSI) saved to the registry.

### 2.3. Macro-Financials (Treasury & Yield)
-   **TreasuryPool**: Macro-capital accounts (Reserve, Yield, Growth) dictating overall platform health.
-   **TreasuryTransaction**: Immutable ledger logging all capital transfers and yield sweeps.

### 2.4. NEXA Intelligence (Alt-Data Layer)
-   **MarketNewsArticle**: Scraped news articles from external sources (e.g., CoinDesk).
-   **NLPSentiment**: The result of text analysis on a news article. Tracks `sentiment_score` (-1.0 to 1.0) and `sentiment_label` (Bullish/Bearish).
-   **MarketSensitivityScore**: Aggregated AI score for a specific asset (e.g., `BTC/USDT`), heavily utilized by the Risk Gatekeeper.

---

## 3. Core Execution Flows

### 3.1. Autonomous Paper Trading
The `algo_executor.py` background task awakens every 60 seconds. It scans the `Strategy Registry` for algorithms assigned to active `Portfolios`. It executes the mathematical models against the live market state. If a signal triggers, it routes the trade directly through the **Risk Engine**. If the Risk Engine approves, the trade is sent to the appropriate **Exchange Adapter** (Binance or Bybit) for execution on the testnet.

### 3.2. Risk Engine Pipeline
The `RiskEngine` class is a strict gatekeeper instantiated before *any* trade (manual or autonomous) is committed.

1.  **Global Checks**: Rejects if `GlobalSettings.global_kill_switch_active` is true.
2.  **Mandate Status**: Rejects if the assigned Mandate has its `kill_switch_enabled` tripped.
3.  **Capital Checks**: Rejects if Notional Value > `available_margin`.
4.  **Leverage Limits**: Rejects if Notional Value / `total_equity` > Mandate `max_leverage`.
5.  **Drawdown Limits**: Rejects if `current_drawdown_pct` > Mandate `max_drawdown_pct`.
6.  **AI Integration**: If the order is `BUY`, rejects if the asset's `MarketSensitivityScore` is <= the Global Settings `extreme_bearish_threshold` (e.g., -0.5).

### 3.3. Background Scheduled Tasks
FastAPI's `asyncio` loop manages continuous background services:
-   **Market Data Streamer**: Replays historical database ticks to the frontend WebSockets.
-   **Price Updater**: Fetches live hourly closing prices from CCXT.
-   **News Scraper**: Pulls RSS feeds from crypto news outlets every hour.
-   **NLP Analyzer**: Scans unprocessed news articles every 10 minutes and updates the `MarketSensitivityScore`.
-   **Yield Sweeper**: Automatically calculates total platform realized PnL and executes a 10% ledger sweep to the Treasury Yield Pool.
-   **Algo Executor**: Evaluates assigned quantitative strategies and executes autonomous paper trades.

---

## 4. API Reference

An interactive Swagger/OpenAPI documentation is available at `http://localhost:8000/docs` when the application is running.

### 4.1. Key Endpoints

**System & Health**
-   `GET /api/system/environment`: Get the global operating state of the platform.
-   `GET /api/system/health`: Basic health check for the backend engine.
-   `GET /api/system/background-tasks`: Get the status of all running background daemons.
-   `GET /api/system/settings`: Retrieve global platform settings.
-   `PUT /api/system/settings`: Update global platform settings (Admin only).

**Authentication**
-   `POST /api/auth/token`: Log in to receive a JWT access token.
-   `POST /api/auth/register`: Create a new user account.
-   `GET /api/users/me`: Get the profile of the currently authenticated user.

**Portfolio & Capital Management**
-   `GET /api/portfolios`: List all portfolios accessible to the user.
-   `POST /api/portfolios`: Create a new trading portfolio.
-   `GET /api/portfolios/{id}`: Get details for a single portfolio.
-   `DELETE /api/portfolios/{id}`: Delete a portfolio.

**Trading & Execution**
-   `POST /api/trading/{portfolio_id}/execute`: Execute a manual paper trade (validated by the Risk Engine).
-   `GET /api/exchange/{id}/status`: Get live status from an exchange testnet (Binance/Bybit).
-   `DELETE /api/exchange/{id}/orders/{order_id}`: Cancel an open order on an exchange.

**Quantitative Engine**
-   `POST /api/backtest/run`: Run a vectorized backtest for a given strategy.
-   `GET /api/strategies`: List all saved strategies in the registry.
-   `POST /api/strategies`: Save a new strategy to the registry.
-   `PUT /api/strategies/{id}`: Update a strategy (e.g., to assign it to a portfolio).

**Risk & Governance**
-   `GET /api/mandates`: List all active risk mandates.
-   `PUT /api/mandates/{pk_id}`: Create a new version of a mandate and migrate portfolios.
-   `GET /api/mandates/{id}/history`: View the complete version history of a mandate.
-   `POST /api/stress-test/{scenario_id}/run`: Execute a pre-defined risk validation scenario.

**Reporting & Analytics**
-   `GET /api/audit`: Get a paginated list of all system audit logs.
-   `GET /api/execution/health-stats`: Get aggregated statistics for the Execution Health dashboard.
-   `GET /api/validation/summary`: Get aggregated statistics for the 3-Day Validation dashboard.
-   `GET /api/validation/report/pdf`: Download the 3-Day Validation report as a PDF.
-   `POST /api/validation/reports/generate-simulation`: Generate and download a PDF from the Growth Simulator.

**NEXA Intelligence**
-   `GET /api/intelligence/news`: Get the latest scraped market news.
-   `GET /api/intelligence/sentiment/{symbol}`: Get the current AI sentiment score for an asset.

**Treasury & LNX Ecosystem**
-   `GET /api/treasury/pools`: Get the current balance of all treasury pools.
-   `GET /api/treasury/transactions`: View the immutable treasury ledger.
-   `POST /api/treasury/sweep`: Manually trigger the automated yield sweep.

### 4.2. WebSocket Streams
-   `/ws/market`: Live market data ticks.
-   `/ws/portfolio`: Real-time portfolio updates (trades, P&L).
-   `/ws/alerts`: Critical system and risk alerts.