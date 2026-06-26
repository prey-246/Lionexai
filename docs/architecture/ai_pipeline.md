# AI Decision Pipeline

End-to-end flow from market data to client outcomes and validation.

---

## Pipeline Overview

```
Market Data Ingestion (OHLCV, news, events, FRED)
        ↓
Market Intelligence + NLP Sentiment
        ↓
Regime Detection + Macro Intelligence
        ↓
Global Risk Score (0–100)
        ↓
Asset Ranking (risk-adjusted momentum)
        ↓
Allocation Engine (inverse-vol / regime-momentum)
        ↓
Portfolio Rebalancing + Autonomous Execution
        ↓
Weekly Settlement → Treasury Routing
        ↓
LNX Index Snapshot
        ↓
Validation Layer (demo + validated historical)
```

---

## Stage Details

### 1. Market Intelligence

- **Sources:** RSS (CoinDesk, Investing.com), economic calendar, `market_bars`
- **Output:** `market_sensitivity_scores`, `global_market_state`
- **UI:** `/intelligence`, `/market-intelligence`, dashboard widget

### 2. Risk Engine

Two scores (do not conflate):

| Engine | Update | Used on |
|--------|--------|---------|
| Macro Intelligence | Hourly | Dashboard global risk widget |
| Global Risk Engine v2 | On-demand | Research Lab, Fund Performance |

Components: vol, drawdown, sentiment, FRED (VIX, yield curve), correlation stress.

See [Risk Engine](../platform/risk_engine.md).

### 3. Regime Detection

Hourly classification: BULL, BEAR, SIDEWAYS, CRISIS. Tilts allocation weights and cash floors.

### 4. Allocation Engine

Daily 00:10 UTC (and per-fund rebalance frequency). Inverse-vol weights with regime tilts, mandate caps, cash floors.

See [Allocation Engine](../platform/allocation_engine.md).

### 5. Execution

`PortfolioManager` cycle every 60s when `autonomous_v2_enabled`. Routes via `AssetAdapter` to simulated or live exchanges.

### 6. Settlement & Treasury

Monday 01:00 UTC. Guaranteed weekly target for auto-managed portfolios; excess → treasury pools.

See [Treasury](../platform/treasury.md).

### 7. LNX Index

Composite of treasury health, strategy performance, execution quality, AUM growth.

See [LNX Index](../platform/lnx_index.md).

### 8. Validation

- **Validated:** backtests on `market_bars` — never touches operational ledger
- **Demo:** autonomous paper trades — operational snapshots

See [Validation](../platform/validation.md).

---

## Feature Flag

`global_settings.autonomous_v2_enabled` (default `false`) gates multi-asset autonomous execution. Validated portfolios (`*-VALIDATED`) are always excluded from the live autonomous loop.
