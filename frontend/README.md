# LionexAI Frontend

Next.js 14 · TypeScript · Tailwind CSS · TradingView Lightweight Charts

Premium institutional UI for the NEXA / LionexAI platform — dark charcoal theme with **metallic gold + emerald/teal** accents from the brand logo.

## Design system

Tokens live in `src/app/globals.css`. Presentation colors: [docs/BRAND_GUIDE.md](../docs/BRAND_GUIDE.md).

| Token | Hex | Use |
|-------|-----|-----|
| `--primary-gold` | `#CFA43B` | Brand accent, CTAs |
| `--primary-emerald` | `#0FA89A` | AI / positive accent |
| `--background-base` | `#070809` | Page background |
| `--text-primary` | `#F6F8FB` | Headlines |

Fonts: **Inter** (body), **Sora** (display), **JetBrains Mono** (metrics).

## Run (production compose)

```bash
docker compose -f docker-compose.prod.yml up -d
# After UI changes:
docker compose -f docker-compose.prod.yml build frontend
docker compose -f docker-compose.prod.yml up -d frontend
```

Open [http://localhost:3000](http://localhost:3000).

## Run (dev compose)

```bash
docker compose up -d
```

Backend must be running at `NEXT_PUBLIC_API_URL` (default `http://localhost:8000`).

## Key routes

| Route | Purpose |
|-------|---------|
| `/fund-performance` | Validated historical funds; admin demo comparison toggle |
| `/validation` | Validated Historical (default) or Demo Ledger |
| `/portfolios/[id]` | Portfolio detail — validated reference portfolios show backtest stats |
| `/funds` | Client invest flow |
| `/treasury`, `/lnx` | Treasury & index |
| `/research-lab`, `/alpha-evidence` | Staff validation tools |

## API client

- `src/lib/api.ts` — core API + `validatedAPI`
- `src/lib/api/validation.ts` — validation snapshots (`data_source=validated|demo`)

## Typecheck

```bash
docker compose -f docker-compose.prod.yml exec frontend npx tsc --noEmit
```

## Demo login

`admin@google.com` / `password123` — see [docs/README.md](../docs/README.md).
