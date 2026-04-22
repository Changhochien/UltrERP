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

# CLAUDE.md

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.
