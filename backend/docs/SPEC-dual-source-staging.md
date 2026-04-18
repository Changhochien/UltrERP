# SPEC: Dual-Source Legacy Staging

## Status
Draft for Stories 15.11-15.12, with the Story 15.10 connector contract validated.

## Background

The legacy import system currently supports a single data source: a pre-existing `.sql` dump file processed through `extract → stage → normalize → canonical`. This document specifies adding support for a second data source: a live PostgreSQL 8.2.23 legacy DB accessed over Tailscale.

## Goals

1. Stage data from a live legacy DB via Tailscale (no file intermediary)
2. Maintain full backward compatibility with the existing file-based pipeline
3. Allow both approaches to coexist — CLI chooses which source per run

## Story 15.10 Compatibility Decision

- Approved connector: `asyncpg` `0.31.0`
- Verified source: PostgreSQL `8.2.23` over Tailscale
- Required session guardrails:
  - `default_transaction_read_only=on`
  - `client_encoding=BIG5`
- Verified live source characteristics:
  - `server_encoding=SQL_ASCII`
  - `public` schema exposes `528` tables
  - Story 15.1 required tables were present: `tbscust`, `tbsstock`, `tbsslipx`, `tbsslipdtx`, `tbsstkhouse`
- Approved staging-row contract:
  - Supported live column types are `character varying`, `character`, `text`, `numeric`, `integer`, `smallint`, `double precision`, `date`, and `timestamp with time zone`
  - Live reads must project each source column as `COALESCE(column::text, 'NULL')`
  - The shared raw loader therefore receives the same text-first contract as file staging: empty string stays empty, database `NULL` becomes the literal text `NULL`, numerics preserve PostgreSQL text output, and date-like values arrive as PostgreSQL text dates/timestamps
  - `_legacy_pk` continues hashing the serialized text row, so file-backed and live-backed staging preserve the same lineage semantics when the textual values match
- Fail-fast guardrails:
  - Unsupported live column types are rejected before streaming
  - Non-string projected values are rejected before they can reach the raw loader
  - Credentials stay environment-only; do not persist them in docs, story artifacts, or committed config

See the linked probe artifact for the validated sample-table evidence and rerun instructions: [`15-10-live-legacy-source-compatibility-probe.md`](../../_bmad-output/implementation-artifacts/15-10-live-legacy-source-compatibility-probe.md).

## Architecture

### Existing flow (file-based)
```
.sql file (Big5) → extract → CSV/JSON files → stage (asyncpg) → raw_legacy schema
```

### New flow (live DB)
```
Legacy DB (Tailscale) → stage (asyncpg) → raw_legacy schema
```

Both flows use the same `raw_legacy` schema and the same `legacy_import_runs` / `legacy_import_table_runs` control tables.

## Configuration

### New environment variables (common/config.py)

```env
# Live legacy DB (Tailscale access)
LEGACY_DB_HOST=<tailscale-host-or-ip>
LEGACY_DB_PORT=5432
LEGACY_DB_USER=<legacy-user>
LEGACY_DB_PASSWORD=<legacy-password>
LEGACY_DB_NAME=<legacy-database>
LEGACY_DB_CLIENT_ENCODING=BIG5
```

These live alongside `DATABASE_URL` (the UltrERP target DB).
They must be supplied via environment variables or an untracked local `.env`, never committed into planning or implementation artifacts.

## Data flow

```
legacy-import live-stage --batch-id <id> [--tables tbsstock,tbacompany]

1. Connect to legacy DB via asyncpg (Tailscale IP:port)
2. List all tables in legacy DB (SELECT tablename FROM pg_tables WHERE schemaname='public')
3. For each table (or selected subset):
   a. Build a metadata-driven `::text` projection for supported column types
   b. Stream rows using an asyncpg cursor inside a read-only transaction
   c. Feed the shared raw loader text rows that preserve the existing file-stage contract
4. Track each table in legacy_import_table_runs
5. Return StageBatchResult (same shape as file-based)
```

**Story 15.10 boundary**: The connector contract is now proven, but the final shared orchestration shape remains a Story 15.11 decision. The validated invariant for later implementation is that any live adapter must produce the same text-first rows and lineage semantics as the existing file-based stage.

## CLI changes

### New subcommand: `live-stage`

```bash
legacy-import live-stage \
  --batch-id <string> \
  [--tables tbsstock,tbacompany] \   # optional filter; if omitted, stage all tables
  [--tenant-id <uuid>] \
  [--schema <string>]                 # defaults to raw_legacy
```

### Output

Same `StageBatchResult` and console summary as `stage`.

## Backward compatibility

- `legacy-import stage` (file-based) works unchanged
- `legacy-import extract` works unchanged
- All existing subcommands unchanged

## New dependencies

- `asyncpg` (already used by staging.py for the target DB connection — no new dep)
- No new packages needed

## File changes

| File | Change |
|------|--------|
| `common/config.py` | Add `LegacyDbSettings` class with `LEGACY_DB_*` fields |
| `domains/legacy_import/staging.py` | Add `run_live_import()` and `discover_live_tables()` |
| `domains/legacy_import/cli.py` | Add `live_stage_parser` and `_run_live_stage()` |
| `.env.example` | Document `LEGACY_DB_*` variables |

## Error handling

- Legacy DB connection failure → raise with clear message ("Cannot connect to legacy DB at $HOST — check Tailscale and credentials")
- Individual table fetch failure → log error, continue with remaining tables, mark failed table in `LegacyImportTableRun`
- Same batch rollback semantics as file-based stage (per-table, not per-batch)

## Security notes

- `LEGACY_DB_PASSWORD` is a secret — same sensitivity level as `JWT_SECRET`
- Connection uses no TLS (legacy PostgreSQL 8.2 doesn't support modern TLS) — Tailscale provides the network-level security
- `LEGACY_DB_*` vars should never be committed to git, planning docs, or implementation artifacts
- `LEGACY_DB_CLIENT_ENCODING=BIG5` is required for this SQL_ASCII source when using `asyncpg`
