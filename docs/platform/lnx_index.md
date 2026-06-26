# LNX Ecosystem Index

Backend-computed composite index tracking platform health — **operational metrics**, not validated backtest performance.

---

## Composite Formula

| Component | Weight | Source |
|-----------|--------|--------|
| Treasury health | 30% | Reserve ratio × 2 (cap 100) |
| Strategy performance | 25% | 30d profit / AUM |
| Execution quality | 20% | 7d autonomous fill rate |
| AUM growth | 15% | Weekly AUM change |
| NAV scale | 10% | NAV / 1M × 10 |

**LNX NAV** = total treasury NAV / 100,000,000 (100M supply)

---

## Schedule

- Daily snapshot 02:00 UTC
- Recomputed after weekly settlement

Stored in `lnx_index_snapshots`.

---

## APIs

| Endpoint | Purpose |
|----------|---------|
| `GET /api/lnx/index` | Latest composite + sub-scores |
| `GET /api/lnx/history` | Time series |
| `GET /api/institutional/lnx/attribution` | Component breakdown |

---

## UI

`/lnx` — composite index chart, treasury NAV, reserve ratio, AUM, attribution panel.

Clients see pool summary via `GET /api/treasury/pools/summary` (not full staff treasury).

---

## Provenance

`OPERATIONAL_LEDGER` — includes demo ledger when seeded. For validated strategy performance use `/fund-performance`.

See [Treasury](./treasury.md).
