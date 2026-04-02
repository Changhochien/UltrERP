# Story 1.2: Project Structure

Status: completed

## Story

As a developer,
I want a clear, consistent project structure,
So that I know where to put code and can navigate easily.

## Context

Based on the architecture, this is a **modular monolith** with FastAPI. The structure follows:
- **FastAPI modular monolith** with `app/`, `common/`, and `domains/` packages
- **Frontend source in `src/`** with the package manifest and toolchain files at repository root
- **Backend package in `backend/`**
- **Migrations in `migrations/`** with Alembic invoked from `backend/` via explicit config path

## Acceptance Criteria

**Given** the project structure is established
**When** I look at the codebase
**Then** frontend code is in `src/` with components/, pages/, domain/, hooks/, lib/ subdirectories
**And** backend code is in `backend/` with `app/`, `common/`, and `domains/` subdirectories
**And** migrations are in `migrations/`
**And** scripts are in `scripts/backup/` and `scripts/restore/`
**And** GitHub Actions workflows are in `.github/workflows/`
**And** empty directories have placeholder files where needed

## Technical Requirements

### Directory Structure

```
ultr-erp/
├── src/                              # Frontend source tree
│   ├── components/                   # Shared UI components
│   │   └── .gitkeep
│   ├── pages/                       # Route pages
│   │   └── .gitkeep
│   ├── domain/                      # Frontend domain types/utils
│   │   └── .gitkeep
│   ├── hooks/                       # React hooks
│   │   └── .gitkeep
│   ├── lib/                         # Third-party integrations
│   │   └── .gitkeep
│   ├── App.tsx                      # Root component
│   ├── main.tsx                     # Entry point
│   ├── index.css                    # Global styles
│   └── vite-env.d.ts
│
├── backend/                         # FastAPI (Python package)
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                  # FastAPI app entry
│   │   └── deps.py                  # Shared FastAPI dependencies
│   ├── common/
│   │   ├── __init__.py
│   │   ├── config.py                # Settings (pydantic-settings)
│   │   ├── database.py              # SQLAlchemy engine/session factory
│   │   ├── errors.py                # Shared error types
│   │   └── events.py                # Domain event bus placeholder
│   ├── domains/
│   │   ├── __init__.py
│   │   └── health/
│   │       ├── __init__.py
│   │       ├── routes.py            # /api/v1/health endpoint
│   │       └── service.py           # Health service placeholder
│   ├── tests/                      # Backend tests
│   │   ├── __init__.py
│   │   └── test_health.py
│   ├── pyproject.toml              # UV project config
│   └── .python-version            # uv managed python version (3.12)
│
├── migrations/                      # Alembic migrations
│   ├── alembic.ini
│   ├── env.py
│   └── versions/                   # Migration scripts
│       └── .gitkeep
│
├── scripts/                         # DevOps scripts
│   ├── backup/
│   │   ├── pg-dump.sh
│   │   └── rclone-sync.sh
│   └── restore/
│       └── pg-restore.sh
│
├── .github/
│   └── workflows/
│       └── ci.yml                 # CI pipeline
│
├── package.json                     # Root pnpm package.json
├── pnpm-workspace.yaml              # pnpm workspaces config
├── tsconfig.json                   # TypeScript config
├── tsconfig.node.json              # Vite config type-checking
├── vite.config.ts                  # Vite config
├── index.html
├── eslint.config.js
├── .env.example                   # Environment template
├── .gitignore
└── README.md
```

### Backend Modular Monolith Pattern

Per architecture Section 4.2:
```python
# Domain routers mounted inside the FastAPI app
api_router.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(api_router, prefix="/api/v1")
```

## Tasks

- [x] Task 1: Create frontend directory structure
  - [x] Subtask: Create all frontend subdirectories with .gitkeep files
  - [x] Subtask: Create source entry files under `src/`
- [x] Task 2: Create backend directory structure
  - [x] Subtask: Create `app/`, `common/`, and `domains/` packages with `__init__.py` files
  - [x] Subtask: Create backend/pyproject.toml
  - [x] Subtask: Create backend/.python-version
- [x] Task 3: Create migrations directory structure
  - [x] Subtask: Create alembic.ini
  - [x] Subtask: Create env.py
- [x] Task 4: Create scripts directory structure
  - [x] Subtask: Create scripts/backup/ and scripts/restore/
  - [x] Subtask: Create placeholder scripts
- [x] Task 5: Create GitHub Actions workflows directory
  - [x] Subtask: Create .github/workflows/ci.yml (placeholder)

## Dev Notes

### Critical Patterns

1. **Modular Monolith** - All domains are in single FastAPI process, mounted at `/api/v1/{domain}`
2. **pydantic-settings** - For configuration management (NOT dataclasses)
3. **SQLAlchemy 2.0** - With async support
4. **asyncpg** - With `statement_cache_size=0` for PgBouncer compatibility
5. **Tooling files at repo root** - `package.json`, `vite.config.ts`, `tsconfig*.json`, and `eslint.config.js` live at repository root

### Source References

- Architecture: Section 4.2 - FastAPI Modular Monolith
- Architecture: Section 3.1 - Technology Stack Table
- PRD: Technology decisions

## File List

- src/components/.gitkeep
- src/pages/.gitkeep
- src/domain/.gitkeep
- src/hooks/.gitkeep
- src/lib/.gitkeep
- backend/app/__init__.py
- backend/app/main.py
- backend/app/deps.py
- backend/common/__init__.py
- backend/common/config.py
- backend/common/database.py
- backend/common/errors.py
- backend/common/events.py
- backend/domains/__init__.py
- backend/domains/health/__init__.py
- backend/domains/health/routes.py
- backend/domains/health/service.py
- backend/tests/__init__.py
- backend/tests/test_health.py
- migrations/alembic.ini
- migrations/env.py
- backend/pyproject.toml
- backend/.python-version
- migrations/alembic.ini
- migrations/env.py
- scripts/backup/pg-dump.sh
- scripts/backup/rclone-sync.sh
- scripts/restore/pg-restore.sh
- .github/workflows/ci.yml
- package.json
- pnpm-workspace.yaml
- tsconfig.json
- tsconfig.node.json
- vite.config.ts
- index.html
- eslint.config.js

## Validation Evidence

- The scaffolded repository tree now exists with tracked placeholder files for empty frontend directories and importable Python packages under `backend/`.
- Frontend, backend, migration, script, and workflow roots were validated during Epic 1 execution and review.

## Review Outcome

- Empty frontend directories are now preserved in version control with `.gitkeep` files.
- Structure-only placeholders were replaced with the real script and workflow files created by the later Epic 1 stories.
