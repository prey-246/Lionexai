# NEXA System Architecture

This document provides a deep dive into the database schema, microservice topology, and autonomous service loops powering the NEXA Platform.

## 1. Container Topology

The platform utilizes a decoupled, containerized microservices architecture:

*   **nexa_backend_prod**: The core API and Execution Engine. Powered by **FastAPI** running on the **Uvicorn** ASGI server (Python 3.12). It handles REST requests, WebSocket broadcasting, Vectorized Backtesting (Pandas), and runs the asynchronous background task loop.
*   **nexa_frontend_prod**: The client-facing interface. Powered by **Next.js 15** (React/TypeScript). Handles Server-Side Rendering (SSR), Edge Middleware for RBAC security, and client-side visualization via Tailwind CSS and TradingView Lightweight Charts.
*   **nexa_db_prod**: The persistence layer. Powered by **PostgreSQL 15** + **TimescaleDB** extension. It manages highly relational entity data and high-frequency time-series OHLCV market data.
*   **nexa_redis_prod**: The caching and pub/sub layer. Powered by **Redis 7**. Used for high-speed WebSocket message brokering and session rate-limiting.

---

## 2. Database ERD & Data Models

The database uses SQLAlchemy 2.0 ORM. All entities utilize an integer primary key (`pk_id`) for high-performance relational joins, while exposing a string `id` (e.g., `PORT-1234`) to the frontend APIs.

### 2.1 Governance & Security
*   **User**: `id`, `email`, `hashed_password`, `role_tier` (client, operator, risk_manager, admin).
*   **Mandate**: `pk_id`, `id` (e.g., 'ALPHA'), `version`, `max_leverage`, `max_drawdown_pct`, `daily_loss_limit_pct`, `is_active`. Maintains immutable version history via `previous_version_pk_id`.
*   **GlobalSettings**: Singleton row (`id="default"`). Stores `environment_state`, `global_kill_switch_active`, `extreme_bearish_threshold`, and default trading fees.
*   **AuditLog**: Immutable ledger storing `action_type`, `description`, and `metadata_json`.

### 2.2 Capital & Trading
*   **Portfolio**: `pk_id`, `id`, `user_id`, `mandate_pk_id`, `total_equity`, `available_margin`. Represents a live paper-trading account.
*   **Trade**: `pk_id`, `portfolio_id`, `symbol`, `side` (BUY/SELL), `size`, `entry_price`, `exit_price`, `pnl`, `status` (OPEN/CLOSED/REJECTED).
*   **EquityCurve**: Time-series snapshots mapping `portfolio_pk_id` to `equity` and `timestamp`.

### 2.3 Quantitative & Execution
*   **Strategy**: `id`, `name`, `description`, `parameters` (JSONB), `is_active`. Saved backtest models.
*   **BacktestResult**: Historical simulation outputs mapping `strategy_id` to performance metrics (JSONB).

### 2.4 Treasury & Yield
*   **TreasuryPool**: `pk_id`, `id` (RESERVE, YIELD, GROWTH), `balance`, `target_allocation_pct`.
*   **TreasuryTransaction**: `pool_pk_id`, `amount`, `transaction_type` (e.g., YIELD_SWEEP), `timestamp`.

### 2.5 NEXA Intelligence (Alt-Data)
*   **MarketNewsArticle**: `title`, `url`, `source`, `published_at`. Scraped RSS data.
*   **NLPSentiment**: `article_id`, `symbol`, `sentiment_score` (-1.0 to 1.0), `sentiment_label`.
*   **MarketSensitivityScore**: `symbol`, `aggregated_score`, `timestamp`. The final AI metric read by the Risk Engine.

---

## 3. The Asynchronous Engine (Background Tasks)

The backend utilizes FastAPI's `asyncio` event loop to run continuous daemon processes that power the autonomous ecosystem.

1.  **Market Data Streamer (`market_data_streamer`)**: Runs continuously. Replays historical TimescaleDB ticks over WebSockets to the frontend, injecting 0.02% micro-volatility to simulate live spread action.
2.  **Price Updater (`periodic_price_updater`)**: Runs hourly. Re-syncs internal databases with live Binance/CCXT closing prices to ensure accurate simulated execution fills.
3.  **News Scraper (`periodic_news_scraper`)**: Runs hourly. Ingests CoinDesk XML/RSS feeds and securely deduplicates articles by title before saving to the DB.
4.  **NLP Analyzer (`periodic_nlp_analyzer`)**: Runs every 10 minutes. Scans unanalyzed text content, extracts bullish/bearish heuristic patterns, and recalculates the `MarketSensitivityScore`.
5.  **Yield Sweeper (`periodic_yield_sweeper`)**: Runs hourly. A stateless reconciliation script that calculates total platform historical PnL, deducts previously swept yield, and transfers 10% of new profits into the `YIELD` TreasuryPool.
6.  **Autonomous Executor (`periodic_algo_executor`)**: Runs every 60 seconds. 
    *   Scans the `Strategy` registry for active algorithms assigned to a `Portfolio`.
    *   Fetches the latest 100 OHLCV candles.
    *   Calculates moving averages or RSI math to determine signals.
    *   Generates a Trade execution order securely routed through the **Risk Engine**.

---

## 4. The Risk Engine Pipeline

The `RiskEngine` class is a strict gatekeeper instantiated before *any* trade (manual or autonomous) is committed to the database.

**The Evaluation Flow:**
1.  **Global Checks**: Rejects if `GlobalSettings.global_kill_switch_active` is true.
2.  **Mandate Status**: Rejects if the assigned Mandate has its `kill_switch_enabled` tripped.
3.  **Capital Checks**: Rejects if Notional Value > `available_margin`.
4.  **Leverage Limits**: Rejects if Notional Value / `total_equity` > Mandate `max_leverage`.
5.  **Drawdown Limits**: Rejects if `current_drawdown_pct` > Mandate `max_drawdown_pct`.
6.  **AI Integration**: If the order is `BUY`, rejects if the asset's `MarketSensitivityScore` is <= the Global Settings `extreme_bearish_threshold` (e.g., -0.5).

If rejected, an `AuditLog` of type `RISK_REJECTION` is generated for compliance tracking.