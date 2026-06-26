# Database Schema Documentation

## Overview

NEXA uses PostgreSQL 15 with TimescaleDB extension for time-series data. The schema is designed for:
- Institutional-grade audit trails
- Time-series performance tracking
- Fast queries on portfolio analytics
- Immutable risk event logging

## Tables & Relationships

### Users Table

```sql
CREATE TABLE users (
    id VARCHAR PRIMARY KEY,
    email VARCHAR UNIQUE NOT NULL,
    role_tier VARCHAR DEFAULT 'retail',  -- retail, ops_admin, quant
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT now()
);
```

**Purpose**: User account management and role-based access control

**Columns**:
- `id`: UUID string (primary key)
- `email`: Unique email for login
- `role_tier`: Permission level
- `is_active`: Account status
- `created_at`: Registration timestamp

**Indexes**: email (unique), role_tier

---

### Mandates Table

```sql
CREATE TABLE mandates (
    id VARCHAR PRIMARY KEY,
    name VARCHAR NOT NULL,
    max_leverage FLOAT NOT NULL,
    max_drawdown_pct FLOAT NOT NULL,
    daily_loss_limit_pct FLOAT NOT NULL,
    allowed_assets JSON NOT NULL,
    kill_switch_active BOOLEAN DEFAULT false
);
```

**Purpose**: Risk parameter definitions for portfolios

**Columns**:
- `id`: String identifier (PRESERVE, BALANCE, VAULT, etc.)
- `name`: Display name
- `max_leverage`: Maximum leverage ratio (e.g., 3.0 = 3x)
- `max_drawdown_pct`: Maximum acceptable drawdown percentage
- `daily_loss_limit_pct`: Daily loss limit as % of portfolio
- `allowed_assets`: JSON array of allowed trading symbols
- `kill_switch_active`: System halt status

**Sample Data**:
```sql
INSERT INTO mandates VALUES
('PRESERVE', 'Capital Preservation', 1.0, 5.0, 2.0, '["BTC/USDT", "ETH/USDT"]', false),
('BALANCE', 'Balanced Growth', 3.0, 10.0, 4.0, '["BTC/USDT", "ETH/USDT", "SOL/USDT"]', false),
('VAULT', 'NEXA Vault', 10.0, 25.0, 10.0, '["ALL"]', false);
```

---

### Portfolios Table

```sql
CREATE TABLE portfolios (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL,
    mandate_id VARCHAR NOT NULL,
    total_equity FLOAT DEFAULT 100000.0,
    available_margin FLOAT DEFAULT 100000.0,
    current_drawdown_pct FLOAT DEFAULT 0.0,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (mandate_id) REFERENCES mandates(id)
);
```

**Purpose**: Portfolio accounts and current state

**Columns**:
- `id`: Portfolio UUID
- `user_id`: Owner reference
- `mandate_id`: Risk ruleset reference
- `total_equity`: Current portfolio value
- `available_margin`: Unallocated capital
- `current_drawdown_pct`: Current peak-to-trough percentage

**Indexes**: user_id, mandate_id

**Example**:
```sql
SELECT * FROM portfolios WHERE user_id = 'user_123';
-- Returns current portfolio state and margin
```

---

### Trades Table

```sql
CREATE TABLE trades (
    id VARCHAR PRIMARY KEY,
    portfolio_id INTEGER NOT NULL,
    symbol VARCHAR NOT NULL,
    side VARCHAR NOT NULL,  -- BUY, SELL
    quantity FLOAT NOT NULL,
    entry_price FLOAT NOT NULL,
    exit_price FLOAT,
    status VARCHAR DEFAULT 'OPEN',  -- OPEN, CLOSED, REJECTED
    pnl FLOAT,
    exchange VARCHAR,              -- binance, bybit
    execution_latency_ms FLOAT,
    strategy_name VARCHAR,
    rejection_reason TEXT,
    trade_source VARCHAR DEFAULT 'MANUAL',  -- AUTONOMOUS, MANUAL, SEED
    created_at TIMESTAMP DEFAULT now(),
    closed_at TIMESTAMP,
    FOREIGN KEY (portfolio_id) REFERENCES portfolios(pk_id)
);
```

**Purpose**: Trade execution history, validation analytics, and trade explorer

**Columns**:
- `id`: Trade UUID
- `portfolio_id`: Portfolio reference (integer FK)
- `symbol`: Trading pair (BTC/USDT, etc.)
- `side`: Direction (BUY or SELL)
- `quantity`: Position quantity
- `entry_price`: Execution price
- `exit_price`: Closing price (nullable for open trades)
- `status`: Trade lifecycle state (OPEN, CLOSED, REJECTED)
- `pnl`: Profit/loss (computed on close)
- `exchange`: Execution venue (binance/bybit) — populated by autonomous executor
- `execution_latency_ms`: Round-trip order latency
- `strategy_name`: Algorithm that generated the signal
- `rejection_reason`: Human-readable reason when status = REJECTED
- `trade_source`: Origin — `AUTONOMOUS` (validation scope), `MANUAL`, `SEED`
- `created_at`: Entry timestamp
- `closed_at`: Exit timestamp (nullable)

**Indexes**: portfolio_id, symbol, exchange, trade_source, created_at

**Validation scope**: Institutional metrics filter `trade_source = 'AUTONOMOUS'` only.

**Queries**:
```sql
-- Get closed trades with P&L
SELECT * FROM trades 
WHERE portfolio_id = 'port_123' 
AND status = 'CLOSED'
ORDER BY closed_at DESC;

-- Calculate win rate
SELECT 
    COUNT(CASE WHEN pnl > 0 THEN 1 END) * 100.0 / COUNT(*) as win_rate
FROM trades 
WHERE portfolio_id = 'port_123' AND status = 'CLOSED';
```

---

### Strategies Table

```sql
CREATE TABLE strategies (
    id VARCHAR PRIMARY KEY,
    name VARCHAR NOT NULL,
    description VARCHAR,
    strategy_type VARCHAR,  -- moving_average, rsi, atr, custom
    parameters JSON,
    is_active BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT now()
);
```

**Purpose**: Strategy definitions and configuration

**Columns**:
- `id`: Strategy UUID
- `name`: Display name
- `description`: Purpose and logic
- `strategy_type`: Classification
- `parameters`: JSON object with parameters
  ```json
  {
    "fast_ma": 20,
    "slow_ma": 50,
    "rsi_threshold": 70
  }
  ```
- `is_active`: Deployment status
- `created_at`: Creation timestamp

**Example**:
```sql
INSERT INTO strategies VALUES
('strat_001', 'MA Crossover', 'Moving average crossover', 'moving_average',
 '{"fast":20,"slow":50}', true, now());
```

---

### BacktestResults Table

```sql
CREATE TABLE backtest_results (
    id VARCHAR PRIMARY KEY,
    strategy_id VARCHAR NOT NULL,
    start_date TIMESTAMP,
    end_date TIMESTAMP,
    initial_capital FLOAT,
    final_equity FLOAT,
    total_return_pct FLOAT,
    cagr FLOAT,
    sharpe_ratio FLOAT,
    sortino_ratio FLOAT,
    max_drawdown_pct FLOAT,
    win_rate FLOAT,
    profit_factor FLOAT,
    total_trades INTEGER,
    winning_trades INTEGER,
    created_at TIMESTAMP DEFAULT now(),
    results_json JSON,
    FOREIGN KEY (strategy_id) REFERENCES strategies(id)
);
```

**Purpose**: Backtest execution results and metrics

**Columns**:
- All standard backtest metrics
- `results_json`: Full detailed results
  ```json
  {
    "trades": [...],
    "equity_curve": [...],
    "daily_returns": [...]
  }
  ```

**Query**:
```sql
-- Best performing strategy
SELECT strategy_id, sharpe_ratio, max_drawdown_pct
FROM backtest_results
ORDER BY sharpe_ratio DESC
LIMIT 1;
```

---

### AuditLogs Table

```sql
CREATE TABLE audit_logs (
    id VARCHAR PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT now(),
    action_type VARCHAR NOT NULL,  -- RISK_REJECTION, KILL_SWITCH_TRIGGERED, etc.
    description VARCHAR,
    metadata_json JSON
);
```

**Purpose**: Immutable compliance and risk event log

**Indexes**: timestamp DESC, action_type

**Columns**:
- `id`: Log entry UUID
- `timestamp`: Event occurrence time
- `action_type`: Event classification
- `description`: Human-readable explanation
- `metadata_json`: Full event context
  ```json
  {
    "portfolio_id": "port_123",
    "mandate_id": "BALANCE",
    "symbol": "BTC/USDT",
    "required_margin": 50000,
    "available_margin": 30000,
    "reason": "Leverage limit exceeded"
  }
  ```

**Queries**:
```sql
-- Recent risk rejections
SELECT * FROM audit_logs
WHERE action_type = 'RISK_REJECTION'
ORDER BY timestamp DESC LIMIT 10;

-- Kill switch events
SELECT * FROM audit_logs
WHERE action_type = 'KILL_SWITCH_TRIGGERED'
AND timestamp > now() - INTERVAL '24 hours';

-- Compliance report (30 days)
SELECT action_type, COUNT(*) as count
FROM audit_logs
WHERE timestamp > now() - INTERVAL '30 days'
GROUP BY action_type;
```

---

### EquityCurves Table (TimeSeries)

```sql
CREATE TABLE equity_curves (
    id VARCHAR,
    portfolio_id VARCHAR NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    equity FLOAT NOT NULL,
    drawdown_pct FLOAT DEFAULT 0.0,
    FOREIGN KEY (portfolio_id) REFERENCES portfolios(id)
);

SELECT create_hypertable('equity_curves', 'timestamp');
```

**Purpose**: Time-series equity tracking (TimescaleDB optimized)

**Columns**:
- `id`: Entry UUID
- `portfolio_id`: Portfolio reference
- `timestamp`: Data point time
- `equity`: Portfolio value
- `drawdown_pct`: Drawdown at that time

**Performance**: TimescaleDB compression for efficient storage

**Query**:
```sql
-- Portfolio equity over last 7 days
SELECT timestamp, equity, drawdown_pct
FROM equity_curves
WHERE portfolio_id = 'port_123'
AND timestamp > now() - INTERVAL '7 days'
ORDER BY timestamp DESC;
```

---

### RiskEvents Table

```sql
CREATE TABLE risk_events (
    id VARCHAR PRIMARY KEY,
    portfolio_id VARCHAR NOT NULL,
    event_type VARCHAR,
    severity VARCHAR,  -- INFO, WARNING, CRITICAL
    description VARCHAR,
    triggered_at TIMESTAMP DEFAULT now(),
    resolved BOOLEAN DEFAULT false,
    metadata_json JSON,
    FOREIGN KEY (portfolio_id) REFERENCES portfolios(id)
);
```

**Purpose**: Risk trigger tracking and monitoring

**Columns**:
- `id`: Event UUID
- `portfolio_id`: Affected portfolio
- `event_type`: Event classification (MARGIN_BREACH, LOSS_LIMIT, etc.)
- `severity`: Impact level
- `description`: Event explanation
- `triggered_at`: Timestamp
- `resolved`: Resolution status
- `metadata_json`: Event context

**Example Events**:
```json
{
  "event_type": "DAILY_LOSS_LIMIT",
  "severity": "CRITICAL",
  "description": "Daily loss limit breached: -$4,200 >= -$4,000",
  "metadata_json": {
    "daily_pnl": -4200,
    "limit": -4000,
    "mandate": "BALANCE"
  }
}
```

---

### ValidationSnapshots Table

```sql
CREATE TABLE validation_snapshots (
    pk_id SERIAL PRIMARY KEY,
    snapshot_key VARCHAR UNIQUE NOT NULL,
    snapshot_type VARCHAR NOT NULL,  -- GLOBAL, PORTFOLIO, STRATEGY
    period VARCHAR NOT NULL,           -- TODAY, 7D, 14D, 30D, ALL
    scope_id VARCHAR,
    total_trades INTEGER DEFAULT 0,
    winning_trades INTEGER DEFAULT 0,
    losing_trades INTEGER DEFAULT 0,
    win_rate_pct FLOAT DEFAULT 0.0,
    total_pnl FLOAT DEFAULT 0.0,
    profit_factor FLOAT,
    sharpe_ratio FLOAT,
    max_drawdown_pct FLOAT DEFAULT 0.0,
    avg_return_pct FLOAT DEFAULT 0.0,
    largest_win FLOAT DEFAULT 0.0,
    largest_loss FLOAT DEFAULT 0.0,
    avg_latency_ms FLOAT DEFAULT 0.0,
    fill_rate_pct FLOAT DEFAULT 0.0,
    chart_data JSON,
    updated_at TIMESTAMP DEFAULT now()
);
```

**Purpose**: Live rolling validation metrics cache, refreshed every 15 minutes

**Snapshot keys**: `GLOBAL_30D`, `PORTFOLIO_{id}_7D`, `STRATEGY_{name}_ALL`, etc.

**chart_data JSON** includes equity curves, daily PnL series, and `meta` object:
```json
{
  "meta": {
    "total_orders": 142,
    "filled_orders": 128,
    "rejected_orders": 14,
    "best_portfolio": "PORT-1234",
    "worst_portfolio": "PORT-5678",
    "best_strategy": "BTC_RSI_ALPHA",
    "worst_strategy": "ETH_MA_CROSS",
    "exchange_distribution": {"binance": 62.5, "bybit": 37.5}
  }
}
```

---

### ValidationSnapshotHistory Table

```sql
CREATE TABLE validation_snapshot_history (
    pk_id SERIAL PRIMARY KEY,
    archive_date DATE NOT NULL,
    snapshot_key VARCHAR NOT NULL,
    snapshot_type VARCHAR NOT NULL,
    period VARCHAR NOT NULL,
    scope_id VARCHAR,
    -- same metric columns as validation_snapshots
    chart_data JSON,
    archived_at TIMESTAMP DEFAULT now()
);
```

**Purpose**: Append-only daily archive for historical charts and compliance (730-day retention)

**Unique constraint**: One row per `(archive_date, snapshot_key)` — upsert on re-archive same day.

**Migration**: `c4d8e2f91a03_validation_snapshot_history.py`

---

### Reports Table

```sql
CREATE TABLE reports (
    id VARCHAR PRIMARY KEY,
    portfolio_id VARCHAR NOT NULL,
    report_type VARCHAR,  -- WEEKLY, MONTHLY
    period_start TIMESTAMP,
    period_end TIMESTAMP,
    performance_metrics JSON,
    risk_metrics JSON,
    trades_summary JSON,
    html_content VARCHAR,
    pdf_content VARCHAR,
    created_at TIMESTAMP DEFAULT now(),
    FOREIGN KEY (portfolio_id) REFERENCES portfolios(id)
);
```

**Purpose**: Performance reporting and analysis

**Columns**:
- `id`: Report UUID
- `portfolio_id`: Portfolio reference
- `report_type`: WEEKLY or MONTHLY
- `period_start/end`: Report period
- `performance_metrics`: JSON metrics
  ```json
  {
    "total_return_pct": 3.25,
    "win_rate": 72.7,
    "best_trade": 850,
    "worst_trade": -200,
    "total_pnl": 3250
  }
  ```
- `risk_metrics`: Risk statistics
- `trades_summary`: Trade breakdown
- `html_content`: Rendered report
- `pdf_content`: PDF export
- `created_at`: Generation timestamp

---

## Relationships

```
users (1) ──────→ (many) portfolios
            ↓
        mandates
            ↓
        trades
        equity_curves
        risk_events
        reports

strategies → backtest_results

validation_snapshots (live cache)
validation_snapshot_history (daily archive)
    ↑ computed from trades WHERE trade_source = 'AUTONOMOUS'
```

## Indexing Strategy

### Critical Indexes
```sql
-- Fast lookups by portfolio
CREATE INDEX idx_portfolios_user_id ON portfolios(user_id);
CREATE INDEX idx_trades_portfolio_id ON trades(portfolio_id);
CREATE INDEX idx_equity_curves_portfolio_id ON equity_curves(portfolio_id);

-- Time-range queries
CREATE INDEX idx_trades_created_at ON trades(created_at DESC);
CREATE INDEX idx_audit_logs_timestamp ON audit_logs(timestamp DESC);

-- Status filtering
CREATE INDEX idx_trades_status ON trades(status);
CREATE INDEX idx_audit_logs_action_type ON audit_logs(action_type);

-- Compound indexes for common queries
CREATE INDEX idx_trades_portfolio_status ON trades(portfolio_id, status);
CREATE INDEX idx_equity_curves_portfolio_time ON equity_curves(portfolio_id, timestamp DESC);
```

## Query Patterns

### Portfolio Performance
```sql
SELECT 
    (SELECT equity FROM equity_curves 
     WHERE portfolio_id = 'port_123' 
     ORDER BY timestamp DESC LIMIT 1) as current_equity,
    MAX(pnl) as best_trade,
    MIN(pnl) as worst_trade,
    COUNT(CASE WHEN pnl > 0 THEN 1 END) * 100.0 / COUNT(*) as win_rate
FROM trades
WHERE portfolio_id = 'port_123' AND status = 'CLOSED';
```

### Risk Analysis
```sql
SELECT 
    action_type,
    COUNT(*) as frequency,
    MAX(timestamp) as last_occurrence
FROM audit_logs
WHERE timestamp > now() - INTERVAL '7 days'
GROUP BY action_type
ORDER BY frequency DESC;
```

### Drawdown Calculation
```sql
WITH equity_with_max AS (
    SELECT 
        timestamp,
        equity,
        MAX(equity) OVER (ORDER BY timestamp) as peak_equity
    FROM equity_curves
    WHERE portfolio_id = 'port_123'
)
SELECT 
    timestamp,
    equity,
    ((peak_equity - equity) / peak_equity) * 100 as drawdown_pct
FROM equity_with_max
ORDER BY timestamp DESC;
```

## Maintenance

### Backup Strategy
```bash
# Full backup
pg_dump -U user -d nexa_mvp | gzip > backup.sql.gz

# Point-in-time recovery
# PostgreSQL WAL archives enable recovery to any point
```

### TimescaleDB Compression
```sql
-- Compress old equity data (>30 days)
ALTER TABLE equity_curves SET (
    timescaledb.compress,
    timescaledb.compress_orderby = 'timestamp DESC',
    timescaledb.compress_segmentby = 'portfolio_id'
);

SELECT compress_chunk(chunk) FROM show_chunks('equity_curves');
```

### Retention Policies
```sql
-- Keep 1 year of equity curves
SELECT add_retention_policy('equity_curves', INTERVAL '1 year');

-- Keep 5 years of trades
SELECT add_retention_policy('trades', INTERVAL '5 years');
```

---

## Data Dictionary

| Table | Purpose | Volume | Retention |
|-------|---------|--------|-----------|
| users | Accounts | < 1K | Indefinite |
| mandates | Risk rules | < 100 | Indefinite |
| portfolios | Accounts | < 10K | Indefinite |
| trades | History | Millions | 5 years |
| validation_snapshots | Live validation cache | < 1K rows | Rolling |
| validation_snapshot_history | Daily archive | ~730 × keys | 730 days |
| strategies | Definitions | < 10K | Indefinite |
| backtest_results | Results | Millions | 1 year |
| audit_logs | Compliance | Millions | 7 years |
| equity_curves | Time-series | 100M+ | 1 year |
| risk_events | Events | Millions | 1 year |
| reports | Generated | 100K+ | 5 years |

---

For migration details, see `backend/alembic/versions/`.

### Validation Migrations

| Revision | File | Description |
|----------|------|-------------|
| `b7c3e1a42f90` | `extend_trade_validation_fields.py` | Trade columns: exchange, latency, strategy, rejection, trade_source |
| `c4d8e2f91a03` | `validation_snapshot_history.py` | Daily snapshot archive table |

---

## Phase 4 Schema (June 2026)

Historical schema narrative: [Phase 4 archive](../archive/PHASE4_AUTONOMOUS_FUND_MANAGER.md) · Current platform: [Funds](../platform/funds.md), [Treasury](../platform/treasury.md)

### Phase 4 Migrations

| Revision | File | Description |
|----------|------|-------------|
| `d5f3a1b9c204` | `phase4_autonomous_fund_manager.py` | Assets, market_bars, funds, universes, allocations, rebalances, regimes, global_market_state, strategy_scores, lnx_index_snapshots |
| `e6a8c3d12f05` | `treasury_economics_settlements.py` | Fund weekly targets, portfolio principal/last_settled_at, client_settlements |
| `f9c2a4e01b06` | `market_intel_news_columns.py` | market_news_articles.region, asset_classes |

### Key Phase 4 Tables

| Table | Purpose |
|-------|---------|
| `assets` | Multi-asset registry (symbol, asset_class, data_provider, execution_venue) |
| `market_bars` | Unified OHLCV (Timescale-friendly) for crypto, metals, FX |
| `funds` | PRESERVE / BALANCE / ALPHA — `target_weekly_return_pct`, `target_monthly_return_pct`, `target_return_label` (actual returns computed at API layer via `fund_performance_service`, not stored) |
| `fund_asset_universe` | Per-fund asset min/max weight constraints |
| `portfolio_allocations` | Target vs current weight per asset per portfolio |
| `rebalance_events` | Allocation engine decision audit trail |
| `client_settlements` | Weekly profit-routing ledger (idempotent per ISO week) |
| `market_regimes` | Per-asset + GLOBAL regime snapshots |
| `global_market_state` | Macro risk score, asset ranking |
| `strategy_scores` | Weekly optimizer composite rankings |
| `lnx_index_snapshots` | Daily LNX composite index components |

### Portfolio Extensions

- `fund_pk_id` — FK to funds (auto-managed portfolios)
- `auto_managed` — gates settlement + portfolio manager
- `principal` — initial deposit for yield-delivery metrics
- `last_settled_at` — settlement watermark

### Treasury Pools (Seeded)

`RESERVE`, `YIELD`, `GROWTH`, `OPERATIONS`, `INSURANCE`, `LNX_INDEX`

### Validation Extensions

Snapshot periods include **90D**, **180D**, **365D**. Extended fund/treasury/LNX metrics stored in `validation_snapshots.chart_data.extended_metrics` (JSON). Demo snapshots refreshed every 15 minutes; validated snapshots computed on-demand via `data_source=validated`.

### Validated fund runs (Phase 5+)

| Table | Purpose |
|-------|---------|
| `validated_fund_runs` | Fund-level historical backtests on `market_bars`; stores `metrics`, `equity_curve`, `rebalance_log`, `experiment_config`, `rank_score`, `provenance=VALIDATED_HISTORICAL` |
| `validated_strategy_runs` | Single-strategy / symbol research runs |

Reference portfolios `LNX-*-VALIDATED` are regenerated from `SELECTED_BEST` runs via `ValidatedInstitutionalRegenerator`.

