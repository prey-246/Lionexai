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
    Use the production Docker Compose file, which is configured with hot-reloading for a seamless development experience.
    ```bash
    docker-compose -f docker-compose.prod.yml up --build -d
    ```

4.  **Verify Services:**
    After a minute, check that all containers are running and healthy.
    ```bash
    docker-compose -f docker-compose.prod.yml ps
    ```

5.  **Access the Platform:**
    - **Frontend:** `http://localhost:3000`
    - **Backend API Docs:** `http://localhost:8000/docs`

6.  **Seed Demo Data (Optional but Recommended):**
    To populate the platform with a rich set of demo data, run the seeder script inside the backend container.
    ```bash
    docker exec -it nexa_backend_prod python scripts/seed_demo_environment.py
    ```

---

## 2. Common Development Tasks

### Viewing Logs
Tailing logs is essential for debugging.
```bash
# View logs for the backend
docker-compose -f docker-compose.prod.yml logs -f nexa_backend_prod

# View logs for the frontend
docker-compose -f docker-compose.prod.yml logs -f nexa_frontend_prod
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

    **Validation migrations** (required for Stages 1–4):
    - `b7c3e1a42f90` — extended trade fields
    - `c4d8e2f91a03` — validation snapshot history

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
| Algo executor | 60s | `scripts/algo_executor.py` |
| Validation snapshots | 15 min + startup | `validation_service.update_validation_snapshots_job()` |
| Daily archive | 00:05 UTC | Same job, `archive_snapshots_to_history()` |
| Price updater | 1 hour | `main.py` scheduler |
| News scraper | 1 hour | `main.py` scheduler |
| NLP analyzer | 10 min | `main.py` scheduler |

---

## 3. Contribution Guidelines

1.  Create a feature branch from `develop`: `git checkout -b feature/my-new-feature`
2.  Make your code changes.
3.  Ensure all tests pass locally.
4.  Commit your changes with a descriptive message.
5.  Push your branch and open a Pull Request against the `develop` branch.