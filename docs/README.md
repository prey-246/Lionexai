# LionexAI Documentation

Production documentation for the LionexAI autonomous multi-asset fund platform.

Last updated: **June 2026**

---

## Start Here

| Audience | Start with |
|----------|------------|
| Founders / stakeholders | [Root README](../README.md) |
| Developers | [Developer Setup](./guides/developer_setup.md) |
| Operators | [Demo Guide](./guides/demo_guide.md) |
| API integrators | [API Reference](./api/api_reference.md) |
| UI / metrics deep dive | [Platform Pages Guide](./guides/platform_pages.md) |

---

## Architecture

| Document | Description |
|----------|-------------|
| [System Architecture](./architecture/system_architecture.md) | Containers, layers, provenance, schedulers |
| [Backend](./architecture/backend.md) | Services, engines, scripts |
| [Frontend](./architecture/frontend.md) | Next.js structure, roles, design system |
| [Database](./architecture/database.md) | Schema, tables, migrations |
| [AI Pipeline](./architecture/ai_pipeline.md) | Intelligence → risk → allocation → validation |

---

## Platform

| Document | Description |
|----------|-------------|
| [Funds](./platform/funds.md) | PRESERVE / BALANCE / ALPHA products |
| [Validation](./platform/validation.md) | Validated vs demo, Research Lab, alpha evidence |
| [Treasury](./platform/treasury.md) | Pools, settlement routing, verification |
| [Risk Engine](./platform/risk_engine.md) | Macro + global risk scores |
| [Allocation Engine](./platform/allocation_engine.md) | Weight computation, rebalancing |
| [Market Intelligence](./platform/market_intelligence.md) | News, NLP, sentiment |
| [LNX Index](./platform/lnx_index.md) | Ecosystem composite index |

---

## Deployment

| Document | Description |
|----------|-------------|
| [Deployment](./deployment/deployment.md) | Production server guide (Nginx, TLS) |
| [Docker](./deployment/docker.md) | Compose, env vars, commands |

---

## API

| Document | Description |
|----------|-------------|
| [API Reference](./api/api_reference.md) | Complete REST catalog |
| Interactive docs | `http://localhost:8000/docs` |

---

## Guides

| Document | Description |
|----------|-------------|
| [Developer Setup](./guides/developer_setup.md) | Local dev, migrations, troubleshooting |
| [Demo Guide](./guides/demo_guide.md) | Persona-driven demo scripts |
| [Platform Pages Guide](./guides/platform_pages.md) | Every UI page — metrics, sources, refresh |
| [Brand Guide](./guides/brand_guide.md) | Colors and presentation theme |
| [Contribution](./guides/contribution.md) | How to contribute |

---

## Data Provenance

| Label | Meaning |
|-------|---------|
| `VALIDATED_HISTORICAL` | Backtest on `market_bars` |
| `DEMO` | Seeded operational paper ledger |
| `PAPER_LIVE` | Long-running autonomous trading |
| `OPERATIONAL_LEDGER` | Treasury pools and settlements |

---

## Demo Accounts

Password: **`password123`** (after institutional reset)

| Email | Role |
|-------|------|
| `admin@google.com` | admin |
| `client1@google.com` | client |
| `operator1@google.com` | operator |
| `risk1@google.com` | risk_manager |

---

## Archive

Historical phase reports: [archive/](./archive/)

---

## Bootstrap Commands

```bash
docker compose -f docker-compose.prod.yml up --build -d
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head
docker compose -f docker-compose.prod.yml exec backend python scripts/seed_phase4.py
docker compose -f docker-compose.prod.yml exec backend python scripts/reset_institutional_demo.py --confirm
```
