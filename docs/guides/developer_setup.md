# NEXA Platform: Developer Guide

This document provides a comprehensive guide for developers to set up the local environment, run tests, manage the database, and contribute to the NEXA platform.

---

## 1. Local Development Setup

### Prerequisites
- Docker & Docker Compose
- Git

### Steps

1.  **Clone the Repository:**
    ```bash
    git clone <your-repository-url>
    cd Lionexai
    ```

2.  **Create Environment File:**
    Copy the example environment file. This file contains all the necessary secrets and configuration for the Docker containers.
    ```bash
    cp .env.example .env
    ```
    *Note: The default values in `.env.example` are configured for the local Docker environment and do not need to be changed for a standard setup.*

3.  **Build and Start Services:**
    Use the standard Docker Compose file, which is configured with hot-reloading for a seamless development experience for both the frontend and backend.
    ```bash
    docker compose up --build -d
    ```
    *Note: This command uses the `docker-compose.yml` file by default, which is designed for local development.*

4.  **Verify Services:**
    After a minute, check that all containers are running and healthy.
    ```bash
    docker compose ps
    ```
    You should see services like `nexa_backend`, `nexa_frontend`, `nexa_db`, and `nexa_redis` with a status of `Up`.

5.  **Access the Platform:**
    - **Frontend:** `http://localhost:3000`
    - **Backend API Docs:** `http://localhost:8000/docs`

6.  **Seed Demo Data (Phase 4 + institutional demo):**
    ```bash
    docker compose exec backend alembic upgrade head
    docker compose exec backend python scripts/seed_phase4.py
    docker compose exec backend python scripts/reset_institutional_demo.py --confirm
    ```

    Demo accounts (password `password123`): `admin@google.com`, `client1@google.com`, `operator1@google.com`, `risk1@google.com`.

7.  **Alpha optimization + validated portfolios (optional):**
    ```bash
    docker compose -f docker-compose.prod.yml exec backend python scripts/run_alpha_optimization.py --phase all
    docker compose -f docker-compose.prod.yml exec backend python -c \
      "from app.core.database import SessionLocal; from app.validation.validated_institutional_regenerator import ValidatedInstitutionalRegenerator; db=SessionLocal(); ValidatedInstitutionalRegenerator(db).regenerate_all(); db.close()"
    ```

---

## 2. Common Development Tasks

### Viewing Logs
Tailing logs is essential for debugging.
```bash
# View logs for the backend
docker compose logs -f backend

# View logs for the frontend
docker compose logs -f frontend
```

### Running Tests

**Backend (Pytest):**
Execute the test suite inside the backend container.
```bash
docker exec -it nexa_backend_prod pytest
```

**Frontend (Lint & Build):**
Execute the linting and build checks inside the frontend container.
```bash
docker exec -it nexa_frontend_prod pnpm lint
docker exec -it nexa_frontend_prod pnpm build
```

### Database Migrations (Alembic)

1.  **Access the Backend Container:**
    ```bash
    docker exec -it nexa_backend_prod /bin/bash
    ```

2.  **Generate a New Migration:**
    After making changes to your SQLAlchemy models in `backend/app/models/domain.py`, run:
    ```bash
    alembic revision --autogenerate -m "Your descriptive migration message"
    ```

3.  **Apply Migrations:**
    The `alembic upgrade head` command runs automatically on container startup. To apply manually:
    ```bash
    docker compose -f docker-compose.prod.yml exec backend alembic upgrade head
    ```

    **Phase 5 + 6 migrations** (applied automatically on startup):
    - `a1b2c3d4e5f6_p5_validated` — validated strategy runs, paper snapshots, allocation alerts
    - `b2c3d4e5f6a7_p6_institutional` — live validation, treasury verification, institutional reports

4.  **Refresh Validation Snapshots:**
    After seeding or when autonomous trades start flowing:
    ```bash
    docker compose -f docker-compose.prod.yml exec backend python -c \
      "from app.services.validation_service import update_validation_snapshots_job; update_validation_snapshots_job()"
    ```

5.  **Rebuild Frontend After UI Changes:**
    The frontend container does not hot-reload in production compose. After changing React pages:
    ```bash
    docker compose -f docker-compose.prod.yml build frontend
    docker compose -f docker-compose.prod.yml up -d frontend
    ```

### Backend Dependencies

Validation PDF chart embedding requires **matplotlib** (`matplotlib>=3.8.0` in `backend/requirements.txt`). Rebuild the backend image after dependency changes.

### Background Jobs

| Job | Interval | Location |
|-----|----------|----------|
| Portfolio manager / algo executor | 60s | `portfolio_manager.py` / `algo_executor.py` |
| Validation snapshots | 15 min + startup | `validation_service.update_validation_snapshots_job()` |
| Live validation snapshots | 6 h | `live_validation_engine.update_live_validation_snapshots()` |
| Paper validation snapshots | 6 h | `paper_trading_validation_service` |
| Allocation integrity scan | 1 h | `allocation_integrity_monitor.run_integrity_scan()` |
| Daily archive | 00:05 UTC | `validation_service.archive_snapshots_to_history()` |
| Price updater | 1 hour | `main.py` scheduler |
| News scraper | 1 hour | `main.py` scheduler |
| NLP analyzer | 10 min | `nlp_service.run_nlp_analysis()` |
| Weekly settlement | Mon 01:00 UTC | `settlement_engine` |
| LNX snapshot | daily | `lnx_index.py` |

---

## 3. Troubleshooting

### API authentication lost on portfolio list
Use `GET /api/portfolios/` with a **trailing slash**. Requests to `/api/portfolios` without a slash may redirect and drop the JWT `Authorization` header. The backend also exposes a no-slash alias route.

### Frontend changes not visible
The frontend container does not hot-reload. Rebuild after React/TypeScript changes:
```bash
docker compose -f docker-compose.prod.yml build frontend
docker compose -f docker-compose.prod.yml up -d frontend
```

Backend changes hot-reload automatically via the `./backend:/code` volume mount.

### Intelligence Hub shows NO DATA
This is expected when no news articles match a symbol's NLP keywords. Refresh sentiment:
```bash
docker compose -f docker-compose.prod.yml exec backend python -c \
  "from app.services.nlp_service import run_nlp_analysis; run_nlp_analysis()"
```

### Validation metrics overflow or all zeros
- **Validated mode** (`/validation`, default): requires `validated_fund_runs` — run alpha optimization or `POST /api/validated/fund/run-all`.
- **Demo mode**: refresh with `update_validation_snapshots_job()` after `reset_institutional_demo.py`.
- Metrics use equity curves; values are sanitized on API response (max DD ≤ 100%).

### Research Lab global risk error
Ensure `global_risk_engine.py` orders `MarketSensitivityScore` by **`timestamp`** (not `computed_at`).

---

## 4. Contribution Guidelines

1.  Create a feature branch from `develop`: `git checkout -b feature/my-new-feature`
2.  Make your code changes.
3.  Ensure all tests pass locally.
4.  Commit your changes with a descriptive message.
5.  Push your branch and open a Pull Request against the `develop` branch.