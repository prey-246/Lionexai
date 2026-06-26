# LionexAI Platform Page Guide

**Complete reference for every UI route:** what each page shows, how metrics are calculated, where data comes from, how it is refreshed, and how historical vs live data flows through the system.

Last updated: **June 2026**

---

## Table of Contents

1. [Data Provenance Model](#1-data-provenance-model)
2. [Background Jobs & Live Update Schedule](#2-background-jobs--live-update-schedule)
3. [Shared UI Components](#3-shared-ui-components)
4. [Global Metric Reference](#4-global-metric-reference)
5. [Page-by-Page Guide](#5-page-by-page-guide)
6. [Data Journey Timelines](#6-data-journey-timelines)
7. [API Quick Map](#7-api-quick-map)

---

## 1. Data Provenance Model

Every performance surface labels its source. **Never mix provenance without an explicit admin toggle.**

| Label | Meaning | Typical Tables / APIs |
|-------|---------|----------------------|
| `VALIDATED_HISTORICAL` | Backtest on real OHLCV from `market_bars` (Binance, yfinance). No demo ledger. | `validated_fund_runs`, `validated_strategy_runs`, validation snapshots with `data_source=validated` |
| `DEMO` | Seeded operational paper ledger (`LNX-*-001` … `003`, autonomous simulated trades) | `trades`, `equity_curves`, `portfolios`, `client_settlements` |
| `PAPER_LIVE` | Long-running autonomous trading with non-simulated exchange routing | `trades` (exchange ≠ simulated), `live_validation_snapshots` |
| `NEWS_AGGREGATE` | NLP sentiment from scraped news and economic events | `market_news_articles`, `nlp_sentiments`, `market_sensitivity_scores` |
| `OPERATIONAL_LEDGER` | Treasury pools, settlements, admin transfers | `treasury_pools`, `treasury_transactions`, `client_settlements` |
| `UNVALIDATED` | No validated run exists yet for that fund/strategy | — |

### Where each label appears by default

| Surface | Default provenance | Admin / operator toggle |
|---------|-------------------|-------------------------|
| `/fund-performance` | `VALIDATED_HISTORICAL` | **Show demo comparison** → extra Demo Ledger column |
| `/validation` | `VALIDATED_HISTORICAL` | **Demo Ledger** toggle |
| `/portfolios/LNX-*-VALIDATED` | `VALIDATED_HISTORICAL` | — |
| `/portfolios/LNX-*-00x` | `DEMO` | — |
| `/lnx`, `/treasury`, `/dashboard` (treasury contrib) | `OPERATIONAL_LEDGER` | — |
| `/simulator` | Target rates from funds (not backtested) | — |

---

## 2. Background Jobs & Live Update Schedule

Defined in `backend/app/main.py`. These jobs write the data that pages read.

### APScheduler (cron / interval)

| Job ID | Function | Cadence | Data written |
|--------|----------|---------|--------------|
| `update_validation_snapshots` | `update_validation_snapshots_job` | Every **15 min** + **00:05 UTC** daily archive | `validation_snapshots`, `validation_snapshot_history` |
| `market_ingestion` | `run_market_ingestion` | Hourly | `market_bars` (OHLCV) |
| `regime_detection` | `run_regime_detection` | Hourly | `market_regimes` |
| `global_market_state` | `run_global_market_state` | Hourly | `global_market_state` |
| `allocation_cycle` | `run_allocation_cycle` | Daily **00:10 UTC** | `portfolio_allocations`, `rebalance_events` |
| `weekly_settlement` | `run_weekly_settlement` | Monday **01:00 UTC** | `client_settlements`, `treasury_transactions`, `equity_curves` |
| `lnx_snapshot` | `run_lnx_snapshot` | Daily **02:00 UTC** | `lnx_index_snapshots` |
| `strategy_optimizer` | `run_strategy_optimizer` | Monday **03:00 UTC** | strategy optimizer scores |
| `market_intel_ingestion` | `run_market_intelligence_ingestion` | Every **2 hours** | news / intel pipeline |
| `paper_trading_validation` | `update_paper_validation_snapshots` | Every **6 hours** | paper validation snapshots |
| `live_validation` | `update_live_validation_snapshots` | Every **6 hours** | `live_validation_snapshots` |
| `allocation_integrity_scan` | `run_integrity_scan` | Hourly | allocation drift alerts |

### Async loops (not APScheduler)

| Loop | Interval | Purpose |
|------|----------|---------|
| `market_data_streamer` | Continuous WebSocket | Live ticks → `/api/ws/market` |
| `periodic_price_updater` | Continuous | Mark-to-market for open positions |
| `periodic_algo_executor` | **60 seconds** | Autonomous trade cycle (`portfolio_manager`) |
| `periodic_news_scraper` | **1 hour** | RSS / crypto news → `market_news_articles` |
| `periodic_nlp_analyzer` | **10 minutes** | NLP → `nlp_sentiments`, `market_sensitivity_scores` |
| `periodic_economic_scraper` | **6 hours** | Economic calendar → `economic_events` |
| `periodic_yield_sweeper` | **1 hour** | Legacy yield sweep on treasury pools |

### Frontend refresh behavior

| Page | Client-side refresh |
|------|---------------------|
| `/dashboard` | WebSocket market ticks; page load only for other data |
| `/execution-health` | Polls API every **30 seconds** |
| Most other pages | Fetch on mount / user action only (no auto-poll) |

---

## 3. Shared UI Components

### `GlobalMarketIntelligence`

Used on: `/dashboard`, `/funds`, `/intelligence`, `/market-intelligence`, `/allocation` (regime badge only).

| Display | API | Source engine |
|---------|-----|---------------|
| Global Risk Score (0–100) | `GET /api/market/global-state` | `MacroIntelligenceEngine` → `global_market_state.global_risk_score` |
| Market Regime | same | `RegimeEngine` (BULL / BEAR / SIDEWAYS / CRISIS) |
| Risk Posture | same | `risk_on_off`: RISK_ON (≤40), RISK_OFF (≥60), NEUTRAL |
| Top Ranked Assets | same | Risk-adjusted momentum ranking from macro engine |
| `computed_at` timestamp | same | Last hourly macro recompute |

**UI color rules:** score ≥60 red (elevated risk), ≤40 green (risk-on), else gold. CRISIS regime pulses red.

**Note:** `/fund-performance` and `/research-lab` also show **Global Risk Engine v2** via `GET /api/validated/global-risk` — a richer composite overlay (see §4.2).

---

## 4. Global Metric Reference

### 4.1 Global Risk Score — Macro Intelligence (dashboard widget)

**Service:** `backend/app/engines/macro_intelligence.py`  
**Stored in:** `global_market_state`  
**Updated:** Hourly + bootstrap on startup

**Inputs:**

- `market_bars` — 3m momentum, drawdown, annualized vol per asset
- `market_sensitivity_scores` — mean sentiment last 3 days
- `economic_events` — high-impact event count
- `market_regimes` — via `RegimeEngine`
- Safe-haven assets (gold vs equity momentum)

**Five components (each 0–100), weighted:**

| Component | Weight | Logic (simplified) |
|-----------|--------|-------------------|
| Volatility | 34% | `avg_vol × 110` |
| Equity drawdown | 22% | `max(SPX/NDX drawdown) × 300` |
| Sentiment | 20% | `50 − sentiment×50` |
| Economic severity | 12% | `high_impact_events / 8 × 100` |
| Safe-haven | 12% | `50 + (gold_mom − eq_mom)×150` |

**Post-processing:**

- Weighted sum → `global_risk_score` (0–100)
- If score ≥ 78 → force regime `CRISIS`
- `risk_on_off`: ≥60 `RISK_OFF`, ≤40 `RISK_ON`, else `NEUTRAL`

---

### 4.2 Global Risk Score — Global Risk Engine v2 (Research Lab / Fund Performance)

**Service:** `backend/app/engines/global_risk_engine.py`  
**API:** `GET /api/validated/global-risk`  
**Updated:** On demand (each API call)

Starts from macro base score, then adjusts:

| Driver | Adjustment |
|--------|------------|
| News sentiment (last 20 scores) | `−avg × 15` |
| BTC 60d realized vol (annualized) | up to +20 if vol > 50% |
| Gold 30d momentum (inverted) | ×5 |
| EURUSD momentum | ×3 |
| Zero economic events tracked | +5 |
| Cross-asset correlation stress | ×10 |
| FRED VIX >30 / >20 | +15 / +8 |
| 10Y–2Y spread <0 | +10 |
| Inverted yield curve | +5 |

**Labels:** LOW / BALANCED / MODERATE / ELEVATED (clamped 0–100). Returns `components` dict for explainability.

---

### 4.3 Performance Engine (equity-based analytics)

**Service:** `backend/app/analytics/performance_engine.py`

Used by: validation snapshots, live validation, portfolio equity analytics.

| Metric | Formula |
|--------|---------|
| Period return | `(end_equity / start_equity − 1) × 100` |
| CAGR | `(end/start)^(365/days) − 1` |
| Sharpe | `(mean_daily_return / std_daily_return) × √252` |
| Sortino | Same with downside deviation only |
| Max drawdown | Peak-to-trough on equity curve |
| Calmar | CAGR / max drawdown |
| Win rate | % closed trades with positive PnL |
| Profit factor | gross wins / gross losses |

Validated snapshots use equity-curve aggregation (not multiplicative compounding of individual trade returns).

---

### 4.4 LNX Composite Index

**Service:** `backend/app/engines/lnx_index.py`  
**Table:** `lnx_index_snapshots`  
**Updated:** Daily 02:00 UTC + after weekly settlement

| Sub-score | Weight | Calculation |
|-----------|--------|-------------|
| Treasury health | 30% | `min(100, reserve_ratio × 2)` where reserve_ratio = RESERVE pool / total treasury NAV |
| Strategy performance | 25% | `50 + (30d_profit / AUM) × 500` capped 0–100 |
| Execution quality | 20% | Autonomous fill rate last 7d (default 75 if no trades) |
| AUM growth | 15% | `50 + weekly_AUM_growth_pct` |
| NAV scale | 10% | `NAV / 1M × 10` |

**Composite:** weighted sum → `composite_index`  
**LNX NAV:** `total_treasury_NAV / 100_000_000` (100M LNX supply)

---

### 4.5 Allocation Engine Weights

**Service:** `backend/app/engines/allocation_engine.py`  
**Updated:** Daily 00:10 UTC (+ per-fund `rebalance_freq_days`, default 7)

| Step | Logic |
|------|-------|
| Base method | `inverse_vol`: weight ∝ 1/vol (floor 0.05) |
| Optional | `regime_momentum`: multiply by `1 + max(momentum,0)×2` |
| Regime tilt | BULL ×1.25, BEAR ×0.4, CRISIS ×0.1 |
| Safe-haven | XAUUSD/XAGUSD ×1.5 in risk-off |
| Cash floor | Policy minimum +15% in RISK_OFF, min 60% in CRISIS |
| Caps | Mandate max position, `fund_asset_universe.max_weight_pct` |
| Output | Normalized `target_weight_pct`; `current_weight_pct` from open positions / NAV |

**Drift (UI):** `current_weight_pct − target_weight_pct` per asset.

---

### 4.6 Weekly Settlement

**Service:** `backend/app/services/settlement_engine.py`  
**Updated:** Monday 01:00 UTC

| Field | Logic |
|-------|-------|
| Opening equity | Prior settlement or portfolio principal |
| Marked equity | Cash + unrealized on open trades |
| Target gain | `opening × (target_weekly_pct / 100)` — PRESERVE 1%, BALANCE 2.5%, ALPHA 5% |
| Excess PnL | Routed to treasury pools: YIELD 40%, GROWTH 25%, RESERVE 15%, OPERATIONS 15%, LNX_INDEX 5% |
| Shortfall | Top-up from YIELD → RESERVE; uncovered → PARTIAL/PASSTHROUGH |
| Client NAV | `opening + target_gain` (or pass-through if shortfall uncovered) |
| Status | SETTLED / PARTIAL / PASSTHROUGH |

---

### 4.7 NLP Sentiment

**Services:** `nlp_service.py`, `market_intelligence_service.py`  
**Tables:** `market_news_articles`, `nlp_sentiments`, `market_sensitivity_scores`

| Step | Logic |
|------|-------|
| Ingestion | RSS (CoinDesk, Investing.com), hourly news scraper, 2h intel ingestion |
| NLP | Heuristic `nexa-heuristic-v1`: bullish/bearish keyword counts → score −1..+1 |
| Per-symbol | Keyword rules map articles to assets |
| GLOBAL_RISK row | Economic events: HIGH impact −0.6, MEDIUM −0.2 + text score |
| Coverage (UI) | DIRECT / ASSET_CLASS_PROXY / insufficient — shown on Intelligence Hub |

**UI thresholds:** score > 0.2 BULLISH (teal), < −0.2 BEARISH (red), else NEUTRAL; no coverage → NO DATA (grey).

---

### 4.8 Alpha Evidence Verdict

**Service:** `backend/app/services/alpha_evidence_service.py`  
**API:** `POST /api/institutional/alpha/evidence/full`

Combines five checks against target monthly return (default 20% for ALPHA fund):

| Check | Threshold | Provenance |
|-------|-----------|------------|
| Latest fund backtest monthly | vs target | VALIDATED_HISTORICAL |
| Historical single-asset grid | vs target | VALIDATED_HISTORICAL |
| Walk-forward avg monthly | ≥80% of target | VALIDATED_HISTORICAL |
| Monte Carlo median monthly | ≥70% of target | VALIDATED_HISTORICAL |
| Paper-live avg monthly (90D) | ≥50% of target | PAPER_LIVE or EXCLUDED_DEMO |

**Verdict:** ≥75% checks pass → SUPPORTED; ≥40% → PARTIALLY_SUPPORTED; else NOT_SUPPORTED.

---

## 5. Page-by-Page Guide

Routes are grouped by primary audience. **Role access** is enforced by Next.js middleware and backend JWT roles.

---

### 5.1 `/login` and `/register` (public)

| Aspect | Detail |
|--------|--------|
| **Purpose** | Authentication |
| **APIs** | `POST /api/auth/token`, `POST /api/auth/register`, `GET /api/auth/me` |
| **Data** | JWT stored in cookie; role tier drives sidebar nav |
| **Refresh** | On submit only |

Demo accounts: see [docs/README.md](../README.md#demo-accounts).

---

### 5.2 `/dashboard` — Client Dashboard

| Aspect | Detail |
|--------|--------|
| **Audience** | Client |
| **Purpose** | Personal fund overview: equity, targets, treasury contributions, LNX, news |

**APIs on load:**

| API | Data shown |
|-----|------------|
| `GET /api/portfolios/summary` | Total equity across user portfolios |
| `GET /api/portfolios/` | Portfolio cards with mandate, equity |
| `GET /api/funds/` | Fund list → average weekly target |
| `GET /api/lnx/index` | LNX composite index |
| `GET /api/intelligence/news?limit=5` | Latest headlines |
| `GET /api/intelligence/sentiment/{symbol}` | Per-asset sentiment (top 6 assets) |
| `GET /api/portfolios/{id}/settlements?limit=5` | Sum of `excess_routed` → Treasury Contributions |
| WebSocket `/api/ws/market` | Live BTC/ETH/SOL prices |

**Key metrics:**

| Metric | Calculation | Source | Provenance |
|--------|-------------|--------|------------|
| Total Equity | Sum of user portfolio `total_equity` | `portfolios` | DEMO or mixed |
| Avg Weekly Target | Mean of `funds.target_weekly_return_pct` | `funds` table | Policy (not backtest) |
| Treasury Contributions | Σ `client_settlements.excess_routed` last 5 per auto portfolio | Settlements | OPERATIONAL_LEDGER |
| LNX Index | `composite_index` from latest snapshot | `lnx_index_snapshots` | OPERATIONAL_LEDGER |
| Global Risk / Regime | See §3 | `global_market_state` | Live macro (hourly) |

**Historical vs live:** Equity and settlements reflect operational ledger history. Macro panel refreshes hourly on backend; prices live via WebSocket.

---

### 5.3 `/funds` — Lionex Funds

| Aspect | Detail |
|--------|--------|
| **Purpose** | Browse funds, view targets/universe, invest capital |

**APIs:** `GET /api/funds/`, `GET /api/portfolios/`, `POST /api/funds/{id}/invest`

**Displays per fund:**

| Field | Source |
|-------|--------|
| Target weekly / monthly % | `funds.target_weekly_return_pct`, `target_monthly_return_pct` |
| Risk label | `funds.risk_label` |
| Asset universe | `fund_asset_universe` join |
| Actual returns (if shown) | `funds` API may include demo actuals from operational ledger |

**Invest flow:** Creates or funds portfolio → triggers allocation engine on next cycle.

**Provenance:** Targets are policy. Actual columns on fund cards may show DEMO operational metrics unless viewing validated surfaces elsewhere.

---

### 5.4 `/fund-performance` — Fund Performance

| Aspect | Detail |
|--------|--------|
| **Audience** | All roles; admin actions for backtests |
| **Purpose** | Primary validated historical fund metrics |

**APIs:**

| API | Purpose |
|-----|---------|
| `GET /api/funds/` | Fund list |
| `GET /api/market/global-state` | Regime / macro risk banner |
| `GET /api/validated/global-risk` | Global Risk Engine v2 |
| `GET /api/validated/fund/latest/{id}` | Validated backtest metrics |
| `GET /api/validated/fund/latest/{id}?include_demo=true` | Admin: side-by-side demo comparison |
| `GET /api/funds/{id}/institutional` | Legacy/demo operational analytics |
| `POST /api/validated/optimization/run` | Run alpha optimization (admin) |
| `POST /api/validated/fund/run-all` | Re-run all fund backtests |

**Metrics (validated primary column):**

| Metric | From `validated_fund_runs` |
|--------|---------------------------|
| Total return, CAGR | Equity curve simulation on `market_bars` |
| Sharpe, Sortino, Calmar | PerformanceEngine on simulated equity |
| Max drawdown, ann vol | Same |
| Win rate | % positive rebalance periods |
| Profit factor | Wins/losses on rebalance returns |
| Yield delivery % | Weeks meeting `target_weekly_return_pct` |
| `meets_target_monthly` | ALPHA: monthly return vs 20% target |

**Simulation assumptions:** Commission 0.10%, slippage 0.10%, regime-aware cash floors, inverse-vol / regime-momentum weights.

**Toggle:** Admin **Show demo comparison** adds red Demo Ledger column from operational portfolios (excludes `*-VALIDATED`).

**Default provenance:** `VALIDATED_HISTORICAL`

---

### 5.5 `/portfolios` — Portfolio List

| Aspect | Detail |
|--------|--------|
| **Purpose** | List/create/delete user portfolios |

**APIs:** `GET /api/portfolios/`, `GET /api/mandates/`, `POST /api/portfolios/`, `DELETE /api/portfolios/{id}`

**Displays:** Portfolio ID, mandate, equity, auto_managed flag.

---

### 5.6 `/portfolios/[id]` — Portfolio Detail

| Aspect | Detail |
|--------|--------|
| **Purpose** | Deep dive: stats, equity curve, trades, allocation, settlements |

**APIs:**

| API | Data |
|-----|------|
| `GET /api/portfolios/{id}` | NAV, mandate, provenance hint |
| `GET /api/portfolios/{id}/stats` | PnL, win rate, trade counts |
| `GET /api/portfolios/{id}/trades` | Trade ledger |
| `GET /api/portfolios/{id}/equity-curve` | NAV time series |
| (components) allocations, settlements, rebalances | Same portfolio namespace |

**Two stat paths:**

| Portfolio type | Stats source |
|----------------|--------------|
| `LNX-*-VALIDATED` | `validated_portfolio_service` — metrics from latest `validated_fund_run`; allocations show target as current; full equity from backtest |
| Demo / operational | Closed `trades` aggregation + `equity_curves` |

**UI:** Blue validated banner for `*-VALIDATED`. Returns computed client-side from equity curve (`computeEquityReturns`).

**Equity curve updates:** On trade close, settlement, autonomous activity, demo reset, validated regenerator.

---

### 5.7 `/allocation` — Live Allocation

| Aspect | Detail |
|--------|--------|
| **Purpose** | Target vs current weights from allocation engine |

**APIs:** `GET /api/portfolios/`, `GET /api/portfolios/{id}/allocations`, `GET /api/market/global-state`

**Table columns:**

| Column | Source field |
|--------|-------------|
| Target % | `portfolio_allocations.target_weight_pct` |
| Current % | `portfolio_allocations.current_weight_pct` (position NAV / total) |
| Drift | current − target (UI highlights if \|drift\| > 2%) |

**Refresh:** Page load; backend updates daily 00:10 UTC (+ rebalance events on regime change).

---

### 5.8 `/lnx` — LNX Ecosystem

| Aspect | Detail |
|--------|--------|
| **Purpose** | LNX token economics and composite index (operational, not validated backtest) |

**APIs:**

| API | Data |
|-----|------|
| `GET /api/lnx/index` | Latest composite + sub-scores |
| `GET /api/lnx/history?limit=90` | 90-day chart |
| `GET /api/treasury/pools/summary` | Reserve balance (client-safe) |
| `GET /api/institutional/lnx/attribution` | Component attribution breakdown |

**Metrics:** See §4.4. Weekly/monthly change computed from snapshot history.

**Provenance:** `OPERATIONAL_LEDGER` — includes demo ledger when seeded.

---

### 5.9 `/intelligence` — Intelligence Hub

| Aspect | Detail |
|--------|--------|
| **Purpose** | NLP sentiment, news, economic calendar with coverage-aware labels |

**APIs:**

| API | Data |
|-----|------|
| `GET /api/intelligence/news?limit=15` | Headlines |
| `GET /api/intelligence/events?limit=8` | Economic calendar |
| `GET /api/intelligence/sentiment?limit=9` | Sentiment pulse grid |
| `GET /api/market/global-state` | GlobalMarketIntelligence widget |

**Sentiment display:** Uses `contributing_factors.coverage` — DIRECT and ASSET_CLASS_PROXY show real scores; else NO DATA.

**Refresh:** Backend NLP every 10 min; news hourly; page fetch on load.

---

### 5.10 `/market-intelligence` — Global Market Intelligence

| Aspect | Detail |
|--------|--------|
| **Purpose** | Unified dashboard: asset pulse, regimes, regional news |

**APIs:** `GET /api/market-intelligence/dashboard`, `GET /api/intelligence/sentiment?limit=12`

**Dashboard payload includes:** macro `global_state`, regimes, news with region tags, `global_risk_sentiment` from latest `GLOBAL_RISK` sensitivity row.

---

### 5.11 `/simulator` — Growth Simulator

| Aspect | Detail |
|--------|--------|
| **Purpose** | Forward projection from fund **target** weekly rates (not validated backtest) |

**APIs:** `GET /api/funds/` (target rates), optional PDF via validation API

**Client-side calculation:**

```
weeklyRate = fund.target_weekly_return_pct / 100  (PRESERVE ~1%, BALANCE ~2.5%, ALPHA ~5%)
each week: capital *= (1 + weeklyRate)
each month: + monthlyContribution; optional withdrawal % of capital
projectedCapital, totalYield, yieldPct computed at end
```

**Provenance:** **Policy targets only** — illustrative, not `VALIDATED_HISTORICAL`.

---

### 5.12 `/validation` — Validation Framework

| Aspect | Detail |
|--------|--------|
| **Audience** | Operator, risk_manager, admin |
| **Purpose** | Long-term validation metrics with validated/demo toggle |

**APIs:**

| API | When |
|-----|------|
| `GET /api/validation/snapshots?period=&data_source=validated\|demo` | Primary metrics |
| `GET /api/validation/summary` | Demo mode only — operational summary |
| `GET /api/institutional/live-validation/snapshots` | Demo mode — paper/live overlay |
| `GET /api/validation/metrics/{key}/timeseries` | Demo mode — win rate / drawdown history |
| `POST /api/validation/refresh` | Force recompute demo snapshots |
| PDF download | `GET /api/validation/report/{period}` |

**Default:** `data_source=validated` → `VALIDATED_HISTORICAL` from `validated_fund_runs` equity aggregation.

**Demo mode:** AUTONOMOUS trades + equity curves; excludes `*-VALIDATED` from global scope.

**Core snapshot metrics:**

| Metric | Validated path | Demo path |
|--------|---------------|-----------|
| Avg return / day | Equity curve daily returns | Same from demo equity |
| Sharpe, Sortino | PerformanceEngine | Same |
| Max drawdown | Peak-trough on equity | Same (sanitized, capped 0–100%) |
| Win rate | Rebalance win rate (validated) or closed trades | Closed trades |
| Profit factor | Rebalance returns | Trade PnL |
| Fill rate, latency | N/A in validated mode | From `audit_logs` |
| Exposure % | From backtest simulation | Open positions / equity |

**Periods:** TODAY, 7D, 14D, 30D, 90D, 180D, 365D, ALL.

**Refresh:** Backend every 15 min; daily archive at 00:05 UTC.

---

### 5.13 `/research-lab` — Strategy Research Lab

| Aspect | Detail |
|--------|--------|
| **Purpose** | Run strategy backtests, view runs, global risk, allocation alerts |

**APIs:**

| API | Action |
|-----|--------|
| `GET /api/funds/` | Fund context |
| `GET /api/validated/strategy/runs` | Historical run list |
| `GET /api/validated/global-risk` | Global Risk Engine v2 |
| `GET /api/validated/allocation/alerts` | Drift / integrity alerts |
| `POST /api/validated/strategy/run` | Trigger backtest |
| `POST /api/institutional/alpha/evidence/full` | Alpha evidence block |

**Provenance:** All backtest results `VALIDATED_HISTORICAL`.

---

### 5.14 `/alpha-evidence` — Alpha Evidence Dashboard

| Aspect | Detail |
|--------|--------|
| **Purpose** | Institutional verdict on ALPHA 20% monthly target |

**API:** `POST /api/institutional/alpha/evidence/full` with `{ fund_id: 'ALPHA', target_monthly_pct }`

**Displays:** Verdict (SUPPORTED / PARTIALLY_SUPPORTED / NOT_SUPPORTED), rationale, four evidence blocks with JSON detail.

**Re-evaluate:** User can change target % and reload.

---

### 5.15 `/treasury` — Treasury NAV

| Aspect | Detail |
|--------|--------|
| **Audience** | Risk manager, admin |
| **Purpose** | Pool balances, transactions, profit routing, verification |

**APIs:**

| API | Data |
|-----|------|
| `GET /api/treasury/pools` | All pool balances + targets |
| `GET /api/treasury/transactions` | Immutable ledger |
| `GET /api/treasury/routing` | Settlement profit routing history |
| `GET /api/treasury/pools/analytics` | Per-pool contributions/withdrawals |
| `GET /api/institutional/treasury/verify` | Balance reconciliation check |
| `POST /api/treasury/seed`, `/transfer`, `/sweep` | Admin actions |

**Pools:** RESERVE, YIELD, GROWTH, OPERATIONS, INSURANCE, LNX_INDEX — each with `target_allocation_pct`.

**Provenance:** `OPERATIONAL_LEDGER`

---

### 5.16 `/` — System Operations (operator home)

| Aspect | Detail |
|--------|--------|
| **Audience** | Operator |
| **Purpose** | Engine health, recent audit activity, risk rejections |

**APIs:** `GET /api/system/health`, `GET /api/audit/`

**Health fields:** API status, database connection, trades_today count.

---

### 5.17 `/executive` — Executive Summary

| Aspect | Detail |
|--------|--------|
| **Audience** | Admin |
| **Purpose** | Platform-wide KPIs aggregated client-side |

**APIs:** portfolios, treasury pools/transactions, strategies, system health, audit rejections, execution health, exchange status, background tasks.

**Computed client-side:**

| KPI | Formula |
|-----|---------|
| Platform AUM | Σ portfolio `total_equity` |
| Corporate Treasury NAV | Σ pool balances |
| LNX NAV | RESERVE balance / 100M |
| Yield Generated | Σ positive YIELD_SWEEP transactions |
| Autonomous AUM | Portfolios linked to active autonomous strategies |
| Execution fill rate | From execution health API |

---

### 5.18 `/risk` — Risk Command Center

| Aspect | Detail |
|--------|--------|
| **Audience** | Risk manager |
| **Purpose** | Portfolio-level risk overview |

**APIs:** `GET /api/portfolios/`, audit APIs for rejections/kill-switch events.

---

### 5.19 `/mandates` — Mandate Contracts

| Aspect | Detail |
|--------|--------|
| **Purpose** | View/edit investment mandates (position limits, allowed assets, kill switch) |

**APIs:** `GET/PUT /api/mandates/`, activate/deactivate, history, `POST /api/trading/mandates/{id}/reset` for kill switch.

**Affects:** Trade execution risk checks, allocation caps.

---

### 5.20 `/audit` — Audit Trail

| Aspect | Detail |
|--------|--------|
| **Purpose** | Paginated immutable audit log |

**API:** `GET /api/audit/` with filters (action_type, exchange, date range, search).

**Sources:** Trades, settlements, admin actions, risk rejections, kill switch.

---

### 5.21 `/trade-explorer` — Trade Explorer

| Aspect | Detail |
|--------|--------|
| **Purpose** | Search/filter trades across portfolios |

**API:** `GET /api/trades/` (paginated filters).

---

### 5.22 `/trade` — Trading Terminal

| Aspect | Detail |
|--------|--------|
| **Purpose** | Manual simulated trade execution |

**APIs:** `POST /api/trading/{portfolio_id}/execute`, portfolio list/get.

**Flow:** Risk engine validates against mandate → simulated fill → updates positions/trades/equity.

---

### 5.23 `/backtest` — Strategy Engine

| Aspect | Detail |
|--------|--------|
| **Purpose** | Ad-hoc strategy backtest (operator) |

**API:** `POST /api/backtest/run`

**Input:** symbol, strategy params, date range on `market_bars`.

---

### 5.24 `/strategies` — Strategy Registry

| Aspect | Detail |
|--------|--------|
| **Purpose** | CRUD for strategy definitions, optimizer scores |

**APIs:** `GET/POST/PUT /api/strategies`, portfolio list for assignment.

---

### 5.25 `/execution-monitor` and `/execution-health`

| Route | Purpose | Refresh |
|-------|---------|---------|
| `/execution-monitor` | Exchange order monitoring | Page load |
| `/execution-health` | Fill rate, latency, rejections breakdown | **30s poll** |

**API:** `GET /api/execution/health-stats`

**Metrics:** Today's order count, fill rate %, avg placement latency ms, risk rejection breakdown by reason.

---

### 5.26 `/stress-test` — Risk Stress Tests

| Aspect | Detail |
|--------|--------|
| **Purpose** | Scenario simulation on portfolio |

**API:** `POST /api/stress-test/{scenario_id}/run`

---

### 5.27 `/analytics/compare` — Compare Analytics

| Aspect | Detail |
|--------|--------|
| **Purpose** | Cross-portfolio/strategy comparison |

**APIs:** Portfolio list + analytics comparison endpoints under `/api/analytics/`.

---

### 5.28 `/reports` — Performance Reports

| Aspect | Detail |
|--------|--------|
| **Purpose** | Generate/download PDF portfolio reports |

**APIs:** `POST /api/reports/generate`, `GET /api/reports/{portfolio_id}`, download by report ID.

---

### 5.29 `/admin/users` and `/admin/settings`

| Route | Purpose |
|-------|---------|
| `/admin/users` | User list, role tier updates (`GET/PUT /api/users`) |
| `/admin/settings` | Global settings e.g. `autonomous_v2_enabled` (`GET/PUT /api/system/settings`) |

---

## 6. Data Journey Timelines

### 6.1 Market bar → Validated fund metric (days to weeks)

```
External APIs (Binance, yfinance)
    → hourly market_ingestion → market_bars
    → POST /api/validated/fund/run (or optimization program)
    → historical_fund_simulator rebalance loop on bars
    → validated_fund_runs (equity curve + metrics)
    → GET /api/validated/fund/latest/{id}
    → /fund-performance UI
```

**Historical depth:** Depends on `bar_limit` in optimization (typically 1–3 years of bars). Not live-updated unless admin re-runs backtest.

---

### 6.2 Live autonomous trade → Demo validation snapshot (minutes to hours)

```
periodic_algo_executor (60s)
    → portfolio_manager → trades (AUTONOMOUS, simulated)
    → equity_curves on close / mark
    → update_validation_snapshots_job (15 min)
    → validation_snapshots (data_source=demo)
    → /validation Demo Ledger toggle
```

---

### 6.3 Weekly client economics (Monday cycle)

```
Monday 01:00 UTC run_weekly_settlement
    → mark portfolios → client_settlements
    → excess → treasury_transactions (profit routing)
    → equity_curves post-settlement point
    → triggers LNX snapshot recompute
    → /dashboard treasury contributions, /portfolios settlements panel, /treasury routing
```

---

### 6.4 News → Global risk on dashboard (10 min – 1 hour)

```
RSS / scraper (1h) → market_news_articles
    → NLP loop (10 min) → market_sensitivity_scores
    → hourly run_global_market_state → global_market_state
    → GlobalMarketIntelligence on /dashboard, /funds, etc.
```

Parallel path: `GlobalRiskEngine.assess()` on API call adds FRED + correlation overlay for `/fund-performance` and `/research-lab`.

---

### 6.5 Validated reference portfolio regeneration

```
run_alpha_optimization.py --phase all
    → best config in validated_fund_runs (SELECTED_BEST)
    → ValidatedInstitutionalRegenerator.regenerate_all()
    → LNX-*-VALIDATED portfolios: trades, allocations, equity from backtest metrics
    → autonomous_manager SKIPS *-VALIDATED
    → /portfolios/LNX-ALPHA-VALIDATED shows validated stats
```

---

## 7. API Quick Map

| Page route | Primary API prefix |
|------------|-------------------|
| `/dashboard` | `/api/portfolios/`, `/api/funds/`, `/api/lnx/`, `/api/intelligence/`, WS `/api/ws/market` |
| `/funds` | `/api/funds/` |
| `/fund-performance` | `/api/validated/fund/`, `/api/validated/global-risk`, `/api/market/global-state` |
| `/portfolios/*` | `/api/portfolios/` |
| `/allocation` | `/api/portfolios/{id}/allocations`, `/api/market/global-state` |
| `/lnx` | `/api/lnx/`, `/api/treasury/pools/summary`, `/api/institutional/lnx/` |
| `/intelligence` | `/api/intelligence/` |
| `/market-intelligence` | `/api/market-intelligence/dashboard` |
| `/simulator` | `/api/funds/` (targets only) |
| `/validation` | `/api/validation/`, `/api/institutional/live-validation/` |
| `/research-lab` | `/api/validated/` |
| `/alpha-evidence` | `/api/institutional/alpha/evidence/full` |
| `/treasury` | `/api/treasury/`, `/api/institutional/treasury/verify` |
| `/executive` | Multiple (portfolios, treasury, system, execution) |
| `/execution-health` | `/api/execution/health-stats` |
| `/` (operator) | `/api/system/health`, `/api/audit/` |

Full endpoint catalog: [API Reference](../api/api_reference.md)

---

## Related Documentation

| Doc | Topic |
|-----|-------|
| [Validation](../platform/validation.md) | Validated vs demo framework |
| [Treasury](../platform/treasury.md) | Pools, settlement, verification |
| [Funds](../platform/funds.md) | Fund products and targets |
| [Database](../architecture/database.md) | Table schemas |
| [Developer Setup](./developer_setup.md) | Local setup, scheduler, troubleshooting |
| [Archive: Historical Validation Audit](../archive/HISTORICAL_VALIDATION_AUDIT.md) | Demo vs validated audit (historical) |
