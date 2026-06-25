# Phase 1 — Alpha Optimization Root Cause Diagnostic

**Date:** June 2026  
**Scope:** Why validated historical backtests underperform; audit of engines vs. actual simulation path.

---

## Executive Summary

The validated backtest engine (`HistoricalFundSimulator`) **does not run alpha strategies at all**. It runs a **passive allocation model** (inverse-vol / regime-momentum weights) with **high cash floors**, **frequent rebalancing costs**, and **regime-driven de-risking** that kept portfolios 45–70% in cash during a period when **buy-and-hold crypto rallied strongly**.

Poor fund results are therefore **structural**, not a metrics bug:

| Fund | Core problem |
|------|----------------|
| **PRESERVE** | ~70% average cash + inverse-vol underweights winners; ETH drag |
| **BALANCE** | ~46% cash + inverse-vol; flat composite |
| **ALPHA** | Best of three but **2.4% NAV lost to trade costs** (85 rebalances / 3-day); no tactical signals |

---

## 1. Simulation Path vs. Live Stack

| Component | Live (`AllocationEngine` / `PortfolioManager`) | Validated backtest |
|-----------|-----------------------------------------------|-------------------|
| Allocation weights | inverse_vol / regime_momentum | ✅ Mirrored |
| Alpha strategies (`MOMENTUM`, etc.) | Registered in `FundStrategyUniverse` | ❌ **Not used** |
| `RiskEngine` pre-trade gates | Active | ❌ Not simulated |
| `AutonomousManager` execution | Exchange/simulated fills | ❌ Not simulated |
| `StrategyOptimizer` scores | Demo trade PnL | ❌ Not connected to backtest |
| Treasury / settlement | Weekly guaranteed yield | ❌ Not in NAV path |
| Rebalance | 7d (Preserve/Balance), 3d (Alpha) | ✅ Same |

**Conclusion:** Reported fund metrics measure **static allocation policy**, not the **alpha strategy stack** the product describes.

---

## 2. Fund-by-Fund Diagnosis

### PRESERVE (CAGR -7.05%, Sharpe -0.56, PF 0.89)

**Policy:** `inverse_vol`, 40% cash floor, 7-day rebalance, 4 assets (BTC, ETH, XAU, XAG).

| Factor | Evidence | Impact |
|--------|----------|--------|
| **Cash drag** | Avg **70.3%** cash at rebalance (40% base + RISK_OFF +15% + CRISIS up to 60%) | ~70% of capital earns 0% while crypto/metals move |
| **Inverse-vol trap** | Weights toward low-vol names; in stress vol clusters → stays in declining assets | Underweights BTC/SOL rally |
| **ETH exposure** | ETH buy-hold **-3.13%** over period | Drag on preserve basket |
| **Regime mix** | 20 SIDEWAYS, 13 BEAR, 3 CRISIS (of 36 rebalances) | Persistent de-risking |
| **Trade costs** | $4,144 (0.41% of NAV) | Minor vs cash drag |
| **Win rate vs PF** | 57% win rate but PF 0.89 | Wins smaller than losses — typical of whipsaw rebalancing |

**Why Preserve loses:** Capital is mostly in cash during a period when **BTC +125%**, **SOL +216%** (full history) but the fund held ~30% invested in a mix that included negative ETH.

---

### BALANCE (CAGR -2.01%, Sharpe -0.22, PF 0.99)

**Policy:** `inverse_vol`, 20% cash floor, 7-day rebalance, 6 assets.

| Factor | Evidence | Impact |
|--------|----------|--------|
| **Cash drag** | Avg **45.6%** cash at rebalance | Half the book inactive |
| **Diversification illusion** | BTC/ETH/SOL correlation **0.84–0.89** | Not true diversification in crypto sleeve |
| **NDX/SPX** | SPX +5.2%, NDX **-8.1%** buy-hold | Index mix added noise |
| **Trade costs** | $6,251 (0.63%) | Moderate |
| **Yield delivery** | **0%** weeks meeting 2.5% target | Expected — simulation doesn't guarantee yield |

**Why Balance is flat:** Diversified passive weights + high effective cash ≈ money-market return minus costs.

---

### ALPHA (CAGR +6.88%, Sharpe 0.76, PF 1.36, monthly 0.61%)

**Policy:** `regime_momentum`, 5% cash floor, **3-day rebalance**, 10 assets, max 8 positions.

| Factor | Evidence | Impact |
|--------|----------|--------|
| **Trade costs** | **$24,164 (2.42% of NAV)**, 85 rebalances | Major alpha erosion |
| **No strategy signals** | Same passive weight engine as others | Misses tactical momentum/breakout edge |
| **Regime_momentum helps** | Lower cash (18.6% avg), momentum tilt | Why Alpha beats Preserve/Balance |
| **20% monthly target** | Actual **0.61%** avg monthly | **NOT_SUPPORTED** — honest gap |
| **Asset drag** | NDX -8%, EUR -1.8% in universe | Full universe dilutes |

**Why Alpha only 0.61% monthly:** Positive but fee-like rebalance drag + no actual alpha strategies + targets are marketing-scale (21.65% monthly) vs achievable systematic returns.

---

## 3. Asset Universe Analysis (Buy-and-Hold, Full Available History)

| Asset | Total Return | CAGR | Sharpe | Max DD | Notes |
|-------|-------------|------|--------|--------|-------|
| BTC/USDT | +125.7% | 34.7% | 0.71 | 51.2% | Strong trend, high vol |
| SOL/USDT | +216.7% | 52.4% | 0.76 | 76.3% | Best return, worst DD |
| ETH/USDT | -3.1% | -1.2% | 0.26 | 67.5% | **Remove candidate** for Preserve |
| XAUUSD | +8.7% | 9.1% | **2.05** | 55.4% | Best risk-adj metal |
| XAGUSD | +9.6% | 10.0% | **2.29** | 72.0% | High DD |
| WTIUSD | +15.5% | 16.2% | 1.14 | 39.8% | Energy diversifier |
| SPX | +5.2% | 5.4% | 0.61 | 21.9% | Lower vol equity |
| NDX | -8.1% | -8.4% | 1.42* | 44.7% | **Remove candidate** |
| EURUSD | -1.8% | -1.8% | 0.13 | 9.1% | FX drag |
| GBPUSD | +1.5% | 1.6% | 0.17 | 12.2% | Weak |

*Sortino-like; low vol FX/metals can show odd Sharpe on short samples.

**Correlation clusters:**
- Crypto block: BTC–ETH–SOL **0.84+**
- Metals: XAU–XAG **0.83**
- Equity: SPX–NDX **0.93**
- WTI negatively correlated to metals (~-0.4)

---

## 4. Engine-Specific Findings

### AllocationEngine
- Uses **point-in-time** vol/momentum but live DB regimes; backtest uses `classify_series` ✅
- **Inverse vol in downtrends** allocates to “low vol” assets that are still falling (vol clustering)
- **BEAR weight ×0.4, CRISIS ×0.1** — correct defensively but **too late** (MA-based lag)
- **Cash floor escalation** (+15% RISK_OFF, 60% CRISIS) — primary Preserve killer

### RegimeEngine
- Only 4 regimes: BULL / BEAR / SIDEWAYS / CRISIS
- Backtest period classified **mostly SIDEWAYS/BEAR** on BTC proxy → persistent defensive posture
- No HIGH_VOL / LOW_VOL / inflationary distinction → cannot rotate tactically

### RiskEngine
- Not in backtest path; live would block some buys on sentiment — irrelevant to historical sim

### AutonomousManager / StrategyOptimizer
- Optimizer scores **demo trades**, not validated runs → **feedback loop disconnected**
- Strategies exist in `STRATEGY_MAP` but **never drive fund-level weights** in sim

### Rebalancing
- Fixed calendar + 2% drift band
- Alpha 3-day → **85 rebalances / 241 days** → cost dominates edge
- No regime-triggered-only mode tested yet

### Treasury routing
- Not applied in validated NAV — correct for strategy proof; Phase 9 will simulate settlements separately

---

## 5. Root Cause Summary (Ranked)

1. **Alpha strategies not wired** into fund backtest (largest gap vs. product intent)
2. **Excessive cash** from floor + regime escalation (Preserve/Balance)
3. **Inverse-vol weighting** in trending markets underweights winners
4. **Rebalance frequency / costs** (Alpha 2.4% drag)
5. **Suboptimal asset selection** (ETH, NDX, EURUSD drag; crypto correlation ignored)
6. **Single allocation method** — no ensemble or regime-specific strategy mix
7. **Short aligned sample** (~11 months) — limits statistical confidence

---

## 6. Improvement Hypotheses (For Phases 2–9)

| Hypothesis | Expected impact |
|------------|-----------------|
| Wire tactical strategies (momentum, trend, breakout) as **weight multipliers** | ↑ Alpha CAGR, ↑ Sharpe |
| **Volatility targeting** (scale exposure to 10–15% portfolio vol) | ↓ DD, ↑ Sharpe |
| **Ensemble** weekly strategy scoring | Smoother equity, ↑ PF |
| Reduce Preserve cash floor to **15–25%** + vol-target | Fix negative CAGR |
| Alpha rebalance **7–14 days** not 3 | ↓ costs ~1–2% NAV |
| Drop ETH/NDX/EURUSD from Preserve; add WTI/SPX | ↑ risk-adjusted |
| **Relative strength rotation** among uncorrelated clusters | ↑ Balance/Alpha |
| Expanded regimes + regime-specific ensembles | ↑ stability |

---

## 7. Success Criteria — Honest Assessment

Targets requested:
- Sharpe > 1.5, PF > 1.5, Max DD < 15%, positive CAGR **all funds**

On **~11 months** of real data with **no overfitting**, achieving Sharpe > 1.5 on **all three** funds simultaneously is **unlikely** without:
- Longer history (3–5 years walk-forward)
- Accepting higher DD on Alpha
- Or materially different mandates (e.g. Preserve in mostly cash + gold trend only)

**We will optimize honestly** and report gaps if targets are not achievable on available data.

---

## 8. Next Steps

See [ALPHA_OPTIMIZATION_PROGRAM.md](./ALPHA_OPTIMIZATION_PROGRAM.md) for phased implementation.

Phase 2 begins with `AlphaOptimizationEngine` — strategy matrix, portfolio method grid, ensemble, and stored experiments separate from demo data.
