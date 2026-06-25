# Historical Validation Audit Report

**Date:** June 2026  
**Scope:** Replace demo/seeded/simulated performance displays with `VALIDATED_HISTORICAL` results from `market_bars` backtests.

---

## Executive Summary

The platform previously displayed **seeded demo ledger** performance (from `reset_institutional_demo.py`) as "realized" returns on Fund Performance, Validation, Portfolio, LNX, and Treasury surfaces. This audit:

1. Identified every demo performance data path
2. Built a **fund-level historical backtest engine** on real OHLCV
3. Stored results in **`validated_fund_runs`** (separate from demo tables)
4. Updated Fund Performance and related APIs/UI to show **validated historical metrics only**
5. Ran backtests for **PRESERVE, BALANCE, and ALPHA** — reporting **actual** results (no inflation)

---

## What Was Demo (No Longer Shown as Performance)

| Surface | Previous source | Status |
|---------|-----------------|--------|
| Fund Performance "Realized" | `equity_curves` + seeded `trades` (`exchange=simulated`) | **Replaced** with `validated_fund_runs` |
| Fund list actual returns | `compute_fund_actuals()` on demo ledger | **Replaced** with validated backtest |
| Institutional fund analytics | `PerformanceEngine` over demo portfolios | **Replaced** with validated backtest |
| Alpha Evidence paper-live | Demo AUTONOMOUS trades | **Excluded** when provenance is DEMO |
| Validation dashboard | `trade_source=AUTONOMOUS` including demo simulated | **Labeled** operational; link to Fund Performance |
| Portfolio detail stats | Demo trades/equity curves | **Banner** — operational ledger only |
| LNX index growth / strategy performance | Demo snapshots + seeded settlements | **Banner** — operational index only |
| Treasury growth % | Demo pool balances + seeded routing | Operational only (not strategy validation) |
| Strategy analytics page | Demo AUTONOMOUS trade PnL | Unchanged — use Research Lab / Fund Performance |
| Simulator page | Hardcoded scenario stats | Projection only (unchanged) |

Demo data **remains in the database** for operational demos but is **not displayed** as fund strategy performance.

---

## What Is Now Historical-Data Validated

| Component | Path | Provenance |
|-----------|------|------------|
| Fund backtest engine | `backend/app/validation/historical_fund_simulator.py` | VALIDATED_HISTORICAL |
| Storage | `validated_fund_runs` table | VALIDATED_HISTORICAL |
| Service layer | `backend/app/services/validated_fund_service.py` | VALIDATED_HISTORICAL |
| APIs | `POST /api/validated/fund/run`, `/fund/run-all`, `GET /fund/latest/{id}` | VALIDATED_HISTORICAL |
| Fund Performance UI | `/fund-performance` | VALIDATED_HISTORICAL |
| Alpha Evidence | `fund_backtest` block in evidence payload | VALIDATED_HISTORICAL |
| CLI | `python scripts/run_historical_fund_backtests.py --backfill` | VALIDATED_HISTORICAL |

### Simulation methodology

- **Data:** `market_bars` daily OHLCV (Binance crypto, yfinance metals/FX/indices)
- **Logic:** Point-in-time `RegimeEngine.classify_series`, inverse-vol / regime-momentum allocation (mirrors `AllocationEngine`), periodic rebalance per fund `rebalance_freq_days`
- **Costs:** 0.1% commission + 0.1% slippage on rebalance trades
- **Metrics:** CAGR, annualized return, avg monthly/weekly return, Sharpe, Sortino, Calmar, max drawdown, win rate, profit factor, volatility, yield delivery % (weeks meeting target vs actual weekly returns)
- **Never writes to:** `equity_curves`, `trades`, `portfolios.total_equity`

---

## Fund Backtest Results (Actual — Not Inflated)

Run: `docker exec nexa_backend_prod bash -c "cd /code && PYTHONPATH=/code python scripts/run_historical_fund_backtests.py --backfill --limit 2000"`

| Fund | Period | CAGR | Avg Monthly | Max DD | Sharpe | Meets 20% Monthly Target |
|------|--------|------|-------------|--------|--------|--------------------------|
| **PRESERVE** | 2025-07-09 → 2026-06-24 | **-7.05%** | **-0.60%** | 15.33% | -0.56 | N/A |
| **BALANCE** | 2025-07-10 → 2026-06-24 | **-2.01%** | **-0.15%** | 7.08% | -0.22 | N/A |
| **ALPHA** | 2025-07-10 → 2026-06-24 | **+6.88%** | **+0.61%** | 7.89% | 0.76 | **NO** (target 20%+) |

### Alpha fund — honest conclusion

On available historical daily bars with multi-asset allocation backtest, **Alpha does NOT achieve 20% monthly compounded returns**. Actual average monthly return: **0.61%**. This is reported without smoothing or fabrication.

---

## Limitations & Missing Data

1. **History depth:** Current backfill provides ~350–2000 bars per symbol depending on provider; aligned panel used ~11 months (Jul 2025 – Jun 2026) due to inner-join across fund universes. Run `run_backfill(2000)` and re-backtest for longer history when more bars exist.

2. **Mock provider:** If yfinance/Binance fails, `MockProvider` generates synthetic OHLCV — backtests would still be labeled VALIDATED_HISTORICAL but would not be real market data. Check `data_coverage.provider` in run results.

3. **No live autonomous replay:** Historical simulator uses allocation logic, not full `PortfolioManager` + exchange execution lifecycle. Strategy signal overlays (per `FundStrategyUniverse`) not yet applied in v1.

4. **Treasury / LNX:** Cannot be historically validated without simulating full settlement economics chain; remain operational metrics with UI disclaimers.

5. **Validation dashboard:** Still shows operational paper-trading snapshots; use Fund Performance for strategy validation.

6. **Single-asset Research Lab runs:** Still available separately in `validated_strategy_runs` for strategy×symbol research.

---

## How to Reproduce

```bash
# Migrate
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head

# Backfill + run all fund backtests
docker exec nexa_backend_prod bash -c "cd /code && PYTHONPATH=/code python scripts/run_historical_fund_backtests.py --backfill --limit 2000"

# API (operator/admin)
POST /api/validated/fund/run-all
GET  /api/validated/fund/latest/ALPHA

# Rebuild frontend after UI changes
docker compose -f docker-compose.prod.yml build frontend
docker compose -f docker-compose.prod.yml up -d frontend
```

---

## Provenance Model (Enforced)

| Label | Meaning | Shown on Fund Performance? |
|-------|---------|------------------------------|
| `VALIDATED_HISTORICAL` | Fund backtest on `market_bars` | **Yes (primary)** |
| `DEMO` | Seeded institutional demo ledger | **No** (hidden from performance UI) |
| `PAPER_LIVE` | Live autonomous non-simulated fills | Future — when `autonomous_v2` runs without demo reset |
| `UNVALIDATED` | No backtest run yet | Shown with prompt to run backtests |

---

## Files Changed

- `backend/app/models/domain.py` — `ValidatedFundRun` model
- `backend/app/validation/historical_fund_simulator.py` — backtest engine
- `backend/app/services/validated_fund_service.py` — display metrics service
- `backend/app/services/fund_performance_service.py` — institutional analytics uses validated
- `backend/app/services/market_data_service.py` — `get_bars_panel()`
- `backend/app/api/routes/validated_performance.py` — fund backtest APIs
- `backend/app/api/routes/funds.py` — list funds uses validated display
- `backend/app/analytics/performance_engine.py` — fund_analytics prefers validated
- `backend/app/services/alpha_evidence_service.py` — fund backtest evidence
- `backend/scripts/run_historical_fund_backtests.py` — CLI runner
- `frontend/src/app/fund-performance/page.tsx` — validated-only UI
- `frontend/src/app/validation/page.tsx`, `lnx/page.tsx`, `portfolios/[id]/page.tsx` — disclaimers
