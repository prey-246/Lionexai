# Phase 5 — Platform Audit Report

**Date:** June 2026  
**Scope:** Full codebase audit for demo vs live metrics, institutional credibility, allocation integrity, and validation separation.

---

## Executive Summary

| Category | Verdict |
|----------|---------|
| Demo vs validated separation | **Was insufficient** — UI labeled seeded ledger as "realized" |
| Market price data | **Mixed** — Binance/yfinance when ingested; mock fallback |
| Trade/settlement ledger | **Mostly demo** after `reset_institutional_demo.py` |
| Allocation actual weights | **Was broken** — could exceed 100% (fixed in Phase 5) |
| Validation Sharpe/drawdown | **Non-standard formulas** on dollar PnL series |
| Alpha 20% monthly target | **Not supported by historical backtests** (evidence framework added) |

**Phase 5 response:** Separate `VALIDATED_HISTORICAL` storage, provenance badges, Research Lab, Global Risk Engine, allocation integrity monitor, institutional fund analytics.

---

## 1. Simulated / Demo-Only Metrics

| Source | Path | Issue |
|--------|------|-------|
| Institutional demo reset | `backend/scripts/reset_institutional_demo.py` | Forces weekly PnL, win rates, settlements |
| Simulated exchange | `backend/app/exchange/simulated.py` | All non-crypto + PAPER crypto fills |
| Mock provider | `backend/app/services/providers/mock_provider.py` | Random walk OHLCV |
| Exchange UI success rate | `backend/app/api/routes/exchange.py` | Random 55–75% mocked |
| Intelligence confidence | `frontend/src/app/intelligence/page.tsx` | Synthetic 50–99% from sentiment score |
| System task health | `backend/app/api/routes/system.py` | Demo healthy status |

## 2. Live / External Data

| Source | Path |
|--------|------|
| Crypto OHLCV | Binance via `market_data_service` |
| Metals/FX/indices | yfinance |
| News RSS | CoinDesk, Investing.com (`market_intelligence_service`) |
| NLP sentiment | Heuristic keyword engine (`nlp_service`) |

## 3. Mathematically Incorrect or Misleading

| Metric | Location | Problem |
|--------|----------|---------|
| Sharpe ratio | `validation_service.py` | % change of cumulative dollar PnL, not return series |
| Treasury growth % | `validation_service.py` | NAV / first transaction amount |
| `asset_performance_pct` | `validation_service.py` | Absolute dollars, labeled as % |
| Client yield delivery | `validation_service.py` | Defaults to 100% when no settlements |
| LNX AUM growth | `lnx_index.py` | Field semantics mismatch |
| Backtest sizing | `backtest.py` | 1-unit hold, not capital-weighted |
| Fund monthly target | `fund_performance_service.py` | weekly × 4.33 linear (documented) |

## 4. Demo Presented as Actual Performance

| UI | Issue |
|----|-------|
| `/fund-performance` "Realized" | Sourced from seeded equity curves — **now labeled with `DEMO` provenance** |
| `/allocation` "Live" | Targets live; actual was stale/wrong — **now recomputed at read** |
| `/validation` "live paper" | Includes `AUTONOMOUS` simulated trades |
| Settlement history | Demo guaranteed delivery after reset |

## 5. Allocation 110% vs 7.8% Target — Root Cause

1. `_current_weight` used cost basis / `total_equity` without mark-to-market NAV
2. Settlement rewrote equity without resizing OPEN positions
3. Demo seed created oversized OPEN trades
4. `autonomous_v2_enabled` default false → targets updated without execution trim

**Phase 5 fixes:** `portfolio_nav.py`, live weight recompute on API read, `allocation_integrity_monitor.py`

## 6. Market Intelligence Gaps

- Regime SIDEWAYS → 0.5 confidence (50% if shown as %)
- Macro neutral sentiment → risk score ~50
- Frontend mock confidence when NLP score ≈ 0
- No FRED/Reuters live API (RSS only) — provider architecture extensible in Phase 5

## 7. What Phase 5 Added

| Deliverable | Path |
|-------------|------|
| Real strategy validation | `backend/app/validation/real_strategy_validation.py` |
| Validated runs table | `validated_strategy_runs` |
| Paper trading snapshots | `paper_trading_validation_snapshots` |
| Allocation alerts | `allocation_integrity_alerts` |
| Global risk engine | `backend/app/engines/global_risk_engine.py` |
| Research Lab UI | `/research-lab` |
| Institutional fund API | `GET /api/funds/{id}/institutional` |
| Validated API | `/api/validated/*` |
| Provenance field | `data_provenance` on fund responses |

---

## 8. Recommendations (Remaining)

1. Refactor operational `validation_service` Sharpe/drawdown to equity-based returns (Phase 6 `performance_engine.py` available)
2. ~~Wire FRED / economic calendar providers~~ — FRED wired in Phase 6; set `FRED_API_KEY`
3. Enable `autonomous_v2_enabled` for paper-live validation period
4. Remove or label mock UI metrics (exchange success rate, task health)
5. Post-settlement forced de-leverage in `SettlementEngine`

**Addressed in Phase 5/6 stability pass:**
- Intelligence synthetic confidence scores → coverage-aware NO DATA display
- Allocation weight recompute at API read + integrity monitor
- Alpha evidence null-safe aggregation
- Global Risk Engine sentiment column fix (`timestamp`)
- Treasury client summary endpoint + reports staff portfolio access

See [PHASE5_ROADMAP.md](./PHASE5_ROADMAP.md) for Alpha 20% monthly evidence steps.
