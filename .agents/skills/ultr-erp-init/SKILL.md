---
name: ultr-erp-init
description: Use when the operator says "/UltrERP-init", "init the ERP", "bootstrap the ERP", "first time setup", "fresh install", or "set up from scratch". This skill bootstraps a freshly cloned UltrERP repo — installing dependencies, creating the database, generating the schema, and creating the first admin user. For ongoing operator tasks after init, use /UltrERP-ops. For migration management, use /UltrERP-migrate. For legacy data import, use /legacy-import.
argument-hint: "[check|prereqs|install|init-db|generate-migrations|full] [--env <path>]"
---

Use this skill when bootstrapping a freshly cloned UltrERP repository from scratch.

This skill is idempotent and safe to re-run. It detects already-installed components and skips them.

## What this skill does (in order)

1. **Check prereqs** — PostgreSQL running, required tools installed
2. **Install dependencies** — frontend (`pnpm install`) and backend (`uv sync`)
3. **Create `.env`** — scaffold from `.env.example` if missing
4. **Create database** — `CREATE DATABASE ultr_erp` if it doesn't exist
5. **Generate migrations** — `alembic revision --autogenerate` from SQLAlchemy models
6. **Apply migrations** — `alembic upgrade head`
7. **Seed settings** — default app settings
8. **Create admin user** — prompt for email, display name, password

## Operating rules

1. **Detection is always free.** Any `check-*` or `prereqs` step reads state only. Run without confirmation.
2. **Write actions require confirmation** for database creation, migration generation, admin user creation. Show exactly what will happen and wait for "yes" or "run it".
3. **Follow the order.** Skipping steps causes failures downstream.
4. **Idempotent.** If a step is already done, report "already done" and skip.
5. **Fail with remediation.** Report the error and suggest how to fix it.

## Confirmation checklist before any write action

Show:
- What will be done
- The exact command that will be run
- What success looks like
- What failure could look like and how to recover

Then wait for explicit confirmation.

## Sub-commands

| Sub-command | Writes? | Description |
|---|---|---|
| `prereqs` | No | Check PostgreSQL, pnpm, uv, Python versions |
| `install` | **Yes** | Install frontend and backend dependencies |
| `init-db` | **Yes** | Create the `ultr_erp` database if it doesn't exist |
| `generate-migrations` | **Yes** | Run `alembic revision --autogenerate` to create schema from models |
| `full` | **Yes** | Run the complete init sequence (prereqs → install → init-db → migrate → seed → admin) |

## Execution flow: `full`

1. Run `prereqs` — report what is/isn't installed
2. Confirm and run `install` — pnpm install + uv sync
3. Confirm and run `init-db` — create database
4. Confirm and run `generate-migrations` — create initial schema migration
5. Confirm and run `apply-migrations` — `alembic upgrade head`
6. Confirm and run `seed-settings` — seed default app settings
7. Confirm and run `create-admin` — prompt for email, display name, password, then insert user
8. Offer `check-health` via `/UltrERP-ops` to verify
9. Offer `/legacy-import` if legacy staging data will be imported

## Prereqs check commands

```bash
# PostgreSQL
pg_isready -h localhost -p 5432 2>&1 || echo "PostgreSQL not running"

# pnpm
pnpm --version 2>&1

# uv
uv --version 2>&1

# Python
python3 --version 2>&1

# uv sync (check backend deps)
cd backend && uv sync --dry-run 2>&1

# .env exists
ls .env.example 2>&1 && echo "env example exists"
```

## Database creation command

```bash
psql postgresql://ultr_erp@localhost:5432/postgres -c "SELECT 1 FROM pg_database WHERE datname = 'ultr_erp'" 2>&1
# If row not found:
psql postgresql://ultr_erp@localhost:5432/postgres -c "CREATE DATABASE ultr_erp" 2>&1
```

## Migration generation command

```bash
cd backend && uv run alembic -c ../migrations/alembic.ini revision --autogenerate -m "initial_schema"
```

## Migration apply command

```bash
cd backend && uv run alembic -c ../migrations/alembic.ini upgrade head
```

## Invoking other skills

- After `full` completes, use `/UltrERP-ops` for health checks.
- After `full` completes, offer `/legacy-import` for historical data.
- For migration management (upgrade, downgrade, stamp, resolve heads), use `/UltrERP-migrate`.

Use this skill only for first-time bootstrap. For ongoing operations use `/UltrERP-ops`.
