# NEXA Institutional Validation Framework

This document defines the institutional validation framework for NEXA. **June 2026 update:** the validation dashboard supports two data sources — use the correct one for your audience.

## Data sources (June 2026)

| Mode | API | UI toggle | Audience |
|------|-----|-----------|----------|
| **Validated Historical** (default) | `GET /api/validation/snapshots?data_source=validated` | **Validated Historical** | Investors, institutional reporting |
| **Demo Ledger** | `GET /api/validation/snapshots?data_source=demo` | **Demo Ledger** | Internal ops — seeded paper-trading ledger |

**Validated mode** aggregates equity curves from `validated_fund_runs` (PRESERVE + BALANCE + ALPHA). **Demo mode** uses pre-calculated `validation_snapshots` from autonomous/demo trades — metrics are equity-based and sanitized (max drawdown capped at 100%).

For fund-level strategy validation, prefer **`/fund-performance`** (always VALIDATED_HISTORICAL primary).

This document defines metrics for **operational (demo) validation**. Validated historical snapshots are computed on-demand and not stored in `validation_snapshots`.

## UI & API Entry Points

| Resource | Location |
|----------|----------|
| Validation Dashboard | `/validation` |
| Trade Explorer | `/trade-explorer` |
| Analytics Compare | `/analytics/compare` |
| Execution Health | `/execution-health` |
| Legacy 3-Day Summary | `GET /api/validation/summary` |
| Live Snapshots | `GET /api/validation/snapshots?data_source=validated\|demo` |
| Custom Date Range | `GET /api/validation/snapshots/range` |
| Daily Archive | `GET /api/validation/history` |
| Metric Time-Series | `GET /api/validation/history/metrics` |
| PDF Reports | See [PDF Reports](#pdf-reports) below |

---

## Rolling Periods

Pre-calculated snapshots are stored in `validation_snapshots` and refreshed every **15 minutes** (plus on startup):

| Period | Snapshot Key | Description |
|--------|--------------|-------------|
| TODAY | `GLOBAL_TODAY` | Calendar day (UTC) |
| 7D | `GLOBAL_7D` | Rolling 7 days |
| 14D | `GLOBAL_14D` | Rolling 14 days |
| 30D | `GLOBAL_30D` | Rolling 30 days |
| 90D | `GLOBAL_90D` | Rolling 90 days |
| 180D | `GLOBAL_180D` | Rolling 180 days |
| 365D | `GLOBAL_365D` | Rolling 365 days |
| ALL | `GLOBAL_ALL` | Full validated backtest or all demo history |

Portfolio and strategy scoped snapshots: `PORTFOLIO_{id}_{period}`, `STRATEGY_{name}_{period}`.

---

## Performance Metrics

All metrics below are computed from **autonomous paper trades only** unless noted.

| Metric | Description |
|--------|-------------|
| Total / Winning / Losing Trades | Closed trades with PnL |
| Win Rate | Winning / total closed × 100 |
| Total P&L | Sum of closed trade PnL |
| Average Return | Mean **daily** return % from equity curve (not compounded per-trade) |
| Largest Win / Loss | Best and worst single trade |
| Profit Factor | Gross profit / gross loss |
| Sharpe Ratio | Annualized from daily returns |
| Max Drawdown | Peak-to-trough on **equity curve** |
| Fill Rate | Filled / (filled + rejected) orders |
| Avg Latency | Mean execution latency (ms) |
| Daily / Weekly / Monthly PnL | Aggregated chart series |
| Rolling Win Rate (7D) | 7-day smoothed daily win rate |
| Rolling Drawdown (7D) | 7-day smoothed drawdown |

### Dashboard KPIs (also in API)

- Total / Filled / Rejected orders
- Best / Worst Portfolio
- Best / Worst Strategy
- Exchange distribution (Binance vs Bybit %)

Extended meta (`total_orders`, `best_portfolio`, `exchange_distribution`, etc.) is stored in `chart_data.meta` JSON on each snapshot and flattened in API responses.

---

## Charts (Validation Dashboard)

Available on `/validation` when trade history exists:

- Cumulative P&L / equity curve
- Daily P&L, daily trades, daily returns
- Rolling win rate, rolling drawdown
- Weekly and monthly P&L
- Historical win rate & drawdown from daily archive

---

## PDF Reports

Institutional PDFs use `validation_report_service.py` + matplotlib chart embedding.

| Endpoint | Report |
|----------|--------|
| `GET /api/validation/report/pdf?period=30D` | Parametric (TODAY, 7D, 14D, 30D, ALL) |
| `GET /api/validation/report/pdf/weekly` | 7-day |
| `GET /api/validation/report/pdf/monthly` | 30-day |
| `GET /api/validation/report/pdf/30-day` | 30-day alias |
| `POST /api/validation/reports/generate-simulation` | Growth simulator PDF |

### PDF Sections (11)

1. Executive Summary  
2. Capital Curve & Drawdown (embedded charts)  
3. Risk Metrics  
4. Trade Distribution  
5. Portfolio Performance  
6. Strategy Performance  
7. Exchange Performance  
8. Top Symbols & Largest Trades  
9. Latency Analysis (P50, P95, histogram)  
10. Risk Events  
11. System Health & Execution  

Legacy fallback: if no snapshot exists, PDF shows 3-day summary from `/api/validation/summary`.

---

## Continuous Validation Engine (Stage 4)

| Feature | Implementation |
|---------|----------------|
| Scheduler | APScheduler — 15 min + startup immediate run |
| Daily archive | `validation_snapshot_history` (append-only, one row/key/day) |
| Retention | 730 days, auto-purge |
| Equity curves in archive | Full `chart_data` JSON per archive row |
| Custom queries | `GET /api/validation/snapshots/range?start_date=&end_date=` |
| History metrics | `GET /api/validation/history/metrics?snapshot_key=GLOBAL_30D&metric=win_rate_pct` |

Supported history metrics: `win_rate_pct`, `max_drawdown_pct`, `total_pnl`, `sharpe_ratio`, `avg_return_pct`, `fill_rate_pct`.

---

## Trade Capture (Stage 1)

Every autonomous execution persists a `Trade` row with:

| Field | Description |
|-------|-------------|
| `exchange` | binance / bybit |
| `symbol`, `side`, `quantity` | Order details |
| `entry_price`, `exit_price`, `pnl` | Pricing & outcome |
| `execution_latency_ms` | Round-trip latency |
| `strategy_name` | Algorithm name |
| `rejection_reason` | If status = REJECTED |
| `trade_source` | `AUTONOMOUS`, `MANUAL`, or `SEED` |

Rejections from risk engine or exchange also create queryable `REJECTED` trade rows.

---

## Legacy 3-Day Summary

Still available at `GET /api/validation/summary` and shown on the validation page:

| Day | Metrics |
|-----|---------|
| Day 1–3 | Trades executed, success rate, risk rejections |
| Aggregated | Total/filled/rejected orders, avg latency, best/worst portfolio |

---

## Exchange & Execution Validation

| Exchange | Status Endpoint |
|----------|-----------------|
| Binance Testnet | `GET /api/exchange/binance/status` |
| Bybit Demo | `GET /api/exchange/bybit/status` |

Execution health (`/execution-health`, `GET /api/execution/health-stats`):

- Orders submitted / filled / rejected / cancelled (today)
- Risk rejection breakdown (AI, leverage, kill switch)
- Latency stats and recent activity feed

---

## Risk Validation Scenarios

Five live scenarios at `/stress-test` — each writes a real audit log:

1. Leverage Violation  
2. AI Sentiment Gatekeeper  
3. Mandate Kill Switch  
4. Global Kill Switch  
5. Daily Loss Breach  

---

## Demo Environment Setup

```bash
POST /api/mandates/seed-defaults
POST /api/treasury/seed
docker compose -f docker-compose.prod.yml exec backend python scripts/seed_demo_environment.py
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head
docker compose -f docker-compose.prod.yml exec backend python -c \
  "from app.services.validation_service import update_validation_snapshots_job; update_validation_snapshots_job()"
```

**Targets:** 10+ portfolios, 5+ strategies, 100+ trades, 250+ audit logs.

For autonomous validation metrics (non-zero), additionally:

- Configure `BINANCE_API_KEY` / `BYBIT_API_KEY` in `.env`
- Assign strategies with `assigned_portfolio_id` + `execution_exchange`
- Set `is_active: true` on strategies
- Wait for algo executor cycle (~60s)

---

## Success Criteria

| Criterion | Status |
|-----------|--------|
| Binance Testnet executing orders | ✅ |
| Bybit Demo executing orders | ✅ |
| Full trade field capture | ✅ |
| Scheduler + startup snapshot refresh | ✅ |
| Periods TODAY / 7D / 14D / 30D / ALL | ✅ |
| Validation dashboard (Stage 2) | ✅ |
| Institutional PDF + charts (Stage 3) | ✅ |
| Daily archive + history API (Stage 4) | ✅ |
| Trade explorer + compare tools (Stage 5) | ✅ |
| Enhanced audit (privileged roles) | ✅ |

*Historical Strategy Performance Simulation — Illustrative Projections Only.*
