# Phase 4 API Quick Reference

Companion to [PHASE4_AUTONOMOUS_FUND_MANAGER.md](./PHASE4_AUTONOMOUS_FUND_MANAGER.md). All endpoints require `Authorization: Bearer <token>` unless noted.

## Funds

```http
GET  /api/funds/
GET  /api/funds/{PRESERVE|BALANCE|ALPHA}
POST /api/funds/{fund_id}/invest
```

**Invest**
```json
{ "amount": 10000, "portfolio_id": "MY-FUND-001" }
```

**Fund response fields**
- `target_return_label` — e.g. `"1% weekly · 4.33% monthly"`
- `target_weekly_return_pct` — settlement target: 1.0, 2.5, 5.0
- `target_monthly_return_pct` — weekly × 4.33: 4.33, 10.82, 21.65
- `actual_weekly_return_pct` — trailing 7D, equity-weighted (from equity curves)
- `actual_monthly_return_pct` — trailing 30D, equity-weighted
- `actual_total_return_pct` — (AUM − principal) / principal since inception
- `total_aum`, `portfolio_count`
- `asset_universe[]` — symbol, min/max weight

**Fund targets (operational)**

| Fund | Weekly | Monthly |
|------|--------|---------|
| PRESERVE | 1% | 4.33% |
| BALANCE | 2.5% | 10.82% |
| ALPHA | 5% | 21.65% |

## Assets & Market

```http
GET /api/assets/?asset_class=CRYPTO
GET /api/market/global-state
GET /api/market/regime?scope=GLOBAL&history=5
GET /api/market/regime/all
```

**Price providers:** Binance (crypto), yfinance (metals/FX/indices), mock fallback.

## Portfolio Transparency

```http
GET /api/portfolios/{id}
GET /api/portfolios/{id}/stats
GET /api/portfolios/{id}/equity-curve?limit=100
GET /api/portfolios/{id}/allocations
GET /api/portfolios/{id}/rebalances?limit=20
GET /api/portfolios/{id}/settlements?limit=20
```

Portfolio returns on the UI are derived from `equity-curve` (total + 7D). Stats include win rate and trade PnL.

**Settlement response (sample fields)**
```json
{
  "id": "stl_abc123",
  "iso_week_key": "2026-W25",
  "opening_equity": 50000,
  "starting_nav": 50000,
  "period_pnl": 3200,
  "trading_pnl": 3200,
  "target_return_pct": 5.0,
  "target_yield": 2500,
  "client_entitlement": 2500,
  "excess_routed": 700,
  "treasury_routed": 700,
  "shortfall_topup": 0,
  "shortfall_topups": 0,
  "lnx_contribution": 35,
  "uncovered": 0,
  "status": "SETTLED",
  "breakdown": { "routed": { "YIELD": 280, "GROWTH": 175 } }
}
```

## Treasury

```http
GET  /api/treasury/pools
GET  /api/treasury/pools/analytics          # admin, operator, risk_manager
GET  /api/treasury/transactions?limit=50
GET  /api/treasury/routing?limit=100        # admin, operator, risk_manager, client
POST /api/treasury/seed                     # admin
POST /api/treasury/sweep
POST /api/treasury/transfer
```

**Pool analytics** — per pool (`RESERVE`, `YIELD`, `GROWTH`, `OPERATIONS`, `INSURANCE`, `LNX_INDEX`):
- `balance`, `contributions`, `withdrawals`, `net_flow`, `growth_pct`

## LNX Index

```http
GET /api/lnx/index
GET /api/lnx/history?limit=90
```

**Index response**
```json
{
  "composite_index": 59.35,
  "nav": 125000,
  "treasury_nav": 2719519.13,
  "aum": 3850000,
  "reserve_ratio": 0.72,
  "treasury_health": 72.5,
  "strategy_performance": 1.2,
  "execution_quality": 0.95,
  "aum_growth": 850000,
  "weekly_change_pct": 0.42,
  "monthly_change_pct": 1.8,
  "computed_at": "2026-06-24T10:00:00"
}
```

## Market Intelligence

```http
GET /api/market-intelligence/dashboard
```

Returns: `global_state`, `regimes`, `asset_pulse`, `global_risk_sentiment`, `news[]`.

**News ingestion:** CoinDesk RSS (hourly), Investing.com FX + Commodities RSS (scheduled job). Not used for portfolio return calculation.

## Audit

```http
GET /api/audit?category=Treasury&limit=50
```

**Categories:** Trading, Treasury, Settlement, Allocation, Rebalance, Risk, Infrastructure, System

## Strategies (Optimizer)

```http
GET /api/strategies/scores?limit=20   # admin, operator, risk_manager
```

Live autonomous fund performance also visible at `/strategies` (`AUTO:PRESERVE`, `AUTO:BALANCE`, `AUTO:ALPHA`).

## Validation (Extended Periods)

```http
GET /api/validation/snapshots?period=90D
GET /api/validation/snapshots?period=180D
GET /api/validation/snapshots?period=365D
GET /api/validation/report/pdf?period=90D
```

Extended metrics live at `snapshot.chart_data.extended_metrics`:
- `fund_performance_pct`
- `asset_performance_pct`
- `treasury_growth_pct`
- `lnx_growth_pct`
- `client_yield_delivery_pct`

## Demo Reset (Admin Script)

```bash
python scripts/reset_institutional_demo.py --confirm
python scripts/reset_institutional_demo.py --confirm --enable-autonomous
```

Not an HTTP endpoint — run inside backend container. See [PHASE4 §13](./PHASE4_AUTONOMOUS_FUND_MANAGER.md#13-productionization-pass-june-2026).

## Backtest (Multi-Asset)

```http
POST /api/backtest/run
```

```json
{
  "symbol": "XAUUSD",
  "strategy": "MOMENTUM",
  "timeframe": "1d",
  "initial_capital": 100000,
  "strategy_params": { "lookback": 21 }
}
```

Supported strategy keys: `MA_CROSSOVER`, `MEAN_REVERSION`, `MOMENTUM`, `TREND_FOLLOWING`, `VOL_BREAKOUT`, `CROSS_ASSET_ROTATION`, `RISK_PARITY`, `SENTIMENT_OVERLAY`.

## WebSockets (unchanged)

- `ws://localhost:8000/api/ws/market`
- `ws://localhost:8000/api/ws/portfolio`
- `ws://localhost:8000/api/ws/alerts`
