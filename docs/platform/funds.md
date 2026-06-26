# Lionex Funds

Three AI-managed fund products with fixed weekly yield targets and autonomous multi-asset allocation.

---

## Funds

| Fund ID | Weekly Target | Monthly Target (approx.) | Risk Profile |
|---------|---------------|---------------------------|--------------|
| PRESERVE | 1.0% | ~4.3% | Conservative |
| BALANCE | 2.5% | ~10.8% | Balanced |
| ALPHA | 5.0% | ~21.7% | Aggressive |

Clients invest via `POST /api/funds/{id}/invest` — creates an `auto_managed` portfolio linked to the fund mandate.

---

## Business Model

- Platform selects strategies, assets, and risk — clients choose fund only.
- **Weekly settlement** credits clients their target gain when treasury can cover shortfalls.
- Profit **above** target routes to treasury pools (YIELD, GROWTH, RESERVE, OPERATIONS, LNX_INDEX).
- Shortfalls topped from YIELD → RESERVE; uncovered amounts logged.

---

## Performance Surfaces

| Surface | Provenance | Route |
|---------|------------|-------|
| Fund Performance (primary) | `VALIDATED_HISTORICAL` | `/fund-performance` |
| Demo comparison (admin) | `DEMO` | Toggle on `/fund-performance` |
| Client portfolios | `DEMO` operational ledger | `/portfolios/{id}` |
| Reference portfolios | `VALIDATED_HISTORICAL` | `/portfolios/LNX-*-VALIDATED` |

Validated metrics come from `validated_fund_runs` (historical simulation on `market_bars`).

---

## Asset Universe

Per-fund universe in `fund_asset_universe`: crypto (BTC, ETH, SOL), metals (XAU, XAG), FX, indices, energy. Weights capped by mandate and universe `max_weight_pct`.

---

## Key APIs

- `GET /api/funds/` — list funds with targets and optional actuals
- `POST /api/funds/{id}/invest` — create/fund portfolio
- `GET /api/validated/fund/latest/{id}` — validated backtest metrics
- `GET /api/funds/{id}/institutional` — institutional analytics

---

## Admin Operations

```bash
# Re-run all fund backtests
docker compose exec backend python -c "..." # or UI on /fund-performance

# Regenerate LNX-*-VALIDATED portfolios
docker compose exec backend python -c \
  "from app.core.database import SessionLocal; from app.validation.validated_institutional_regenerator import ValidatedInstitutionalRegenerator; ValidatedInstitutionalRegenerator(SessionLocal()).regenerate_all()"
```

See [Validation](./validation.md) and [Platform Pages](../guides/platform_pages.md).
