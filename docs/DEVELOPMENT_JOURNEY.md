# NEXA Platform: Development Journey & Changelog

This document chronicles the evolution of the UnifyX NEXA platform from a barebones MVP into a production-grade, AI-driven institutional quantitative trading system. 

It details the major features implemented, the architectural shifts, and the specific challenges and bugs overcome during development.

---

## Stage 1: Platform Hardening & Risk Governance
**Objective:** Establish strict, immutable risk controls and system-wide environmental awareness.

### 🚀 Major Features Added
- **Global Environment State:** Added an `ENVIRONMENT_STATE` (PAPER, BACKTEST, DEMO, LIVE) accessible via the `/api/system/environment` endpoint to govern UI and execution logic.
- **Institutional Risk Mandates:** Overhauled the `Mandate` schema to include version control (`version`, `is_active`, `previous_version_pk_id`).
- **Dynamic Auto-Migration:** When an Admin edits a mandate, the system archives the old version, creates a new one, and automatically updates all associated portfolios.
- **Rich Risk Context:** Built a real-time `PortfolioRiskContext` payload that calculates `capital_at_risk` and `current_drawdown_pct` dynamically.

### 🐛 Bugs & Triumphs
- **The PK_ID Migration Challenge:** We shifted from string-based IDs (e.g., `PORT-123`) to high-performance integer primary keys (`pk_id`) for foreign key relationships.
  - **Log Encountered:** `Type error: Argument of type 'number' is not assignable to parameter of type 'SetStateAction<string>'.`
  - **Resolution:** Systematically updated the entire Next.js frontend (`types.ts`) and Pydantic schemas to strictly differentiate between the display `id` (string) and relational `pk_id` (number).
- **Audit Log Schema Crash:** 
  - **Log Encountered:** `TypeError: create_audit_log() got an unexpected keyword argument 'metadata'`
  - **Resolution:** Re-architected `audit_service.py` to use `metadata_json` and gracefully extract `user_id` to prevent silent transaction rollbacks.

---

## Stage 2: Institutional Structure & RBAC
**Objective:** Build a multi-tenant, role-based system separating clients, operators, risk managers, and admins.

### 🚀 Major Features Added
- **Role-Based Access Control (RBAC):** Added `role_tier` to the User schema (`client`, `operator`, `risk_manager`, `admin`).
- **Backend Route Protection:** Implemented a powerful `@Depends(require_role([...]))` FastAPI decorator to lock down sensitive endpoints (e.g., Mandate editing, User management).
- **Next.js Edge Middleware:** Built `middleware.ts` to intercept frontend routing. It reads the `user_role` cookie and instantly bounces unauthorized users to their respective dashboards.
- **Admin Workspace:** Created `/admin/users` to dynamically manage user roles, and `/admin/settings` to manage global AI thresholds and leverage ceilings.
- **Dynamic Role-Based NavBar:** Refactored the `NavBar` component to automatically filter and hide navigation links based on the user's role.
- **Mock Data Seeding:** Created `seed_mock_data.py` to rapidly generate test users (Operators, Risk Managers, Clients) and mock portfolios.

### 🐛 Bugs & Triumphs
- **Database Not-Null Violations:**
  - **Log Encountered:** `sqlalchemy.exc.IntegrityError: (psycopg2.errors.NotNullViolation) column "id" of relation "audit_logs" contains null values`
  - **Resolution:** When adding required columns via Alembic, existing test data caused migrations to crash. We bypassed this by utilizing Docker interactive shells to truncate test tables (`TRUNCATE TABLE audit_logs;`) before migrating the schema.
- **Missing API Routes for Admin UI:**
  - **Log Encountered:** `404 Not Found` on `/api/users`.
  - **Resolution:** Added `GET /api/users` and `PUT /api/users/{user_id}/role` endpoints in `users.py` to allow the Admin UI to correctly fetch and manage user roles.

---

## Stage 3: Real Market Data & High-Fidelity Simulation
**Objective:** Eliminate random mock data and introduce realistic trading costs and historical replay.

### 🚀 Major Features Added
- **Historical Data Pipeline:** Integrated CCXT to fetch Binance OHLCV data and store it in a dedicated `MarketDataOHLCV` table.
- **Vectorized Backtesting Engine:** Upgraded `backtest.py` to use Pandas for high-speed simulation against historical database records.
- **Realistic Slippage & Commissions:** The backtester now subtracts `commission_pct` and `slippage_pct`, delivering highly accurate `net_return_pct` and `gross_return_pct` metrics.
- **Live Ticker Replay:** Rewrote the WebSocket streamer. Instead of broadcasting a random walk, it now loads historical data into memory, adds 0.02% micro-volatility, and replays real market ticks to the frontend.
- **Live Execution Pricing:** Added a `periodic_price_updater` background task to frequently query CCXT and ensure terminal paper trades execute at realistic live prices instead of hardcoded values.

### 🐛 Bugs & Triumphs
- **The String/Integer Ghost Bug:**
  - **Log Encountered:** `sqlalchemy.exc.DataError: (psycopg2.errors.InvalidTextRepresentation) invalid input syntax for type integer: "kill"`
  - **Resolution:** The `get_portfolio_summary` route was querying the `trades` table using the string `portfolio.id` instead of the new integer `portfolio.pk_id`. Refactored all portfolio relational queries to strictly use `pk_id`.
- **Lightweight Charts Visibility Issue:**
  - **Issue:** The Equity Curve chart was completely invisible for new portfolios.
  - **Resolution:** Lightweight Charts requires integer UNIX timestamps and a minimum of 2 data points. Added backend logic to auto-inject a baseline `EquityCurve` point on portfolio creation, and frontend logic to auto-duplicate single points to draw a flat starting line.

---

## Stage 4: Reporting & NEXA Intelligence Foundation
**Objective:** Generate exportable PDF reports and build an AI-driven NLP layer for alt-data analysis.

### 🚀 Major Features Added
- **PDF Generation Engine:** Integrated `WeasyPrint` and `Jinja2` to render custom HTML templates into downloadable institutional reports.
- **NEXA Intelligence Schema:** Created `MarketNewsArticle`, `NLPSentiment`, `EconomicEvent`, and `MarketSensitivityScore` tables.
- **Live News Scraper:** Built an automated background task (`scrape_news.py`) that fetches live RSS feeds from CoinDesk.
- **Heuristic NLP Engine:** Built `nlp_service.py` to analyze article sentiment (-1.0 to 1.0) and map them to specific assets (BTC, ETH, SOL).
- **Global Settings Persistence:** Created a `GlobalSettings` database table to persist Admin settings (environment state, default commissions, global max leverage, and global kill switch).
- **AI Risk Integration:** The Risk Engine now intercepts trade requests and blocks `BUY` orders if the asset's Market Sensitivity Score is `<= -0.5`.

### 🐛 Bugs & Triumphs
- **Mandate Versioning Crash:**
  - **Log Encountered:** `TypeError: Mandate() got multiple values for keyword argument 'version'`
  - **Resolution:** When dynamically creating new mandate versions upon update, excluded specific metadata fields (`version`, `pk_id`) during the object cloning process to allow explicit reassignment.
- **Frontend Form Missing Variable:**
  - **Log Encountered:** `Type error: Cannot find name 'form'` in `AdminSettingsPage`.
  - **Resolution:** React required the `form` state initialized properly. Correctly wired `useState` with `GlobalSettings` defaults and `systemAPI` fetching.
- **The WeasyPrint Dependency Hell:**
  - **Log Encountered:** `ModuleNotFoundError: No module named 'jinja2'` followed by `OSError: cannot load library 'pangoft2-1.0-0'`
  - **Resolution:** Rebuilt the `python:3.12-slim` Dockerfile to include OS-level C-libraries (`libpango-1.0-0`, `libcairo2`, `libffi-dev`).
  - **Log Encountered:** `AttributeError: 'super' object has no attribute 'transform'`
  - **Resolution:** WeasyPrint v62.1 clashed with the newest `pydyf` release. Attempted to pin `WeasyPrint==62.3` and `pydyf==0.9.0`, which resulted in a `ResolutionImpossible` conflict in Pip. Ultimately solved by removing the strict version pins in `requirements.txt` entirely and doing a clean, non-cached Docker rebuild (`--build --force-recreate`).

---

## Conclusion
The platform has successfully transitioned from a conceptual MVP to a highly secure, data-rich ecosystem ready for live-market integration and advanced Machine Learning expansion.