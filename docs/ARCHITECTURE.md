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

### 2. Execution & Accounting
- **Portfolio**: Represents an isolated trading account. Tracks `total_equity` and `available_margin`.
- **Trade**: Represents individual paper trades. Tracks entry/exit prices, sizing, and realized `pnl`.
- **EquityCurve**: Time-series snapshots of portfolio equity, used for charting.

### 3. NEXA Intelligence (Alt-Data Layer)
- **MarketNewsArticle**: Scraped news articles from external sources (e.g., CoinDesk).
- **NLPSentiment**: The result of text analysis on a news article. Tracks `sentiment_score` (-1.0 to 1.0) and `sentiment_label` (Bullish/Bearish).
- **MarketSensitivityScore**: Aggregated AI score for a specific asset (e.g., `BTC/USDT`), heavily utilized by the Risk Gatekeeper.

---

## Core Execution Flows

### 1. Trade Execution & Risk Validation
When a user submits a trade via the Terminal:
1. The request hits `POST /api/trading/{portfolio_id}/execute`.
2. The **Risk Engine** (`risk_engine.py`) is instantiated. It evaluates the trade against:
   - **Kill Switch**: Is the global/mandate halt engaged?
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
3. Accurately deducts simulated `commission_pct` and `slippage_pct` costs on every position change to generate realistic `net_return_pct` metrics.

### 4. Background Scheduled Tasks
FastAPI's `asyncio` loop manages continuous background services:
- **Market Data Streamer**: Replays historical database ticks to the frontend WebSockets, injecting micro-volatility to simulate live markets.
- **Price Updater**: Fetches live hourly closing prices from CCXT to ensure the execution terminal prices are accurate.
- **News Scraper**: Pulls RSS feeds from crypto news outlets every hour.
- **NLP Analyzer**: Scans unprocessed news articles every 10 minutes, generates sentiment scores, and updates the global `MarketSensitivityScore`.