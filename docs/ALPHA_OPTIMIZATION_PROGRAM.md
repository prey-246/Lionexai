# LionexAI Alpha Optimization & Strategy Improvement Program

**Principal Quant Research Program — Implementation Plan**

---

## Program Overview

| Phase | Name | Status | Deliverable |
|-------|------|--------|-------------|
| **1** | Root Cause Analysis | ✅ Complete | [PHASE1_ALPHA_DIAGNOSTIC.md](./PHASE1_ALPHA_DIAGNOSTIC.md) |
| **2** | Strategy Expansion | 🔄 Next | Independent strategy backtests → `validated_strategy_runs` |
| **3** | Strategy Ensemble | Planned | Weekly scoring + regime-aware capital allocation |
| **4** | Asset Universe Optimization | Planned | Per-asset metrics + correlation + remove list |
| **5** | Regime Engine v2 | Planned | 8-regime taxonomy + regime-specific allocations |
| **6** | Rebalancing Optimization | Planned | Grid: 1/3/7/14/30/regime-triggered days |
| **7** | Portfolio Construction | Planned | 6 methods compared per fund |
| **9** | Platform Regeneration | Planned | Best config → validated institutional history |

*Phase 8 not specified in requirements; walk-forward + Monte Carlo fold into Phase 9 selection.*

---

## Architecture

```
market_bars (Binance, yfinance)
        ↓
AlphaOptimizationEngine
  ├── StrategyMatrixRunner      → validated_strategy_runs
  ├── PortfolioMethodGrid       → validated_fund_runs (experiment)
  ├── EnsembleSimulator         → validated_fund_runs (experiment)
  ├── RebalanceGrid             → validated_fund_runs (experiment)
  └── ConfigSelector            → best config per fund
        ↓
ValidatedInstitutionalRegenerator (Phase 9)
  ├── LNX-PRESERVE-VALIDATED portfolios
  ├── Treasury / settlement / LNX from validated NAV
  └── Dashboards (VALIDATED_HISTORICAL primary)
```

**Storage:** All experiments in `validated_fund_runs` / `validated_strategy_runs` with `config` JSON. Demo tables untouched.

---

## Phase 2 — Strategy Expansion

**Strategies to implement/test:**

| Key | Status | Implementation |
|-----|--------|----------------|
| MOMENTUM | Exists | `alpha_strategies.MomentumStrategy` |
| TREND_FOLLOWING | Exists | `TrendFollowingStrategy` |
| VOL_BREAKOUT | Exists | `VolatilityBreakoutStrategy` |
| MEAN_REVERSION | Exists | `RsiMeanReversionStrategy` |
| CROSS_ASSET_ROTATION | Exists | Extend to multi-asset panel |
| RISK_PARITY | Exists | Portfolio-level in optimizer |
| RELATIVE_STRENGTH | **New** | Rank N-day return, top-K long |
| ADAPTIVE_REGIME_SWITCHING | **New** | Regime → strategy weight map |
| DYNAMIC_POSITION_SIZING | **New** | Kelly/vol-scaled units |
| VOLATILITY_TARGETING | **New** | Scale gross exposure to target vol |

Each: independent backtest per asset + fund-level overlay test.

---

## Phase 3 — Ensemble

Weekly loop:
1. Score each strategy on trailing 63-day OOS window (Sharpe, PF, win rate)
2. Softmax / rank-weight capital to top 3 strategies
3. Apply regime multiplier table (data-driven from Phase 5 backtests)
4. Decay weight of strategies with 4-week negative rolling Sharpe

---

## Phase 4 — Asset Universe

**Remove candidates (validated period):** ETH (Preserve), NDX, EURUSD  
**Keep / add:** XAU, WTI, SPX, BTC, SOL (Alpha only), GBPUSD (optional)

Output: `recommended_universe` per fund in config JSON.

---

## Phase 5 — Regime Engine v2

Expand to: `BULL_TREND`, `BEAR_TREND`, `SIDEWAYS`, `HIGH_VOL`, `LOW_VOL`, `INFLATIONARY`, `DEFLATIONARY`, `CRISIS`

Classify using: MA structure, vol percentile, drawdown, optional breakeven inflation proxy from stored macro.

---

## Phase 6 — Rebalancing Grid

Test per fund: `[1, 3, 7, 14, 30, "regime_change"]` × drift bands `[1%, 2%, 5%]`

Select by: max Sharpe subject to DD < 15% (or min DD if none pass).

---

## Phase 7 — Portfolio Construction

Compare:
1. Equal weight  
2. Inverse volatility (current)  
3. Risk parity  
4. Minimum variance (ledoit-wolf simplified)  
5. Maximum diversification (correlation penalty)  
6. Regime-aware dynamic (ensemble output)

---

## Phase 9 — Selection & Regeneration

**Selection score (risk-adjusted, not return-only):**

```
score = 0.35×Sharpe + 0.20×Sortino + 0.20×Calmar + 0.15×PF + 0.10×(1 - DD/100)
        - penalty if walk-forward OOS Sharpe < 0.5 × IS Sharpe
```

**Regenerate:**
- `LNX-PRESERVE-VALIDATED`, `LNX-BALANCE-VALIDATED`, `LNX-ALPHA-VALIDATED`
- Validated equity curves, trades, allocations, rebalances, settlements
- Treasury pools + LNX index from validated profit routing
- Update all dashboards (validated primary, demo toggle for sales)

**Final report:** [INSTITUTIONAL_PERFORMANCE_REPORT.md](./INSTITUTIONAL_PERFORMANCE_REPORT.md) (generated after Phase 9)

---

## CLI / API

```bash
# Full optimization program
PYTHONPATH=/code python scripts/run_alpha_optimization.py --phase all

# Individual phases
python scripts/run_alpha_optimization.py --phase strategy-matrix
python scripts/run_alpha_optimization.py --phase grid --fund ALPHA
python scripts/run_alpha_optimization.py --phase select-best
python scripts/run_alpha_optimization.py --phase regenerate
```

API: `POST /api/validated/optimization/run` (operator/admin)

---

## Timeline Estimate

| Phase | Effort |
|-------|--------|
| 2–3 | 2–3 days implementation + compute |
| 4–7 | 2 days + grid compute (~30 min in Docker) |
| 9 | 2–3 days regeneration + UI |

---

## Open Decisions (see user confirmation)

1. Sharpe > 1.5 on **all** funds — report gap if unreachable?  
2. Validated portfolios **alongside** or **replace** demo on client dashboard?  
3. Accept longer backfill (5yr) for walk-forward robustness?
