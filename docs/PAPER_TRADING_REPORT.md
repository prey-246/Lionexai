# NEXA Paper Trading Report

## Environment

| Setting | Value |
|---------|-------|
| Mode | Paper / Testnet |
| Exchanges | Binance Testnet, Bybit Demo Trading |
| Execution Engine | Autonomous Executor (60s cycle) |
| Risk Engine | Pre-trade mandate validation |

## Day 1 — Baseline Connectivity

| Metric | Target | Verification |
|--------|--------|--------------|
| Binance adapter connect | Pass | `GET /api/exchange/binance/heartbeat` |
| Bybit adapter connect | Pass | `GET /api/exchange/bybit/heartbeat` |
| Balance fetch | Pass | Status endpoint returns balances |
| Order placement | Pass | Autonomous executor or manual monitor |
| Audit trail write | Pass | `AUTONOMOUS_TRADE_EXECUTED_*` events |

## Day 2 — Execution Volume

| Metric | Target | Verification |
|--------|--------|--------------|
| Orders submitted | > 0 | Execution health dashboard |
| Orders filled | > 0 | Audit log `ORDER_FILLED` |
| Risk rejections logged | Captured | Audit log `ORDER_REJECTED` |
| Average latency | < 500ms | Audit metadata `latency_ms` |
| Portfolio updates | Automatic | Trade records + equity changes |

## Day 3 — Risk & Validation

| Metric | Target | Verification |
|--------|--------|--------------|
| Leverage rejection | REJECTED | Stress test SCENARIO_A |
| AI sentiment gate | REJECTED | Stress test SCENARIO_B |
| Mandate kill switch | REJECTED | Stress test SCENARIO_C |
| Global kill switch | REJECTED | Stress test SCENARIO_D |
| Daily loss breach | REJECTED | Stress test SCENARIO_E |

## Results Summary

View live aggregated results at `/validation`:

- Total orders (3-day window)
- Filled vs rejected breakdown
- Average execution latency
- Best / worst performing portfolio
- Exchange uptime percentage

Download PDF: `GET /api/validation/report/pdf`

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
- [ ] At least one strategy assigned with `execution_exchange` and `assigned_portfolio_id`
- [ ] Strategy marked `is_active: true`
- [ ] Demo data seeded: `python scripts/seed_demo_environment.py`
- [ ] Execution health dashboard shows CONNECTED for configured exchanges
- [ ] All five stress test scenarios return REJECTED with audit logs

*Historical Strategy Performance Simulation — Illustrative Projections Only.*
