# NEXA Validation Report

## Purpose

This document defines the institutional validation framework for the NEXA platform's paper trading and execution layer. Metrics are sourced from the audit trail, exchange adapters, and risk engine.

## Validation Framework

**UI:** `/validation`  
**API:** `GET /api/validation/summary`  
**PDF:** `GET /api/validation/report/pdf`

### Three-Day Tracking

| Day | Metrics Captured |
|-----|------------------|
| Day 1 | Trades executed, success rate, risk rejections |
| Day 2 | Same — rolling 24h window |
| Day 3 | Same — aggregated into 3-day summary |

### Aggregated Results

| Metric | Source |
|--------|--------|
| Total Orders | Audit log count (executed + rejected) |
| Filled Orders | `AUTONOMOUS_TRADE_EXECUTED_*`, `ORDER_FILLED` |
| Rejected Orders | `ORDER_REJECTED`, `RISK_REJECTION` |
| Average Latency | Audit metadata `latency_ms` |
| Best Portfolio | Highest successful trade count |
| Worst Portfolio | Lowest successful trade count |
| Exchange Uptime | `EXCHANGE_RECONNECTED` vs `EXCHANGE_DISCONNECTED` ratio |

## Exchange Connectivity Validation

| Exchange | Endpoint | Expected |
|----------|----------|----------|
| Binance Testnet | `/api/exchange/binance/status` | HTTP 200, OPERATIONAL |
| Bybit Demo | `/api/exchange/bybit/status` | HTTP 200, OPERATIONAL |

## Order Execution Statistics

Tracked via execution health dashboard (`/execution-health`):

- Orders submitted / filled / rejected / cancelled (today)
- Average, fastest, and slowest fill latency
- Recent activity table with exchange, portfolio, symbol, result

## Risk Rejection Validation

Five institutional scenarios at `/stress-test`:

1. **Leverage Violation** → REJECTED: Leverage Limit Exceeded
2. **AI Sentiment Gatekeeper** → REJECTED: Extreme Bearish Sentiment
3. **Mandate Kill Switch** → REJECTED: Mandate Kill Switch Active
4. **Global Kill Switch** → REJECTED: Global Kill Switch Active
5. **Daily Loss Breach** → REJECTED: Daily Loss Limit Breached

Each scenario generates a real audit log entry via `POST /api/stress-test/{scenario_id}/run`.

## Uptime Monitoring

Exchange heartbeat is checked on each execution health refresh:
- Connected / Disconnected status per exchange
- Last successful heartbeat timestamp
- Disconnect events logged as `EXCHANGE_DISCONNECTED`

## Demo Environment

Ensure platform is populated for institutional demonstrations:

```bash
# 1. Seed mandates (admin API or startup)
POST /api/mandates/seed-defaults

# 2. Seed treasury pools
POST /api/treasury/seed

# 3. Seed comprehensive demo data
python scripts/seed_demo_environment.py
```

**Targets:** 10+ portfolios, 5+ strategies, 100+ trades, 250+ audit logs, 25+ treasury events, 50+ news articles, 50+ risk events.

## Success Criteria

| Criterion | Status |
|-----------|--------|
| Binance Testnet executing orders | ✅ Adapter + executor wired |
| Bybit Demo executing orders | ✅ Adapter + executor wired |
| Orders logged in audit trail | ✅ Structured metadata |
| Portfolios updated automatically | ✅ Trade + equity on fill |
| Execution Health Dashboard | ✅ `/execution-health` |
| Fund Growth Simulator | ✅ `/simulator` |
| Risk Validation Suite | ✅ `/stress-test` (live API) |
| Three-day validation | ✅ `/validation` |
| Validation PDF reports | ✅ Download endpoint |
| Demo environment populated | ✅ `seed_demo_environment.py` |

## Report Contents (PDF)

Generated validation PDF includes:
- Three-day performance table
- Aggregated order statistics
- Average latency
- Best / worst portfolio
- Exchange uptime percentage

*Historical Strategy Performance Simulation — Illustrative Projections Only.*
