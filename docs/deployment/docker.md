# Docker

Docker Compose runs the full LionexAI stack locally and in production.

---

## Compose Files

| File | Use |
|------|-----|
| `docker-compose.yml` | Local development (hot-reload backend) |
| `docker-compose.prod.yml` | Production-like deployment |

---

## Services

| Service | Image | Ports |
|---------|-------|-------|
| `backend` | Python 3.12 + FastAPI | 8000 |
| `frontend` | Next.js production build | 3000 |
| `db` | PostgreSQL 15 + TimescaleDB | 5432 |
| `redis` | Redis 7 | 6379 |

---

## Quick Start (Development)

```bash
cp .env.example .env
docker compose up --build -d
docker compose exec backend alembic upgrade head
docker compose exec backend python scripts/seed_phase4.py
docker compose exec backend python scripts/reset_institutional_demo.py --confirm
```

Access: `http://localhost:3000` · API docs: `http://localhost:8000/docs`

---

## Production

```bash
docker compose -f docker-compose.prod.yml up --build -d
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head
```

**Frontend changes require rebuild:**

```bash
docker compose -f docker-compose.prod.yml build frontend
docker compose -f docker-compose.prod.yml up -d frontend
```

Backend hot-reloads via volume mount in prod compose.

---

## Environment Variables

Key variables in `.env`:

| Variable | Purpose |
|----------|---------|
| `POSTGRES_*` | Database credentials |
| `SECRET_KEY` | JWT signing |
| `NEXT_PUBLIC_API_URL` | Browser API base URL |
| `INTERNAL_API_URL` | SSR Docker network URL |
| `BINANCE_*` / `BYBIT_*` | Exchange keys (testnet/demo) |
| `FRED_API_KEY` | Optional macro feeds |

See [Deployment](./deployment.md) for server setup with Nginx and TLS.

---

## Useful Commands

```bash
docker compose ps
docker compose logs -f backend
docker compose exec backend python scripts/reconcile_treasury_ledger.py --dry-run
docker compose exec db psql -U nexa -d nexa_db
```

See [Developer Setup](../guides/developer_setup.md).
