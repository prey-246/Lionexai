# NEXA Platform: Feature Deep Dive & Functional Specification

This document provides an exhaustive, formal breakdown of every major system, micro-feature, and algorithmic logic flow within the NEXA MVP platform. It is designed to serve as a comprehensive guide for developers, quants, and stakeholders to understand exactly how the platform operates under the hood.

---

## 1. NEXA Intelligence Foundation (Alt-Data & AI Layer)

The NEXA Intelligence layer transitions the platform from a traditional quantitative terminal into a proactive, AI-driven ecosystem. It ingests, analyzes, and acts upon Alternative Data (Alt-Data).

### 1.1. Data Ingestion (The Scraper)
- **Mechanism**: A synchronous Python script (`scripts/scrape_news.py`) wrapped in an `asyncio` background task running continuously every 1 hour.
- **Source**: Ingests live XML/RSS feeds from major cryptocurrency news outlets (e.g., CoinDesk).
- **Storage**: Parses the RFC-822 timestamps and saves unique articles into the `MarketNewsArticle` PostgreSQL table, ensuring no duplicate entries via URL-matching.

### 1.2. NLP Sentiment Analysis Engine
- **Mechanism**: A heuristic Natural Language Processing (NLP) service (`app/services/nlp_service.py`) running in the background every 10 minutes.
- **Scoring Algorithm**: 
  - The engine scans unanalyzed text (Title + Content) against predefined `BULLISH` (e.g., "surge", "adopt") and `BEARISH` (e.g., "plunge", "sec") keyword sets.
  - It calculates a **Sentiment Score** strictly bounded between **-1.0 (Extreme Fear)** and **1.0 (Extreme Greed)** using the formula: `(Bullish Hits - Bearish Hits) / Total Sentiment Hits`.
- **Asset Mapping**: The engine cross-references the text with an `ASSET_MAPPING` dictionary to bind the score to specific assets (e.g., identifying "bitcoin" and mapping the score to `BTC/USDT`).
- **Aggregation**: Generates a unified `MarketSensitivityScore` for the asset, updating the database with the latest average sentiment.

### 1.3. UI Representation & Live Tickers
- The `MarketSensitivityScore` is broadcasted to the Client Dashboard's live market ticker.
- **Color-Coded Badges**: 
  - Score > `0.2` = **BULLISH** (Green/Success styling)
  - Score < `-0.2` = **BEARISH** (Red/Danger styling)
  - Between `-0.2` and `0.2` = **NEUTRAL** (Gray/Muted styling)

### 1.4. AI-Driven Risk Gatekeeper
- The Risk Engine actively reads the latest `MarketSensitivityScore` before executing any trade.
- If a user attempts to execute a `BUY` order and the target asset's sentiment score is `<= -0.5` (Extreme Bearish), the Risk Engine **blocks the trade**.
- **Rationale**: Protects client capital from catching "falling knives" during highly negative news cycles. (Note: `SELL` orders are always permitted to allow users to cut losses).
- **Global Control**: The `-0.5` threshold is not hardcoded; it is dynamically controlled by the Admin via the `GlobalSettings` table (`extreme_bearish_threshold`).

---

## 2. Institutional Risk Governance (Mandate Engine)

The platform utilizes a strict, hierarchical risk governance model to ensure portfolios never exceed their permitted exposure.

### 2.1. Version-Controlled Mandates
- **Immutability**: Mandates are treated as institutional contracts. They cannot be blindly overwritten.
- **Archiving & Auto-Migration**: When an Admin or Risk Manager edits a mandate (e.g., changing Max Leverage from 2x to 3x):
  1. The current version (v1) is marked `is_active = False` but preserved in the database for auditing.
  2. A new version (v2) is generated containing the updated parameters.
  3. The system executes a bulk SQL `UPDATE` to instantly migrate all active portfolios assigned to v1 over to v2.
- **History UI**: The frontend exposes this via a toggleable "History Drawer", displaying the chronological evolution of the mandate's constraints.

### 2.2. The Global Settings & Kill Switches
- **GlobalSettings Table**: A singleton database row (`id="default"`) that acts as the supreme source of truth for platform-wide configurations.
- **Emergency Halt**: Admins can engage the `global_kill_switch_active` flag. The Risk Engine checks this flag on *every* trade request; if `True`, all execution system-wide is instantly rejected with a 403 Forbidden.
- **Environment State**: Controls the UI Banner (PAPER, BACKTEST, DEMO) to visually warn users of the current execution context.

### 2.3. Dynamic Risk Metrics (High-Water Mark)
- **Live Exposure**: The `PortfolioRiskContext` dynamically calculates `exposure_utilization_pct` by summing the notional value (`quantity * entry_price`) of all `OPEN` trades.
- **High-Water Mark Drawdown**: The execution engine queries `func.max(EquityCurve.equity)` to establish the portfolio's all-time highest valuation. It dynamically recalculates the `current_drawdown_pct` after every trade to track peak-to-trough losses accurately.

---

## 3. High-Fidelity Backtesting & Simulation

The Backtesting Engine is designed to provide highly realistic algorithmic replay, stripping away the illusion of "free" simulated trading.

### 3.1. Historical Data Ingestion
- **Database Native**: Uses a `MarketDataOHLCV` TimescaleDB hyper-table.
- **CCXT Backfill**: Exposes a debug route to request up to 365 days of historical Binance daily data, saving it locally to eliminate third-party API rate limits during simulations.

### 3.2. Vectorized Execution
- Instead of slow, iterative `for` loops, the engine uses **Pandas Vectorization** (`df['signal'].diff()`) to calculate entry and exit points across thousands of rows instantly.

### 3.3. Gross vs. Net Accounting
- **The Reality Filter**: The engine fetches `default_commission_pct` and `default_slippage_pct` from the `GlobalSettings` table (which can be overridden by the user in the UI).
- It calculates the notional value of every position change and explicitly deducts fees and slippage from the cash balance.
- **Output Matrix**: The UI distinctly shows **Gross Return** alongside **Net Return (After Fees)**, calculating total capital lost to slippage and commissions.

---

## 4. Role-Based Access Control (RBAC) & Multi-Tenancy

The platform strictly segregates user workspaces and data access to mimic an enterprise corporate structure.

### 4.1. The Four Tiers
1. **Client**: Can only view their own equity, their own portfolios, and execute trades against them.
2. **Operator**: Monitors system health, daily execution counts, and the live Audit Trail.
3. **Risk Manager**: Designs Mandates, monitors system-wide drawdown/exposure, and investigates Risk Rejections.
4. **Admin**: Supreme access. Manages User Roles and modifies Global Settings.

### 4.2. Next.js Edge Middleware
- **Frontend Bouncer**: `middleware.ts` intercepts all route transitions before the page renders.
- It reads the `user_role` cookie (set securely upon login). If a Client attempts to navigate to `/admin/settings`, the middleware executes a hard HTTP redirect back to `/dashboard`, preventing the UI from ever flashing unauthorized data.
- **Dynamic NavBar**: The sidebar navigation dynamically filters its rendering array, hiding restricted links completely based on the user's role.

### 4.3. Backend Enforcement
- **FastAPI Dependencies**: Protected routes utilize `@Depends(require_role(["admin", "risk_manager"]))`.
- If a compromised frontend attempts to send a `PUT` request to update a mandate, the backend will inspect the JWT token, verify the role, and reject the request at the network layer if unauthorized.

---

## 5. Paper Trading & Market Data Streaming

The MVP execution environment utilizes a hybrid historical-replay approach to provide a realistic, high-speed testing environment.

### 5.1. The WebSocket Replay Engine
- **Historical Loading**: The `market_data_streamer` background task loads historical `MarketDataOHLCV` records into memory on boot.
- **Micro-Volatility Injection**: Every 2 seconds, it broadcasts the historical price to connected clients, but injects a mathematically bounded **0.02% random micro-volatility** (`(random() - 0.5) * 2 * 0.0002`). This ensures the UI ticker feels completely "live" and organic.

### 5.2. Live Execution Pricing
- **Background CCXT Sync**: A `periodic_price_updater` task fetches the absolute latest live prices from Binance every hour and overwrites the current day's OHLCV record.
- **Trade Execution**: When a user clicks "BUY", the `trading.py` route queries the database for the absolute latest closing price to use as the `fill_price`, guaranteeing realistic margin deduction.

### 5.3. Instant Resolution (MVP Characteristic)
- To facilitate rapid UI testing, the MVP executes a trade (`status="OPEN"`), calculates margin impact, and then *immediately* simulates an exit (`status="CLOSED"`).
- The exit price is calculated using a simulated **2% volatility delta**, generating instant P&L to populate the user's charts and stats.

---

## 6. Reporting, Analytics, & Auditing

### 6.1. PDF Report Generation
- **WeasyPrint & Jinja2**: The backend uses an HTML template (`templates/report.html`) infused with Jinja2 variables (Total PNL, Win Rate).
- **On-the-Fly Rendering**: When requested, WeasyPrint compiles the HTML, subsets the required fonts (stripping unused glyphs for tiny file sizes), and returns a raw PDF buffer (`application/pdf`) directly to the browser for download.
- **Metric Precision**: All API metrics are rounded (`round(val, 2)`) and formatted on the frontend (`.toFixed(2)`) to ensure strict institutional presentation (e.g., `53.49%` instead of `53.488372%`).

### 6.2. Immutable Audit Trail
- The `audit_logs` table acts as a permanent ledger for the platform.
- **Data Capture**: Every `action_type` (e.g., `MANDATE_UPDATE`, `KILL_SWITCH_TRIGGERED`) captures a human-readable description alongside a raw `metadata_json` payload containing exact parameters (e.g., Old Leverage vs. New Leverage).
- **Enhanced Filtering (Stage 5)**: Privileged roles (`admin`, `operator`, `risk_manager`) query system-wide logs via `GET /api/audit/` with `search`, `exchange`, `start_date`, and `end_date` filters. Clients see only their own actions.

---

## 7. Institutional Validation Engine (Stages 1–4)

### 7.1. Trade Capture & Scope
- **Service**: `backend/app/services/validation_service.py`
- **Constants**: `backend/app/services/validation_constants.py` — period definitions, metric keys
- **Scope gate**: Only trades with `trade_source = 'AUTONOMOUS'` enter validation metrics. Manual and seed trades remain visible in the trade explorer.
- **Extended fields** on every autonomous execution: `exchange`, `execution_latency_ms`, `strategy_name`, `rejection_reason`, `trade_source`.

### 7.2. Rolling Snapshots
- Pre-calculated rows in `validation_snapshots` for periods TODAY, 7D, 14D, 30D, ALL.
- Scoped keys: `GLOBAL_*`, `PORTFOLIO_{id}_*`, `STRATEGY_{name}_*`.
- Scheduler refreshes every 15 minutes and on application startup.
- Extended KPIs (total orders, best/worst portfolio/strategy, exchange distribution) stored in `chart_data.meta` JSON.

### 7.3. Metrics Computed
Win rate, total PnL, average return, Sharpe ratio, max drawdown, profit factor, fill rate, average latency, largest win/loss, daily/weekly/monthly PnL series, rolling 7-day win rate and drawdown.

### 7.4. Daily Archive (Stage 4)
- `validation_snapshot_history` — append-only, one row per snapshot key per calendar day.
- 730-day retention with automatic purge.
- APIs: `GET /api/validation/history`, `GET /api/validation/history/metrics`, `GET /api/validation/snapshots/range`.

---

## 8. Institutional PDF Reports (Stage 3)

### 8.1. Report Generation Pipeline
```
ValidationSnapshot → validation_report_service.build_context()
    → chart_image_service (matplotlib PNG → base64)
    → validation_report.html (Jinja2, 11 sections)
    → pdf_service.render_pdf()
    → application/pdf response
```

### 8.2. Endpoints
- Parametric: `GET /api/validation/report/pdf?period=30D`
- Presets: `/weekly`, `/monthly`, `/30-day`
- Legacy fallback to 3-day summary when no snapshot exists.

---

## 9. Platform Analytics & Explorer (Stage 5)

### 9.1. Strategy Analytics
- **API**: `GET /api/analytics/strategies?trade_source=AUTONOMOUS`
- **Service**: `backend/app/services/analytics_service.py`
- **UI**: Live performance table on `/strategies` page.

### 9.2. Comparison Tools
- **Portfolios**: `GET /api/analytics/portfolios/compare?ids=PORT-A,PORT-B` (2–6 portfolios, equity curves included).
- **Strategies**: `GET /api/analytics/strategies/compare?names=StratA,StratB` (privileged roles).
- **UI**: `/analytics/compare`

### 9.3. Trade Explorer
- **API**: `GET /api/trades/` with filters: portfolio, symbol, strategy, exchange, trade_source, status, side, date range, free-text search.
- **Pagination**: `skip` + `limit` (max 200).
- **RBAC**: Clients scoped to own portfolios; privileged roles see all trades.
- **UI**: `/trade-explorer`

---

## 10. Frontend Surfaces (Validation & Analytics)

| Route | Features |
|-------|----------|
| `/validation` | Period tabs, KPI grid, 8+ charts, PDF downloads, 3-day legacy panel, historical metrics |
| `/trade-explorer` | Filterable paginated trade table |
| `/analytics/compare` | Portfolio & strategy side-by-side |
| `/execution-health` | Order throughput, rejections, latency |
| `/execution-monitor` | Per-exchange CCXT status |
| `/executive` | Admin summary with strategy success rate |
| `/reports` | Portfolio weekly/monthly PDFs |

Sidebar navigation updated in `TerminalSidebar.tsx`.

---

## 11. Known Gaps (~8% Roadmap Remaining)

- Global unified search across all entities (single search bar)
- Backtest results not wired to strategies page UI
- Risk events not shown on portfolio detail page
- CUSTOM date-range report generation in `/reports` UI
- Dedicated DB columns for meta fields (currently in `chart_data.meta` JSON)

See [VALIDATION_ROADMAP_STATUS.md](./VALIDATION_ROADMAP_STATUS.md) for detailed completion percentages.

---

*This architecture guarantees scalability, strict compliance, and a seamless developer experience as the NEXA platform evolves toward live-market integrations.*