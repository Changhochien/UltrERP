---
name: ultr-erp-ops
description: Use when the operator says "/UltrERP-ops", "check ERP health", "is the ERP running", "check database connectivity", "check tables", "check alembic", "check users", "seed settings", "create admin user", or "run full setup on an existing ERP". This skill is for ongoing operator tasks on an already-bootstrapped ERP. For first-time setup, use /UltrERP-init instead. For migration management, use /UltrERP-migrate.
argument-hint: "[check-db|check-alembic|check-tables|check-users|check-health|seed-settings|create-admin|full-setup]"
---

Use this skill for ongoing ERP operator tasks on an already-bootstrapped UltrERP environment.

This skill is an orchestration wrapper around the backend Python runtime and Alembic CLI. Do not reimplement migration logic, seeding logic, or user-creation logic in Markdown or ad hoc scripts. Always route setup actions through the reviewed commands in [the command map](./command-map.md).

## What this skill checks and manages

- **Database connectivity** — can we reach the PostgreSQL instance?
- **Alembic state** — what migration revision is currently applied?
- **App tables** — do the core domain tables exist?
- **App settings** — are they seeded (non-sensitive defaults)?
- **Users** — does at least one user exist?
- **Legacy staging data** — does any legacy-import batch exist?

## Operating rules

1. **Detection is always free.** Any `check-*` sub-command (check-db, check-alembic, check-tables, check-users, check-legacy, check-health) reads state only and never modifies anything. Run these without confirmation.
2. **Write actions require explicit confirmation.** `seed-settings`, `create-admin`, and `full-setup` are write actions. Before running them, show exactly what will happen, what command will be run, and what the expected outcome is. Wait for the operator to say "yes", "run it", or equivalent before proceeding.
3. **Use the stable invocation path.** All backend commands run from `backend/` so the repo's `uv` environment and import paths are correct.
4. **Handle partial state.** If a step is already done (e.g., migrations applied), skip it and report "already done". Never re-run write actions on already-complete steps unless the operator explicitly asks.
5. **Fail with remediation.** If a step fails (e.g., duplicate user), report the error, suggest a remediation, and ask whether to retry or skip.
6. **Offer legacy import as the final optional step.** After `full-setup` completes, offer to run the `/legacy-import` skill for staging historical data. Do not run it automatically.

## Confirmation checklist before any write action

Show the operator:
- What will be done
- The exact command that will be run
- What success looks like
- What failure could look like and how to recover

Then wait for explicit confirmation.

## Suggested execution flows

### Health check on a running system
1. Run `check-health` and summarize: DB connectivity, alembic head, table count, user count, legacy batch count.
2. Report which components are present vs. missing.

### Full first-time setup (only after /UltrERP-init has been run)
1. Confirm with the operator that `/UltrERP-init` was already run.
2. Confirm and run `seed-settings` to seed non-sensitive app settings.
3. Confirm and run `create-admin` (prompt for email, display name, password first).
4. Offer `check-health` to verify the system is ready.
5. Offer to run `/legacy-import` if legacy staging data exists or will be imported.

## Sub-commands

| Sub-command | Writes? | Description |
|---|---|---|
| `check-db` | No | Test DB connectivity, report schema list |
| `check-alembic` | No | Report current Alembic revision |
| `check-tables` | No | List which app tables exist |
| `check-users` | No | Report user count and roles |
| `check-legacy` | No | Report whether any legacy-import batches exist |
| `check-health` | No | Run all check-* sub-commands and summarize |
| `seed-settings` | **Yes** | Call `seed_settings_if_empty` |
| `create-admin` | **Yes** | Prompt for admin credentials, then insert user |
| `full-setup` | **Yes** | Run seed-settings then create-admin in sequence |

## Invoking other skills

- After `full-setup`, offer: `Use the /legacy-import skill to stage and import historical data.`
- For Alembic migration management (upgrade, downgrade, stamp, resolve heads), use `/UltrERP-migrate` instead.
- For first-time bootstrap, use `/UltrERP-init` instead.

Use this skill for ERP environment operations only. Do not use it for first-time setup (use `/UltrERP-init`), for legacy data import (use `/legacy-import`), or for migration management (use `/UltrERP-migrate`).
