# Allocation Engine

Computes target portfolio weights from fund policy, market regime, and inverse-volatility logic.

---

## Schedule

- **Daily** 00:10 UTC (`run_allocation_cycle`)
- Per-fund gate: `rebalance_freq_days` (default 7)
- Regime change can force rebalance

---

## Default Method: Inverse Volatility

```
raw_weight[asset] = 1 / annualized_vol  (floor 0.05)
optional regime_momentum: × (1 + max(momentum, 0) × 2)
regime tilt: BULL ×1.25, BEAR ×0.4, CRISIS ×0.1
safe-haven (XAU, XAG): ×1.5 in risk-off
normalize to (100% - cash_floor)
cap by mandate + fund_asset_universe.max_weight_pct
```

---

## Cash Floors

From fund `allocation_policy`, escalated in RISK_OFF (+15%) and CRISIS (min 60%).

---

## Outputs

| Table | Content |
|-------|---------|
| `portfolio_allocations` | target_weight_pct, current_weight_pct |
| `rebalance_events` | trigger, regime, global_risk_score snapshot |

---

## UI

`/allocation` — target vs current weights, drift per asset.

---

## Integrity Monitor

Hourly scan for drift, missing pools, solvency alerts.  
API: `GET /api/validated/allocation/alerts`

---

## Related

- [Funds](./funds.md)
- [Risk Engine](./risk_engine.md)
