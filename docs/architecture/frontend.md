# Frontend Architecture

Next.js 14 App Router in `frontend/src/`.

---

## Structure

```
frontend/src/
├── app/              # Routes (page.tsx per route)
├── components/       # UI, charts, shell, intelligence
├── contexts/         # UserContext
├── lib/              # api.ts, types, format, chartTheme
└── middleware.ts     # Auth + role routing
```

---

## API Client

`lib/api.ts` — typed fetch helpers for all backend namespaces. Uses `NEXT_PUBLIC_API_URL` in browser, `INTERNAL_API_URL` in SSR.

WebSocket: `/api/ws/market` for live ticks on dashboard.

---

## Role-Based Navigation

Defined in `components/shell/TerminalSidebar.tsx`:

| Role | Primary routes |
|------|----------------|
| Client | Dashboard, Funds, Fund Performance, Portfolios, LNX, Intelligence |
| Operator | System Ops, Validation, Research Lab, Execution, Backtest |
| Risk Manager | Risk, Treasury, Mandates, Stress Test, Validation |
| Admin | All of the above + Executive, Users, Settings |

---

## Design System

CSS tokens in `app/globals.css` — gold/teal brand on charcoal. Tailwind maps via `tailwind.config.ts`.

Charts use `lib/chartTheme.ts` for axis colors aligned with `--text-muted`.

See [Brand Guide](../guides/brand_guide.md).

---

## Production Build

Frontend in `docker-compose.prod.yml` requires **rebuild** after UI changes (no hot-reload volume).

```bash
docker compose -f docker-compose.prod.yml build frontend
docker compose -f docker-compose.prod.yml up -d frontend
```

See [Platform Pages Guide](../guides/platform_pages.md) for per-route API mapping.
