# Contributing

Guidelines for contributing to LionexAI.

---

## Getting Started

1. Fork / clone the repository
2. Follow [Developer Setup](./developer_setup.md)
3. Create a feature branch from `main`

---

## Code Conventions

- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2.0, type hints where practical
- **Frontend:** TypeScript, Next.js App Router, Tailwind with design tokens from `globals.css`
- **Migrations:** Alembic — one revision per schema change
- **Provenance:** Never mix `VALIDATED_HISTORICAL` metrics into operational treasury without explicit separation

---

## Pull Request Checklist

- [ ] Focused diff — no unrelated changes
- [ ] API changes reflected in `docs/api/api_reference.md` if endpoints added/changed
- [ ] Platform behavior changes reflected in relevant `docs/platform/` doc
- [ ] Frontend UI changes tested; prod compose rebuild noted if needed
- [ ] No secrets in commits

---

## Documentation

When adding features, update:

- [Platform docs](../platform/) for user-visible behavior
- [Platform Pages Guide](./platform_pages.md) for new routes/metrics
- [API Reference](../api/api_reference.md) for new endpoints

Do not add phase-specific implementation logs to the main docs tree — use `docs/archive/` for historical notes.

---

## Demo Data

Use institutional reset for consistent demo state:

```bash
docker compose exec backend python scripts/reset_institutional_demo.py --confirm
```

Demo accounts: `admin@google.com`, `client1@google.com` — password `password123`.

See [Demo Guide](./demo_guide.md).
