# NEXA Paper Trading Report

## Environment

| Setting | Value |
|---------|-------|
| Mode | Paper / Testnet |
| Exchanges | Binance Testnet, Bybit Demo Trading |
| Execution Engine | Autonomous Executor (60s cycle) |
| Risk Engine | Pre-trade mandate validation |
| Validation Scope | `trade_source = AUTONOMOUS` only |

## Day 1 — Baseline Connectivity

| Metric | Target | Verification |
|--------|--------|--------------|
| Binance adapter connect | Pass | `GET /api/exchange/binance/status` |
| Bybit adapter connect | Pass | `GET /api/exchange/bybit/status` |
| Balance fetch | Pass | Status endpoint returns balances |
| Order placement | Pass | Autonomous executor or manual monitor |
| Audit trail write | Pass | `AUTONOMOUS_TRADE_EXECUTED_*` events |
| Trade field capture | Pass | `exchange`, `latency_ms`, `strategy_name`, `trade_source` on Trade row |

## Day 2 — Execution Volume

| Metric | Target | Verification |
|--------|--------|--------------|
| Orders submitted | > 0 | Execution health dashboard |
| Orders filled | > 0 | Audit log + Trade status CLOSED |
| Risk rejections logged | Captured | Trade status REJECTED + audit log |
| Rejection reason stored | Captured | `rejection_reason` column populated |
| Average latency | < 500ms | `execution_latency_ms` on trades |
| Portfolio updates | Automatic | Trade records + equity changes |

## Day 3 — Risk & Validation

| Metric | Target | Verification |
|--------|--------|--------------|
| Leverage rejection | REJECTED | Stress test SCENARIO_A |
| AI sentiment gate | REJECTED | Stress test SCENARIO_B |
| Mandate kill switch | REJECTED | Stress test SCENARIO_C |
| Global kill switch | REJECTED | Stress test SCENARIO_D |
| Daily loss breach | REJECTED | Stress test SCENARIO_E |

## Rolling Validation (Stages 1–4)

View live aggregated results at `/validation`:

| Period | Snapshot Key | Metrics |
|--------|--------------|---------|
| Today | `GLOBAL_TODAY` | Intraday autonomous trades |
| 7 Days | `GLOBAL_7D` | Weekly rolling window |
| 14 Days | `GLOBAL_14D` | Two-week validation |
| 30 Days | `GLOBAL_30D` | Monthly institutional view |
| All Time | `GLOBAL_ALL` | Full autonomous history |

**Dashboard KPIs:** total/filled/rejected orders, best/worst portfolio & strategy, exchange distribution, Sharpe, drawdown, profit factor, fill rate, latency.

**Historical archive:** Daily rows in `validation_snapshot_history` — query via `GET /api/validation/history`.

## PDF Reports

| Report | Endpoint |
|--------|----------|
| Parametric (any period) | `GET /api/validation/report/pdf?period=30D` |
| Weekly | `GET /api/validation/report/pdf/weekly` |
| Monthly | `GET /api/validation/report/pdf/monthly` |
| Legacy 3-day fallback | Same endpoint when no snapshot exists |

## Trade Explorer & Analytics (Stage 5)

| Tool | Route / API |
|------|-------------|
| Trade search | `/trade-explorer` · `GET /api/trades/` |
| Strategy analytics | `/strategies` · `GET /api/analytics/strategies` |
| Portfolio compare | `/analytics/compare` · `GET /api/analytics/portfolios/compare` |
| Strategy compare | `/analytics/compare` · `GET /api/analytics/strategies/compare` |
| Enhanced audit | `/audit` · `GET /api/audit/?search=&exchange=` |

## Audit Event Coverage

All paper trades generate structured audit metadata:

```json
{
  "portfolio": "PORT-XXXX",
  "exchange": "binance",
  "exchange_order_id": "...",
  "symbol": "BTC/USDT",
  "side": "BUY",
  "quantity": 0.01,
  "fill_status": "closed",
  "latency_ms": 142.5,
  "strategy": "Lion Alpha Momentum"
}
```

## Operational Checklist

- [ ] `.env` contains valid testnet API keys
- [ ] Migrations applied: `alembic upgrade head`
- [ ] At least one strategy assigned with `execution_exchange` and `assigned_portfolio_id`
- [ ] Strategy marked `is_active: true`
- [ ] Demo data seeded: `python scripts/seed_demo_environment.py`
- [ ] Validation snapshots refreshed after first autonomous trades
- [ ] Execution health dashboard shows CONNECTED for configured exchanges
- [ ] All five stress test scenarios return REJECTED with audit logs
- [ ] `/validation` shows non-zero metrics (requires autonomous trade volume)
- [ ] Frontend rebuilt after UI changes: `docker compose build frontend`

## Refresh Validation Data

```bash
docker compose -f docker-compose.prod.yml exec backend python -c \
  "from app.services.validation_service import update_validation_snapshots_job; update_validation_snapshots_job()"
```

*Historical Strategy Performance Simulation — Illustrative Projections Only.*
