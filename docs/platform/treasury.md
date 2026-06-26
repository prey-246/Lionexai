# Treasury

Operational ledger for institutional capital pools, profit routing, and client settlement economics.

---

## Pools

| Pool ID | Display Target | Profit Routing Share |
|---------|----------------|----------------------|
| RESERVE | 20% | 15% |
| YIELD | 40% | 40% |
| GROWTH | 15% | 25% |
| OPERATIONS | 10% | 15% |
| LNX_INDEX | 10% | 5% |
| INSURANCE | 5% | 0% (not in routing split) |

No automatic rebalancer — drift is expected after asymmetric routing.

---

## Weekly Settlement Routing

When portfolio PnL exceeds weekly target:

```
excess = period_pnl - target_gain
→ split across YIELD, GROWTH, RESERVE, OPERATIONS, LNX_INDEX
→ treasury_transactions (PROFIT_ROUTING)
```

Shortfalls debited from YIELD then RESERVE (`CLIENT_TOPUP`).

---

## NAV Calculation

```
Treasury NAV = Σ treasury_pools.balance
```

Legitimate NAV = demo reset baseline + sum of `treasury_transactions`. Validated historical backtests **must not** mutate pool balances.

Recovery script: `scripts/reconcile_treasury_ledger.py --confirm`

---

## Verification Engine

`GET /api/institutional/treasury/verify`

| Metric | Meaning |
|--------|---------|
| Solvency Score | Composite 0–100 |
| Routing Integrity | Operational settlements vs PROFIT_ROUTING txs |
| Settlement Coverage | % operational settlements with zero uncovered |

Validated synthetic settlements (`stl_val_*`) are excluded from operational checks.

---

## UI & APIs

| Route | Access |
|-------|--------|
| `/treasury` | Admin, risk_manager, operator |
| `GET /api/treasury/pools/summary` | All authenticated (client-safe) |
| `GET /api/treasury/pools` | Staff only |

---

## Related

- [LNX Index](./lnx_index.md)
- [Funds](./funds.md)
- [Archive: Treasury Audit](../archive/TREASURY_AUDIT_REPORT.md) — June 2026 RCA
