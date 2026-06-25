# NEXA REST API Reference

Complete endpoint catalog. Interactive Swagger: `http://localhost:8000/docs`

**See also:** [API.md](./API.md) for request/response examples · [VALIDATION_REPORT.md](./VALIDATION_REPORT.md) for validation framework details

---

## Authentication

| Method | Path | Roles | Description |
|--------|------|-------|-------------|
| POST | `/api/auth/register` | Public | Create account |
| POST | `/api/auth/token` | Public | Login → JWT |
| GET | `/api/auth/me` | Any | Current user profile |
| POST | `/api/auth/logout` | Any | Logout |

---

## System

| Method | Path | Roles | Description |
|--------|------|-------|-------------|
| GET | `/api/system/environment` | Any | PAPER/BACKTEST/DEMO state |
| GET | `/api/system/health` | Any | Engine health |
| GET | `/api/system/background-tasks` | Any | Scheduler task status |
| GET | `/api/system/settings` | Any | Global settings |
| PUT | `/api/system/settings` | Admin | Update global settings |

---

## Portfolios

| Method | Path | Roles | Description |
|--------|------|-------|-------------|
| GET | `/api/portfolios` | Any | List portfolios |
| POST | `/api/portfolios` | Any | Create portfolio |
| GET | `/api/portfolios/summary` | Any | Aggregated summary |
| GET | `/api/portfolios/{id}` | Owner/Privileged | Portfolio detail |
| DELETE | `/api/portfolios/{id}` | Owner/Admin | Delete portfolio |
| GET | `/api/portfolios/{id}/equity-curve` | Owner/Privileged | Equity time-series (full history for `*-VALIDATED`) |
| GET | `/api/portfolios/{id}/stats` | Owner/Privileged | Trade stats; validated portfolios use backtest metrics |
| GET | `/api/portfolios/{id}/trades` | Owner/Privileged | Portfolio trades |
| GET | `/api/portfolios/{id}/risk-events` | Owner/Privileged | Risk events |
| GET | `/api/portfolios/{id}/allocations` | Owner/Privileged | Target vs actual weights |
| GET | `/api/portfolios/{id}/rebalances` | Owner/Privileged | Rebalance decision log |
| GET | `/api/portfolios/{id}/settlements` | Owner/Privileged | Weekly settlement history |

---

## Trading & Exchange

| Method | Path | Roles | Description |
|--------|------|-------|-------------|
| POST | `/api/trading/{portfolio_id}/execute` | Owner | Manual paper trade |
| POST | `/api/trading/mandates/{mandate_id}/reset` | Admin | Reset mandate portfolios |
| GET | `/api/exchange/{id}/status` | Privileged | Exchange health + balances |
| GET | `/api/exchange/{id}/heartbeat` | Privileged | Connectivity ping |
| DELETE | `/api/exchange/{id}/orders/{order_id}` | Privileged | Cancel order |
| GET | `/api/execution/health-stats` | Privileged | Execution health dashboard |

---

## Strategies & Backtest

| Method | Path | Roles | Description |
|--------|------|-------|-------------|
| GET | `/api/strategies` | Any | List strategies |
| POST | `/api/strategies` | Admin/Operator/Risk | Create strategy |
| GET | `/api/strategies/{id}` | Any | Strategy detail |
| PUT | `/api/strategies/{id}` | Admin | Update / assign portfolio |
| DELETE | `/api/strategies/{id}` | Admin | Delete strategy |
| GET | `/api/strategies/{id}/backtest-results` | Any | Backtest history |
| POST | `/api/backtest/run` | Any | Run backtest |

---

## Mandates & Risk

| Method | Path | Roles | Description |
|--------|------|-------|-------------|
| GET | `/api/mandates` | Any | List mandates |
| POST | `/api/mandates` | Admin/Risk | Create mandate |
| POST | `/api/mandates/seed-defaults` | Admin | Seed default mandates |
| GET | `/api/mandates/{id}` | Any | Mandate detail |
| GET | `/api/mandates/{id}/history` | Any | Version history |
| PUT | `/api/mandates/{pk_id}` | Admin/Risk | New mandate version |
| POST | `/api/mandates/{pk_id}/activate` | Admin/Risk | Activate version |
| POST | `/api/mandates/{pk_id}/deactivate` | Admin/Risk | Deactivate version |
| POST | `/api/stress-test/{scenario_id}/run` | Admin/Risk | Run risk scenario |

---

## Validated Performance (Fund Backtests & Optimization)

Requires authentication. Fund endpoints available to authenticated users; optimization requires **admin** or **operator**.

| Method | Path | Query / Body | Description |
|--------|------|--------------|-------------|
| GET | `/api/validated/fund/latest/{fund_id}` | `include_demo=true` (admin/operator) | Latest VALIDATED_HISTORICAL run + optional `demo_comparison` |
| GET | `/api/validated/fund/runs` | `fund_id`, `limit` | List validated fund runs |
| POST | `/api/validated/fund/run-all` | `{ initial_capital, persist }` | Baseline backtests for all funds |
| POST | `/api/validated/optimization/run` | `{ phase, fund_id, bar_limit, regenerate }` | Alpha optimization program |
| GET | `/api/validated/optimization/experiments` | `fund_id`, `limit` | Optimization grid results |
| GET | `/api/validated/global-risk` | — | Global risk score 0–100 |
| POST | `/api/validated/strategy/run` | — | Single-strategy validation run |

**Validated reference portfolios:** `LNX-PRESERVE-VALIDATED`, `LNX-BALANCE-VALIDATED`, `LNX-ALPHA-VALIDATED` (admin account).

---

## Validation (Institutional)

All validation endpoints require **admin**, **operator**, or **risk_manager** unless noted.

| Method | Path | Query Params | Description |
|--------|------|--------------|-------------|
| GET | `/api/validation/summary` | — | Legacy 3-day summary (demo operational) |
| GET | `/api/validation/snapshots` | `period`, `snapshot_type`, `scope_id`, **`data_source`** (`validated` default, `demo`) | Rolling snapshots |
| GET | `/api/validation/snapshots/range` | `start_date`, `end_date`, `snapshot_key` | Custom date-range metrics |
| POST | `/api/validation/snapshots/refresh` | — | Force snapshot recompute |
| GET | `/api/validation/history` | `snapshot_key`, `start_date`, `end_date` | Daily archive rows |
| GET | `/api/validation/history/metrics` | `snapshot_key`, `metric`, `start_date`, `end_date` | Metric time-series |
| POST | `/api/validation/history/archive` | — | Manual daily archive |
| GET | `/api/validation/report/pdf` | `period` (TODAY/7D/14D/30D/ALL) | Institutional PDF |
| GET | `/api/validation/report/pdf/weekly` | — | 7-day PDF |
| GET | `/api/validation/report/pdf/monthly` | — | 30-day PDF |
| GET | `/api/validation/report/pdf/30-day` | — | 30-day PDF alias |
| POST | `/api/validation/reports/generate-simulation` | — | Growth simulator PDF (client/admin) |

**Snapshot keys:** `GLOBAL_TODAY`, `GLOBAL_7D`, `GLOBAL_14D`, `GLOBAL_30D`, `GLOBAL_ALL`, `PORTFOLIO_{id}_{period}`, `STRATEGY_{name}_{period}`

**History metrics:** `win_rate_pct`, `max_drawdown_pct`, `total_pnl`, `sharpe_ratio`, `avg_return_pct`, `fill_rate_pct`

---

## Analytics (Stage 5)

| Method | Path | Query Params | Roles | Description |
|--------|------|--------------|-------|-------------|
| GET | `/api/analytics/strategies` | `trade_source` | Any | Live strategy performance |
| GET | `/api/analytics/portfolios/compare` | `ids` (comma-separated, 2–6) | Owner/Privileged | Portfolio comparison |
| GET | `/api/analytics/strategies/compare` | `names`, `trade_source` | Privileged | Strategy comparison |

---

## Trade Explorer (Stage 5)

| Method | Path | Query Params | Description |
|--------|------|--------------|-------------|
| GET | `/api/trades/` | See below | Paginated trade search |

**Filters:** `portfolio_id`, `symbol`, `strategy_name`, `exchange`, `trade_source`, `status`, `side`, `start_date`, `end_date`, `search`, `skip`, `limit` (max 200)

Clients see own portfolios only; privileged roles see system-wide trades.

---

## Audit Trail

| Method | Path | Query Params | Description |
|--------|------|--------------|-------------|
| GET | `/api/audit/` | `skip`, `limit`, `action_type`, `exchange`, `start_date`, `end_date`, `search` | Paginated audit logs |

Privileged roles (admin/operator/risk_manager) see system-wide trail; clients see own actions.

---

## Reports

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/reports/generate` | Generate portfolio report |
| GET | `/api/reports/{portfolio_id}` | List reports for portfolio |
| GET | `/api/reports/{report_id}/download` | Download report PDF |

---

## Intelligence & Treasury

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/intelligence/news` | Latest market news |
| GET | `/api/intelligence/events` | Economic events |
| GET | `/api/intelligence/sentiment/{symbol}` | AI sentiment score |
| GET | `/api/treasury/pools` | Treasury pool balances |
| GET | `/api/treasury/transactions` | Treasury ledger |
| POST | `/api/treasury/seed` | Seed treasury (admin) |
| POST | `/api/treasury/transfer` | Inter-pool transfer (admin) |
| POST | `/api/treasury/sweep` | Yield sweep (admin) |

---

## WebSockets

| Path | Purpose |
|------|---------|
| `/ws/market` | Live market ticks |
| `/ws/portfolio` | Portfolio updates |
| `/ws/alerts` | Risk/system alerts |

---

## Role Reference

| Role | Key Access |
|------|------------|
| `client` | Own portfolios, simulator PDF |
| `operator` | Execution, validation, audit (system-wide) |
| `risk_manager` | Mandates, stress tests, validation |
| `admin` | Full access including user/role management |

---

## Frontend Routes ↔ API

| UI Route | Primary APIs |
|----------|--------------|
| `/validation` | `/api/validation/snapshots?data_source=validated`, `/history/metrics` |
| `/fund-performance` | `/api/validated/fund/latest/{id}`, `?include_demo=true` |
| `/trade-explorer` | `/api/trades/` |
| `/analytics/compare` | `/api/analytics/portfolios/compare`, `/strategies/compare` |
| `/strategies` | `/api/strategies`, `/api/analytics/strategies` |
| `/execution-health` | `/api/execution/health-stats` |
| `/execution-monitor` | `/api/exchange/{id}/status` |
| `/audit` | `/api/audit/` |
| `/executive` | `/api/portfolios/summary`, validation snapshots |
| `/reports` | `/api/reports/*`, validation PDF endpoints |
