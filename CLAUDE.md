# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build Commands

```bash
pnpm install          # Install frontend dependencies
pnpm dev              # Start frontend dev server (Vite on :5173)
pnpm build            # TypeScript check + Vite build
pnpm lint             # ESLint
pnpm test             # Vitest unit tests

cd backend && uv sync
uv run pytest         # Backend tests
uv run alembic -c ../migrations/alembic.ini upgrade head  # Run migrations
```

Single test: `pnpm test -- <file>` or `uv run pytest tests/<path>`

## Architecture

### Frontend (src/)
- React 19 + Vite, TypeScript, Tailwind CSS v4, Radix UI
- Routing: React Router v7
- State: React Hook Form for forms; TanStack Table for data tables
- Charts: Recharts + Visx
- i18n: i18next with browser language detection
- Desktop: Tauri (src-tauri/)

**Key directories:**
- `src/pages/` — Route-level page components
- `src/components/` — Shared UI components
- `src/domain/` — Domain-specific page sections and hooks
- `src/lib/api/` — API client functions (one file per domain)
- `src/hooks/` — Shared React hooks

### Backend (backend/)
- FastAPI + SQLAlchemy 2.0 (async, PostgreSQL via asyncpg)
- Alembic for migrations (`migrations/`)
- MCP server via FastMCP at `/mcp/`
- Event-driven handlers in domain modules

**Key directories:**
- `backend/domains/<domain>/` — Routes, schemas, services, handlers per domain
- `backend/common/` — Shared: config, database, models, events
- `backend/app/main.py` — FastAPI app factory, all routers registered here

### Shared
- `src/lib/api/` frontend callers mirror `backend/domains/<domain>/routes.py` endpoints
- API prefix is `/api/v1/<domain>` (health, auth, customers, dashboard, intelligence, invoices, inventory, orders, payments, purchases, reports, settings)
- LINE webhook at `/api/v1/line`

## Database
- PostgreSQL 18+, connection via `DATABASE_URL` env var
- Default: `postgresql+asyncpg://ultr_erp@localhost:5432/ultr_erp`
- Migrations: `migrations/alembic.ini`

## Environment
- Copy `.env.example` to `.env` and set `JWT_SECRET`
- `VITE_API_PROXY_TARGET` overrides backend proxy address
- `CORS_ORIGINS` JSON array for local origins

## MCP
Backend exposes MCP at `/mcp/`. Setup: `ULTRERP_MCP_API_KEY=dev-readonly-key ./scripts/setup-mcp-clients.sh`
