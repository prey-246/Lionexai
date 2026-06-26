# Backend Architecture

FastAPI application in `backend/app/`.

---

## Structure

```
backend/app/
├── api/routes/       # REST endpoints
├── engines/          # Allocation, regime, macro, risk, LNX, optimizer
├── services/         # Settlement, validation, treasury, market data, NLP
├── analytics/        # PerformanceEngine (equity-based metrics)
├── models/           # SQLAlchemy domain + Pydantic schemas
├── validation/       # Historical fund simulator, strategy validator
├── exchange/         # Simulated + live exchange adapters
└── main.py           # Lifespan, schedulers, async loops
```

---

## Core Services

| Service | Purpose |
|---------|---------|
| `settlement_engine` | Weekly client settlement, treasury routing |
| `validation_service` | Demo + validated validation snapshots |
| `validated_fund_service` | Read path for fund backtests |
| `market_data_service` | OHLCV ingestion, live prices |
| `market_intelligence_service` | Dashboard aggregate |
| `nlp_service` | News sentiment scoring |
| `treasury_verification_engine` | Solvency, routing integrity |
| `live_validation_engine` | Paper-live metric snapshots |
| `autonomous_manager` | Autonomous trade cycle (skips `*-VALIDATED`) |
| `portfolio_manager` | Multi-asset execution orchestration |

---

## Engines

| Engine | Output |
|--------|--------|
| `allocation_engine` | Target weights → `portfolio_allocations` |
| `regime_engine` | BULL/BEAR/SIDEWAYS/CRISIS |
| `macro_intelligence` | `global_market_state` (risk score, ranking) |
| `global_risk_engine` | Explainable composite risk (on-demand) |
| `lnx_index` | `lnx_index_snapshots` |
| `strategy_optimizer` | Weekly strategy scores |

---

## Authentication & Roles

JWT via `POST /api/auth/token`. Roles: `client`, `operator`, `risk_manager`, `admin`. Route dependencies in `api/deps.py`.

---

## Scripts

| Script | Use |
|--------|-----|
| `seed_phase4.py` | Funds, assets, treasury pools |
| `reset_institutional_demo.py` | Purge + re-seed demo portfolios |
| `run_alpha_optimization.py` | Optimization grid |
| `reconcile_treasury_ledger.py` | Rebuild pool balances from ledger |

See [Developer Setup](../guides/developer_setup.md).
