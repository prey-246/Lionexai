# Treasury Verification Engine — Root Cause Audit

**Date:** June 2026  
**Scope:** Operational treasury accounting, solvency score, Research Lab strategy metrics  
**Verdict:** Treasury NAV is **materially inflated** (~$125M ledger gap). Solvency score **54/100 is mathematically correct given contaminated data**, but **misleading** because validated historical backtests were mixed into operational accounting.

---

## A. Executive Summary

| Finding | Severity | Classification |
|---------|----------|----------------|
| `$65M–$128M` Treasury NAV vs ~$3M ledger-implied NAV | **CRITICAL** | Accounting bug (D + validated contamination) |
| Routing integrity 27.58% | **HIGH** | Measurement bug — compares operational + validated settlements to operational txs only |
| Settlement coverage 19.49% | **HIGH** | Measurement bug — validated synthetic settlements mark `uncovered > 0` |
| Pool allocation drift (GROWTH, INSURANCE, LNX_INDEX) | **MEDIUM** | Consequence of inflation + no auto-rebalance + INSURANCE excluded from profit routing |
| Research Lab Sharpe `-4.6e16` | **HIGH** | Numeric bug — division by floating-point noise when returns are flat |
| Yield sweep ~$432k on validated trade PnL | **MEDIUM** | Provenance leak — validated synthetic trades counted in operational sweep |

**Bottom line:** The treasury is **not** legitimately funded at $65M+. Real operational NAV from the immutable transaction ledger is approximately **$3.05M** (baseline $2.375M + $670k net flows). The ~$125M excess is caused primarily by `ValidatedInstitutionalRegenerator._recompute_treasury_from_validated()` applying `pool.balance += total_routed * percentage` without dividing by 100, effectively multiplying every validated excess dollar by **100** across pools. This ran **6 times** during regeneration.

Validated historical backtests (`VALIDATED_HISTORICAL`) must **never** mutate `treasury_pools.balance`. They are a separate provenance plane.

---

## B. Root Cause Analysis

### B.1 Primary: Validated treasury inflation bug

**File:** `backend/app/validation/validated_institutional_regenerator.py` (removed in fix)

```python
# BUG (removed):
for pool_id, share in PROFIT_ROUTING_SPLIT.items():  # share = 40.0, 25.0, ...
    pool.balance = (pool.balance or 0) + total_routed * share  # missing / 100.0
```

`PROFIT_ROUTING_SPLIT` values are **percentages** (40, 25, 15, 15, 5). Correct settlement routing uses:

```python
share = amount * (pct / 100.0)  # settlement_engine.py, reset_institutional_demo.py
```

**Effect per regeneration cycle:**

| Validated excess routed | Bug adds to pools | Correct add |
|-------------------------|-------------------|-------------|
| $625,748 | $625,748 × **100** = **$62,574,800** | $625,748 |

**Evidence (live DB audit):**

| Metric | Value |
|--------|-------|
| Stored NAV | $128,195,406 |
| Ledger-implied NAV (baseline + txs) | $3,045,770 |
| **Balance gap** | **$125,149,636** |
| Validated `excess_routed` (no matching txs) | $625,748 |
| `VALIDATED_REGENERATE` audit events | 6 |

Validated settlements (`stl_val_*`) record `excess_routed` in `client_settlements` but **never create** `treasury_transactions` — only the buggy balance mutation ran.

### B.2 Secondary: Yield sweep provenance leak

**File:** `backend/scripts/yield_sweep.py`

Hourly sweep credits YIELD pool with 10% of **all** closed winning `trades.pnl`, including `trade_source = VALIDATED_HISTORICAL` synthetic rebalance trades ($3.26M winning PnL → ~$326k+ of the $432k swept).

Validated trades are not operational profit.

### B.3 Tertiary: Verification engine mixes provenance planes

**File:** `backend/app/services/treasury_verification_engine.py` (fixed)

Original logic:

- `settlement_coverage` = count(`uncovered <= 0`) / **all** settlements
- `routing_integrity` = compare **all** `excess_routed` vs **operational** `PROFIT_ROUTING` txs

Validated settlements (`786` rows):

- `727` have `uncovered > 0` (backtest weeks below guaranteed weekly target)
- Still `status = SETTLED` — synthetic metadata, not real treasury obligation

This drove coverage to **19.49%** = (903 − 727) / 903... actually covered = 176, 176/903 = 19.49%. ✓

Routing: $864,004 settlements vs $238,256 txs → integrity **27.58%**. ✓

### B.4 Pool drift — not a separate bug

Target allocations (seed):

| Pool | Target % | Notes |
|------|----------|-------|
| YIELD | 40% (DB shows 50% — manual/config drift) | Receives 40% of profit routing + yield sweep |
| RESERVE | 20% | 15% routing |
| GROWTH | 15% | 25% routing → naturally overweight when routing works |
| OPERATIONS | 10% | 15% routing |
| LNX_INDEX | 10% | 5% routing → underweight |
| INSURANCE | 5% | **0% routing** — never receives `PROFIT_ROUTING` |

No automatic pool rebalancer exists. Drift is expected after asymmetric routing splits vs display targets.

### B.5 Research Lab Sharpe overflow

**File:** `backend/app/validation/real_strategy_validation.py` (fixed)

When strategy produces **flat equity** (e.g. RELATIVE_STRENGTH on EURUSD — no positions):

- `rets.std()` = 0.0 exactly
- `excess.std()` = **2.7×10⁻²⁰** (float noise)
- Condition `excess.std() > 0` passes → Sharpe = `-0.0001587 / 2.7e-20 × √252` ≈ **−9.3×10¹⁶**

79 of 81 persisted strategy runs affected (alpha optimization matrix).

---

## C. Mathematical Verification

### C.1 Treasury NAV

```
NAV = Σ treasury_pools.balance
```

**Stored (contaminated):** $128,195,406.14

**Legitimate (ledger reconstruction):**

```
implied_balance[pool] = OPERATIONAL_BASELINE[pool] + Σ treasury_transactions.amount WHERE pool_pk_id = pool
```

| Pool | Baseline | Net TX | Implied Balance | Stored | Gap |
|------|----------|--------|-----------------|--------|-----|
| RESERVE | $1,000,000 | $35,738 | $1,035,738 | $19,808,184 | $18,772,446 |
| YIELD | $250,000 | $527,817 | $777,817 | $50,837,671 | $50,059,854 |
| GROWTH | $400,000 | $59,564 | $459,564 | $31,746,973 | $31,287,409 |
| OPERATIONS | $150,000 | $35,738 | $185,738 | $18,958,184 | $18,772,446 |
| INSURANCE | $500,000 | $0 | $500,000 | $500,000 | $0 |
| LNX_INDEX | $75,000 | $11,913 | $86,913 | $6,344,395 | $6,257,482 |
| **TOTAL** | **$2,375,000** | **$670,770** | **$3,045,770** | **$128,195,406** | **$125,149,636** |

**Transaction summary:**

| Type | Net Amount | Count |
|------|------------|-------|
| PROFIT_ROUTING | $238,256 | 585 |
| YIELD_SWEEP | $432,514 | 2 |
| **Total net** | **$670,770** | |

**Why ~$106k “yield” vs $65M NAV:** Displayed yield (~$106k) reflects sweep + routing on **real demo autonomous activity**. NAV inflation came from the **validated regenerator bug** (~$62.5M per regeneration cycle), not from yield generation.

### C.2 Solvency score (original formula)

**File:** `treasury_verification_engine._solvency_score`

```
score = 40
      + min(20, reserve_ratio_pct)
      + settlement_coverage_pct × 0.2
      + routing_integrity_pct × 0.15
      + min(10, yield_pool/nav × 100)
      − issue_count × 5
```

**Manual recalculation (contaminated data, 4 issues):**

| Component | Value | Contribution |
|-----------|-------|--------------|
| Base | | 40.00 |
| Reserve ratio (15.45%) | min(20, 15.45) | +15.45 |
| Settlement coverage (19.49%) | × 0.2 | +3.90 |
| Routing integrity (27.58%) | × 0.15 | +4.14 |
| Yield weight | min(10, 39.66) | +10.00 |
| Issue penalty (4 × 5) | | −20.00 |
| **Total** | | **53.49** ✓ |

Score **54/100 is arithmetically correct** for the flawed input set.

### C.3 Post-reconciliation expected score (operational-only)

After `reconcile_treasury_ledger.py --confirm` and verification engine fix:

| Component | Operational value | Contribution |
|-----------|-------------------|--------------|
| NAV | ~$3,045,770 | |
| Reserve ratio | 34.0% | +20.00 |
| Settlement coverage (117 demo, 0 uncovered) | 100% | +20.00 |
| Routing integrity | 100% | +15.00 |
| Yield pool weight | 25.5% → capped | +10.00 |
| Issues | ~2 (validated info + pool drift) | −10.00 |
| **Expected score** | | **~85–90 (HEALTHY/WATCH)** |

---

## D. Reconciliation Tables

### D.1 Settlement routing — operational vs validated

| Source | Count | Sum excess_routed | Treasury TX created? |
|--------|-------|-------------------|----------------------|
| Demo (`stl_*`, not `stl_val_*`) | 117 | $238,256.00 | Yes — 585 PROFIT_ROUTING rows |
| Validated (`stl_val_*`) | 786 | $625,748.18 | **No** — balance mutation only (bug) |
| **Total** | **903** | **$864,004.18** | **$238,256.00** |

### D.2 Demo settlement → pool routing (sample logic)

Each demo settlement with excess `E` routes:

| Pool | % | Amount |
|------|---|--------|
| YIELD | 40% | 0.40 × E |
| GROWTH | 25% | 0.25 × E |
| RESERVE | 15% | 0.15 × E |
| OPERATIONS | 15% | 0.15 × E |
| LNX_INDEX | 5% | 0.05 × E |

9 portfolios × 13 weeks ≈ 117 settlements; excess always positive in seed → all SETTLED, uncovered = 0.

### D.3 Provenance separation matrix

| Data type | Touches treasury_pools? | Should? |
|-----------|-------------------------|---------|
| Demo settlements + PROFIT_ROUTING txs | Yes | Yes |
| YIELD_SWEEP (autonomous wins) | Yes | Yes (autonomous only after fix) |
| Validated fund backtests (`validated_fund_runs`) | **Yes (bug)** | **No** |
| Validated settlements (`stl_val_*`) | Metadata only | Audit display only |
| Validated strategy runs | No | No |
| Paper/live validation snapshots | No | No |

---

## E. Required Code Changes (implemented)

| File | Change |
|------|--------|
| `validated_institutional_regenerator.py` | **Removed** `_recompute_treasury_from_validated` — validated runs never mutate pools |
| `treasury_verification_engine.py` | Exclude `stl_val_*` from coverage/routing; add ledger reconciliation; stress tests exclude `-VALIDATED` AUM |
| `real_strategy_validation.py` | Sharpe/Sortino numeric floor (`1e-12`); clamp to ±99.99 |
| `yield_sweep.py` | Exclude `trade_source = VALIDATED_HISTORICAL` |
| `scripts/reconcile_treasury_ledger.py` | **New** — rebuild balances from baseline + txs |

### Optional follow-ups

| Item | Priority |
|------|----------|
| Sanitize persisted `validated_strategy_runs` metrics (SQL update or re-run matrix) | Medium |
| Align YIELD `target_allocation_pct` (50% in DB vs 40% in seed) | Low |
| Add `provenance` column to `client_settlements` | Low |
| Auto-rebalance pools to targets (product decision) | Future |

---

## F. Database Changes

**No schema migration required** for fixes. Operational recovery:

```bash
# 1. Preview
docker compose -f docker-compose.prod.yml exec backend python scripts/reconcile_treasury_ledger.py --dry-run

# 2. Apply (preserves all transactions and settlements)
docker compose -f docker-compose.prod.yml exec backend python scripts/reconcile_treasury_ledger.py --confirm

# 3. Re-verify
docker compose -f docker-compose.prod.yml exec backend python -c "
from app.core.database import SessionLocal
from app.services.treasury_verification_engine import TreasuryVerificationEngine
r = TreasuryVerificationEngine(SessionLocal()).verify()
print(r.solvency_score, r.status, r.routing_integrity_pct, r.settlement_coverage_pct)
for i in r.issues: print(' ', i)
"
```

Optional cleanup of bad strategy metrics:

```sql
-- Mark overflow runs invalid (operator review before delete)
UPDATE validated_strategy_runs
SET metrics = metrics || '{"sanitized": true, "sharpe_ratio": 0}'::jsonb
WHERE ABS((metrics->>'sharpe_ratio')::float) > 1000;
```

---

## G. Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Inflated NAV displayed to executives/clients | **Critical** — false sense of solvency | Reconcile ledger; label LNX/treasury as OPERATIONAL_LEDGER |
| Validated/regenerator re-run without fix | Would re-inflate | Code fix prevents mutation |
| Coverage/routing metrics on mixed data | **High** — false AT_RISK | Verification engine provenance split |
| Strategy rank scores from overflow Sharpe | **Medium** — bad optimization picks | Numeric fix + sanitize persisted rows |
| INSURANCE pool never funded by routing | **Low** — design gap | Document; optional routing split update |

---

## H. Post-Fix Expected Solvency Score

| Scenario | Score | Status |
|----------|-------|--------|
| Current contaminated DB | **53.5** | AT_RISK (correct given bad data) |
| After ledger reconcile + code fixes | **~85–90** | HEALTHY / WATCH |
| Legitimate operational NAV | **~$3.05M** | Not $65M |

---

## I. Validation Checklist

- [ ] Run `reconcile_treasury_ledger.py --dry-run` — confirm implied NAV ~$3.05M
- [ ] Apply `--confirm` — pool balances match ledger
- [ ] Treasury verification: routing integrity **100%**, settlement coverage **100%** (operational)
- [ ] Re-run `ValidatedInstitutionalRegenerator.regenerate_all()` — NAV **unchanged**
- [ ] Run strategy backtest on EURUSD/RELATIVE_STRENGTH — Sharpe **0.00**, not overflow
- [ ] Yield sweep with only validated trades — **$0** swept
- [ ] `/treasury` UI shows reconciled balances
- [ ] Research Lab table shows sane Sharpe values for new runs
- [ ] Document in `PLATFORM_PAGE_GUIDE.md` — treasury is operational-only

---

## Research Lab Overflow — Summary

| Symptom | Root cause | Fix |
|---------|------------|-----|
| Sharpe ≈ −10¹⁶, DD 0%, final $100k | Flat equity → `excess.std()` ≈ 10⁻²⁰ | `excess_std > 1e-12` guard + clamp |
| Persists in DB | Alpha optimization matrix persisted 81 runs | Re-run matrix or SQL sanitize |

**Not related to treasury NAV** — separate validation metrics bug.

---

*This audit preserves all existing data. Corrections rebuild balances from the immutable transaction ledger without deleting audit history.*
