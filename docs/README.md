# NEXA Platform Documentation

Central index for all platform documentation. Last updated: **June 2026** (Phase 4–6 + Alpha Optimization + validation hardening).

## Quick Links

| Document | Description |
|----------|-------------|
| **[INSTITUTIONAL_PERFORMANCE_REPORT.md](./INSTITUTIONAL_PERFORMANCE_REPORT.md)** | Post-optimization validated fund results |
| **[ALPHA_OPTIMIZATION_PROGRAM.md](./ALPHA_OPTIMIZATION_PROGRAM.md)** | Alpha optimization master plan (phases 1–9) |
| **[PHASE1_ALPHA_DIAGNOSTIC.md](./PHASE1_ALPHA_DIAGNOSTIC.md)** | Root-cause diagnostic report |
| **[BRAND_GUIDE.md](./BRAND_GUIDE.md)** | Logo-aligned colors for slides & marketing |
| **[PHASE6_INSTITUTIONAL_READINESS.md](./PHASE6_INSTITUTIONAL_READINESS.md)** | Phase 6 — performance engine, live validation, alpha evidence |
| **[PHASE5_AUDIT_REPORT.md](./PHASE5_AUDIT_REPORT.md)** | Phase 5 audit — demo vs validated, metric integrity |
| [PHASE5_ROADMAP.md](./PHASE5_ROADMAP.md) | Institutional readiness + Alpha evidence protocol (complete) |
| **[PHASE4_AUTONOMOUS_FUND_MANAGER.md](./PHASE4_AUTONOMOUS_FUND_MANAGER.md)** | Phase 4 complete reference — treasury, LNX, funds, productionization |
| [PHASE4_API_QUICK_REFERENCE.md](./PHASE4_API_QUICK_REFERENCE.md) | Phase 4 REST endpoints with request/response samples |
| [HISTORICAL_VALIDATION_AUDIT.md](./HISTORICAL_VALIDATION_AUDIT.md) | Demo vs validated surfaces, fund backtest audit |
| [VALIDATION_ROADMAP_STATUS.md](./VALIDATION_ROADMAP_STATUS.md) | 5-stage institutional validation roadmap |
| [VALIDATION_REPORT.md](./VALIDATION_REPORT.md) | Validation framework, metrics, PDF reports, data sources |
| [API_REFERENCE.md](./API_REFERENCE.md) | Complete REST API endpoint catalog |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | System architecture, containers, core flows |
| [SYSTEM_ARCHITECTURE.md](./SYSTEM_ARCHITECTURE.md) | High-level diagrams and subsystem map |
| [EXECUTION_ARCHITECTURE.md](./EXECUTION_ARCHITECTURE.md) | Exchange adapters, autonomous executor |
| [DATABASE.md](./DATABASE.md) | Schema, tables, relationships, migrations |
| [DEMO_GUIDE.md](./DEMO_GUIDE.md) | Persona-driven demo scripts |
| [DEVELOPMENT.md](./DEVELOPMENT.md) | Local setup, tests, migrations, troubleshooting |
| [DEPLOYMENT.md](./DEPLOYMENT.md) | Production deployment guide |

## Archive

Historical phase reports live in [`archive/`](./archive/) and are not maintained for current features.

## Platform Status (June 2026)

| Area | Status |
|------|--------|
| **Phase 4 — Autonomous Multi-Asset Fund Manager** | ✅ Complete |
| **Phase 4 — LNX Treasury Economics & Settlement** | ✅ Complete |
| **Phase 5 — Validated performance layer** | ✅ Complete |
| **Phase 5 — Research Lab + Global Risk Engine** | ✅ Complete |
| **Phase 6 — Institutional metric engine** | ✅ Complete |
| **Alpha Optimization Program** | ✅ Complete (best configs in `validated_fund_runs`) |
| **Validated reference portfolios** | ✅ `LNX-*-VALIDATED` on `admin@google.com` |
| **Fund Performance — validated primary + admin demo toggle** | ✅ `/fund-performance` |
| **Validation — validated default + demo toggle** | ✅ `/validation` |
| **Validation metrics integrity (equity-based)** | ✅ Fixed June 2026 |
| Institutional demo reset script | ✅ `reset_institutional_demo.py` |
| Intelligence Hub (coverage-aware sentiment) | ✅ `/intelligence` |

**Rollout note:** Phase 4 autonomous multi-asset execution is gated by `global_settings.autonomous_v2_enabled` (default `false`). Validated portfolios are excluded from the autonomous manager loop.

## Data Provenance

Every performance surface labels its source:

| Label | Meaning |
|-------|---------|
| `DEMO` | Seeded client demo ledger (`LNX-*-001` … `003`) |
| `VALIDATED_HISTORICAL` | Fund backtests on aligned `market_bars` |
| `PAPER_LIVE` | Long-running autonomous paper trading |
| `LIVE_CAPITAL` | Reserved for future real-capital deployment |

### Where each label appears

| Surface | Default | Admin toggle |
|---------|---------|--------------|
| `/fund-performance` | VALIDATED_HISTORICAL | **Show demo comparison** → Demo Ledger column |
| `/validation` | VALIDATED_HISTORICAL | **Demo Ledger** toggle |
| `/portfolios/LNX-*-VALIDATED` | VALIDATED_HISTORICAL | — |
| `/portfolios/LNX-*-00x` | DEMO operational ledger | — |

## Demo Accounts

All demo users use password **`password123`** (after institutional reset):

| Email | Role | Portfolios |
|-------|------|------------|
| `client1@google.com` | client | LNX-PRESERVE-001, LNX-BALANCED-001, LNX-ALPHA-001 |
| `client2@google.com` | client | …-002 variants |
| `client3@google.com` | client | …-003 variants |
| `admin@google.com` | admin | Full access + **LNX-*-VALIDATED** reference portfolios |
| `operator1@google.com` | operator | Ops + validation + research lab |
| `risk1@google.com` | risk_manager | Treasury + risk + research lab |

## Key UI Routes

### Client (Fund-First)

| Route | Purpose |
|-------|---------|
| `/dashboard` | Fund performance, treasury contributions, LNX |
| `/funds` | Invest; target weekly & monthly per fund |
| `/fund-performance` | Validated historical metrics (admin: demo comparison) |
| `/portfolios/{id}` | Returns, risk, settlements, allocation, trades |
| `/allocation` | Live allocation engine weights |
| `/lnx` | LNX index, treasury NAV, reserve ratio |
| `/intelligence` | AI pulse with coverage-aware sentiment |
| `/market-intelligence` | Multi-asset pulse + news |
| `/simulator` | Growth projections from fund weekly targets |

### Operator / Risk / Admin

| Route | Purpose |
|-------|---------|
| `/research-lab` | Historical validation, global risk, alpha evidence |
| `/alpha-evidence` | Alpha 20% monthly evidence dashboard |
| `/fund-performance` | Run optimization / backtests; demo comparison |
| `/treasury` | Treasury pools + analytics + routing ledger |
| `/validation` | Validated Historical (default) or Demo Ledger |
| `/reports` | Weekly/monthly portfolio PDF reports |
| `/portfolios/LNX-*-VALIDATED` | Institutional reference portfolio detail |

## API Namespaces

| Prefix | Purpose | Roles |
|--------|---------|-------|
| `/api/funds/` | Fund invest, performance | client + staff |
| `/api/validated/` | Backtests, optimization, global risk | operator, risk, admin |
| `/api/validation/` | Snapshots (`data_source=validated\|demo`) | operator, risk, admin |
| `/api/institutional/` | Live validation, treasury verify, reports | mixed |
| `/api/treasury/pools/summary` | Client-safe pool balances | all authenticated |

Interactive docs: `http://localhost:8000/docs`

## Bootstrap & Demo Reset

```bash
docker compose -f docker-compose.prod.yml up --build -d
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head
docker compose -f docker-compose.prod.yml exec backend python scripts/seed_phase4.py
docker compose -f docker-compose.prod.yml exec backend python scripts/reset_institutional_demo.py --confirm

# Alpha optimization (admin) — or use UI button on /fund-performance
docker compose -f docker-compose.prod.yml exec backend python scripts/run_alpha_optimization.py --phase all

# Regenerate LNX-*-VALIDATED portfolios from best runs
docker compose -f docker-compose.prod.yml exec backend python -c \
  "from app.core.database import SessionLocal; from app.validation.validated_institutional_regenerator import ValidatedInstitutionalRegenerator; db=SessionLocal(); ValidatedInstitutionalRegenerator(db).regenerate_all(); db.close()"

docker compose -f docker-compose.prod.yml build frontend && docker compose -f docker-compose.prod.yml up -d frontend
```

## Known Integration Notes

1. **Portfolio list URL** — Use `GET /api/portfolios/` (trailing slash).
2. **Treasury client access** — Clients use `/api/treasury/pools/summary`, not `/api/treasury/pools`.
3. **Validation default** — `GET /api/validation/snapshots` defaults to `data_source=validated`.
4. **Fund demo comparison** — `GET /api/validated/fund/latest/{id}?include_demo=true` (admin/operator only).
5. **Frontend rebuild** — Required after React changes in prod compose.

## Brand & Presentations

See **[BRAND_GUIDE.md](./BRAND_GUIDE.md)** for logo-aligned hex colors, gradients, and slide themes.
