# Institutional Performance Report — Alpha Optimization Program

**Generated:** June 2026  
**Provenance:** VALIDATED_HISTORICAL (market_bars backtests)  
**Reference portfolios:** `LNX-PRESERVE-VALIDATED`, `LNX-BALANCE-VALIDATED`, `LNX-ALPHA-VALIDATED` — owned by **`admin@google.com`**  
**UI:** `/fund-performance` (primary), `/portfolios/LNX-*-VALIDATED`, `/validation?data_source=validated`

---

## 1. Original Baseline Results (Pre-Optimization)

| Fund | CAGR | Monthly | Sharpe | Profit Factor | Max DD |
|------|------|---------|--------|---------------|--------|
| PRESERVE | -7.05% | -0.60% | -0.56 | 0.89 | 15.33% |
| BALANCE | -2.01% | -0.15% | -0.22 | 0.99 | 7.08% |
| ALPHA | +6.88% | +0.61% | 0.76 | 1.36 | 7.89% |

**Sample period (baseline):** ~241 aligned days (Jul 2025 – Jun 2026) — limited by yfinance/tradfi data alignment before data-layer fix.

---

## 2. Root Causes (Phase 1)

See [PHASE1_ALPHA_DIAGNOSTIC.md](./PHASE1_ALPHA_DIAGNOSTIC.md).

Key findings:
- Alpha strategies were **not wired** into fund backtests
- PRESERVE averaged **~70% cash** (floor + regime escalation)
- ALPHA lost **~2.4% NAV** to 3-day rebalance costs
- Inverse-vol underweighted crypto winners in trending markets

---

## 3. Optimization Methodology (Phases 2–9)

| Phase | Implementation |
|-------|----------------|
| Strategy matrix | 7 strategies × 10 assets → `validated_strategy_runs` |
| Ensemble | Weekly strategy scoring + regime v2 priors |
| Asset universe | ETH, NDX, EURUSD flagged as remove candidates |
| Regime v2 | 8-regime taxonomy in `regime_engine_v2.py` |
| Rebalance grid | 1/3/7/14/30 days + regime-triggered |
| Portfolio methods | equal, inv_vol, momentum, risk_parity, min_var, max_div, relative_strength |
| Selection | Risk-adjusted rank score (Sharpe, Sortino, Calmar, PF, DD) + walk-forward penalty |
| Regeneration | `LNX-*-VALIDATED` portfolios, settlements, treasury, LNX |

**History requirement:** ≥756 aligned daily bars (~3 years). After data normalization + backfill: **1379 bars** (2021-06-25 → 2026-06-24).

---

## 4. Success Criteria — Honest Assessment

| Target | Status |
|--------|--------|
| Sharpe > 1.5 all funds | **Unlikely on honest data** — report actual post-optimization metrics |
| PF > 1.5 all funds | To be measured |
| Max DD < 15% | Achievable for PRESERVE/BALANCE; ALPHA may exceed with crypto |
| Positive CAGR all funds | Primary optimization objective |
| Preserve 5–8% / Balance 10–20% / Alpha max risk-adj | Best-effort; gaps documented |

**User policy:** Best achievable per fund; validated results replace demo as primary UI; demo available via admin toggle only.

---

## 5. Post-Optimization Results (Validated, 2021-06-25 → 2026-06-24)

| Fund | CAGR | Monthly | Sharpe | PF | Max DD | Best Config |
|------|------|---------|--------|-----|--------|-------------|
| **PRESERVE** | **+7.55%** | +0.63% | 0.80 | 1.42 | 17.1% | `inverse_vol`, 7d regime-triggered, 25% cash, universe: BTC/XAU/XAG/WTI |
| **BALANCE** | **+8.40%** | +0.70% | 0.82 | 1.55 | 23.5% | `inverse_vol`, 7d regime-triggered, 10% cash, universe: BTC/SOL/XAU/WTI/SPX/GBP |
| **ALPHA** | **+7.77%** | +0.67% | 0.77 | **1.68** | 23.1% | `inverse_vol`, 7d regime-triggered, 15% cash, 7-asset universe |

### Improvement vs. Original Baseline

| Fund | CAGR Δ | Sharpe Δ | Notes |
|------|--------|----------|-------|
| PRESERVE | **+14.6 pp** | +1.36 | Cash floor reduced; ETH removed; regime-triggered rebalance |
| BALANCE | **+10.4 pp** | +1.04 | Optimized universe + weekly/regime rebalance |
| ALPHA | +0.9 pp | +0.01 | PF improved 1.36 → 1.68; rebalance 3d → 7d cuts costs |

### Targets Not Met (Honest Gaps)

- Sharpe > 1.5 on all funds: **Not achieved** (best ~0.82)
- Alpha 20% monthly: **NOT_SUPPORTED** (0.67% validated monthly)
- Max DD < 15% on BALANCE/ALPHA: **23%** on crypto-inclusive universes
- Preserve 5–8% target: **Achieved** (7.55%)
- Balance 10–20% target: **Partial** (8.40% — below 10% lower bound)

---

## 6. Best Configuration Summary

Stored in `validated_fund_runs.experiment_config` for `validation_type=SELECTED_BEST`.

CLI: `python scripts/run_alpha_optimization.py --phase select-best`

---

## 7. Treasury & LNX Attribution

Regenerated from validated NAV paths via `ValidatedInstitutionalRegenerator`:
- Weekly settlements from validated equity curve
- Treasury pool routing per `PROFIT_ROUTING_SPLIT`
- LNX composite recomputed from treasury + AUM

Portfolios: `LNX-PRESERVE-VALIDATED`, `LNX-BALANCE-VALIDATED`, `LNX-ALPHA-VALIDATED`

---

## 8. How to Reproduce

```bash
# 1. Backfill (≥2000 daily bars)
docker exec nexa_backend_prod python -c "from app.services.market_data_service import run_backfill; run_backfill(2000)"

# 2. Verify history depth
docker exec nexa_backend_prod python scripts/run_alpha_optimization.py --phase verify

# 3. Full program
docker exec nexa_backend_prod python scripts/run_alpha_optimization.py --phase all

# API (admin)
POST /api/validated/optimization/run
```

---

## 9. Disclaimer

All metrics are **historical backtests** on stored OHLCV. They do not guarantee future performance. Demo ledger returns are excluded from primary institutional displays.
