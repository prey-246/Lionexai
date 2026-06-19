# NEXA Platform Documentation

Central index for all platform documentation. Last updated: June 2026.

## Quick Links

| Document | Description |
|----------|-------------|
| [VALIDATION_ROADMAP_STATUS.md](./VALIDATION_ROADMAP_STATUS.md) | **5-stage institutional validation roadmap** — completion % per stage |
| [VALIDATION_REPORT.md](./VALIDATION_REPORT.md) | Validation framework, metrics, PDF reports, API reference |
| [API_REFERENCE.md](./API_REFERENCE.md) | Complete REST API endpoint catalog |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | System architecture, containers, core flows |
| [SYSTEM_ARCHITECTURE.md](./SYSTEM_ARCHITECTURE.md) | High-level diagrams and subsystem map |
| [EXECUTION_ARCHITECTURE.md](./EXECUTION_ARCHITECTURE.md) | Exchange adapters, autonomous executor, audit events |
| [DATABASE.md](./DATABASE.md) | Schema, tables, relationships, migrations |
| [API.md](./API.md) | API usage guide with request/response examples |
| [FEATURES_DEEP_DIVE.md](./FEATURES_DEEP_DIVE.md) | Detailed functional specification |
| [DEMO_GUIDE.md](./DEMO_GUIDE.md) | Persona-driven demo scripts (Client, Operator, Risk, Validation) |
| [PAPER_TRADING_REPORT.md](./PAPER_TRADING_REPORT.md) | Paper trading validation checklist |
| [DEVELOPMENT.md](./DEVELOPMENT.md) | Local setup, tests, migrations |
| [DEPLOYMENT.md](./DEPLOYMENT.md) | Production deployment guide |

## Archive

Historical phase reports live in [`archive/`](./archive/) and are not maintained for current features.

## Platform Status (June 2026)

| Area | Status |
|------|--------|
| Autonomous paper trading (Binance + Bybit) | ✅ Wired |
| Institutional validation (Stages 1–4) | ✅ ~95% |
| Validation dashboard + PDF reports | ✅ Complete |
| Daily snapshot archive + history API | ✅ Complete |
| Trade explorer + analytics compare | ✅ Stage 5 |
| Enhanced audit trail (privileged roles) | ✅ Stage 5 |

**Note:** Validation metrics for autonomous paper trades show zeros until the algo executor runs with valid exchange keys and active assigned strategies. Seed/manual trades are excluded from validation by design (`trade_source != AUTONOMOUS`).

## Key UI Routes

| Route | Purpose |
|-------|---------|
| `/validation` | Long-term validation dashboard |
| `/execution-health` | Real-time execution monitoring |
| `/execution-monitor` | Per-exchange CCXT monitor |
| `/trade-explorer` | Historical trade search & filters |
| `/analytics/compare` | Portfolio & strategy comparison |
| `/strategies` | Strategy registry + live performance |
| `/reports` | Weekly/monthly portfolio PDF reports |
| `/stress-test` | Risk validation scenarios |
| `/executive` | Admin executive summary |

## Migrations (Validation)

Apply after pulling latest code:

```bash
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head
docker compose -f docker-compose.prod.yml exec backend python -c \
  "from app.services.validation_service import update_validation_snapshots_job; update_validation_snapshots_job()"
docker compose -f docker-compose.prod.yml build frontend
docker compose -f docker-compose.prod.yml up -d
```
