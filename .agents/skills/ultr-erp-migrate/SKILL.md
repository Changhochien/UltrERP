---
name: ultr-erp-migrate
description: Use when the operator says "/UltrERP-migrate", "check alembic", "check migrations", "run migrations", "resolve migration heads", "upgrade migrations", "downgrade migrations", "stamp alembic", or "show alembic history". This skill manages Alembic migration lifecycle — checking state, upgrading, downgrading, resolving conflicts, and stamping. For first-time setup, use /UltrERP-init. For ongoing ERP operations, use /UltrERP-ops.
argument-hint: "[check|history|heads|branches|upgrade|downgrade|stamp|resolve-heads] [--revision <rev>]"
---

Use this skill for Alembic migration lifecycle management on an already-bootstrapped UltrERP environment.

This skill is an orchestration wrapper around the Alembic CLI. Do not reimplement Alembic logic in Markdown or ad hoc scripts.

## What this skill manages

- **Alembic state** — current revision, history, branches, heads
- **Migration upgrade** — apply pending migrations
- **Migration downgrade** — roll back migrations
- **Stamp** — mark DB as at a specific revision without running migrations
- **Resolve heads** — merge or resolve conflicting migration heads

## Operating rules

1. **Read operations are always free.** `check`, `history`, `heads`, `branches` read state only. Run without confirmation.
2. **Write operations require confirmation.** `upgrade`, `downgrade`, `stamp`, `resolve-heads` modify the DB or migration state. Show exactly what will happen and wait for "yes" or "run it".
3. **Use the stable invocation path.** All alembic commands run from `backend/` directory: `cd backend && uv run alembic -c ../migrations/alembic.ini ...`
4. **Multiple heads require resolution.** If `upgrade head` fails with "multiple heads", use `heads` to see both, then `resolve-heads` to merge them before upgrading.
5. **Warn before downgrade.** Downgrading can lose data. Always confirm the target revision and explain the risk.

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
| `check` | No | Detect bootstrap state; report Alembic revision if bootstrapped |
| `history` | No | Show full migration history |
| `heads` | No | Show all current heads |
| `branches` | No | Show branch structure |
| `upgrade` | **Yes** | Run `alembic upgrade head` |
| `downgrade` | **Yes** | Run `alembic downgrade <revision>` (requires `--revision`) |
| `stamp` | **Yes** | Stamp DB to a specific revision without running migrations (requires `--revision`) |
| `resolve-heads` | **Yes** | Merge multiple heads into one (requires `--revision`) |

### Bootstrap detection (runs before all sub-commands)

Before executing any sub-command, the skill checks whether the environment is bootstrapped:

```bash
cd backend && uv run python -c "
import asyncio
from common.database import AsyncSessionLocal
from sqlalchemy import text

async def check_bootstrap():
    async with AsyncSessionLocal() as s:
        result = await s.execute(text('''
            SELECT COUNT(*) FROM information_schema.tables
            WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
        '''))
        count = result.scalar()
        print('app_table_count:', count)

asyncio.run(check_bootstrap())
"
```

- **app_table_count == 0** (only `alembic_version` or nothing at all): the DB is **not bootstrapped**. Skip all sub-commands and prompt the operator to run `/UltrERP-init` first.
- **app_table_count > 0**: proceed with the requested sub-command normally.

This applies to `check`, `history`, `heads`, `branches`, `upgrade`, `downgrade`, `stamp`, and `resolve-heads` — all of them require a bootstrapped environment to be meaningful.

## Alembic command reference

```bash
# Check current revision
cd backend && uv run alembic -c ../migrations/alembic.ini current

# Show full history
cd backend && uv run alembic -c ../migrations/alembic.ini history

# Show all heads
cd backend && uv run alembic -c ../migrations/alembic.ini heads

# Show branch structure
cd backend && uv run alembic -c ../migrations/alembic.ini branches

# Upgrade to head (single head)
cd backend && uv run alembic -c ../migrations/alembic.ini upgrade head

# Upgrade to specific head (multiple heads)
cd backend && uv run alembic -c ../migrations/alembic.ini upgrade <branchname>@head

# Upgrade to specific revision
cd backend && uv run alembic -c ../migrations/alembic.ini upgrade <revision>

# Downgrade one step
cd backend && uv run alembic -c ../migrations/alembic.ini downgrade -1

# Downgrade to base
cd backend && uv run alembic -c ../migrations/alembic.ini downgrade base

# Stamp to a specific revision (no migration run)
cd backend && uv run alembic -c ../migrations/alembic.ini stamp <revision>

# Generate a new migration
cd backend && uv run alembic -c ../migrations/alembic.ini revision -m "description"
```

## Resolve multiple heads

If `upgrade head` fails with "multiple heads":

1. Run `heads` to see both heads and their branch points
2. Show the operator the two heads and explain the conflict
3. Options:
   - **Merge into one head:** `cd backend && uv run alembic -c ../migrations/alembic.ini merge <head1> <head2> -m "merge"`
   - **Upgrade to specific head:** `cd backend && uv run alembic -c ../migrations/alembic.ini upgrade <branchname>@head`
4. After resolving, run `upgrade head` to apply

## Required run report

After any command finishes, report:
- exact command that was run
- exit code (0 = success, non-zero = failure)
- what was detected or changed
- what to do next

## Invoking other skills

- For first-time bootstrap (generate schema migrations), use `/UltrERP-init`.
- For ongoing ERP health checks and user management, use `/UltrERP-ops`.
- For legacy data import, use `/legacy-import`.

Use this skill for Alembic migration management only. Do not use it for first-time setup (`/UltrERP-init`) or ongoing operations (`/UltrERP-ops`).
