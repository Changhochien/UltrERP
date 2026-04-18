# Story 15.10: Live Legacy Source Compatibility Contract

Status: review

## Story

As a migration operator and ERP engineer,
I want the live legacy source contract verified before we build against it,
So that dual-source staging uses a proven read-only connector and a stable row-serialization contract.

## Acceptance Criteria

1. Given `LEGACY_DB_*` settings are configured, when a compatibility probe runs against the live legacy PostgreSQL 8.2 source over Tailscale, then the repo proves or rejects the chosen connector in read-only mode and captures the table discovery, column metadata, and streaming-read behaviors needed by staging.
2. Given the live-source connector contract is approved, when staging code consumes rows from the live source, then the contract defines how `NULL`, numerics, strings, and date-like values are serialized for the shared raw loader and preserves the text semantics needed for existing lineage fields such as `_legacy_pk`.
3. Given the legacy source must remain read-only, when the probe or adapter connects, then it issues no write operations and fails fast with explicit diagnostics for unsupported types, incompatible server behavior, or connector/runtime incompatibility.
4. Given the connector decision is still open at planning time, when the story is completed, then the implementation artifacts document the approved connector choice and any driver-specific constraints without committing secrets into the repo.

## Tasks / Subtasks

- [x] Task 1 (AC: 1, 3)
  - [x] Add `LEGACY_DB_*` configuration fields to the backend settings surface with correct sensitivity metadata and safe defaults.
  - [x] Implement a focused compatibility probe that can authenticate, enumerate `public` tables, inspect column metadata, and stream at least one table in read-only mode.
- [x] Task 2 (AC: 2, 3)
  - [x] Define the live-row serialization contract for values that will flow into raw staging.
  - [x] Add helper tests that prove the serialization contract preserves current staging text semantics and fails clearly on unsupported cases.
- [x] Task 3 (AC: 4)
  - [x] Record the approved connector choice and source contract in the dual-source staging spec or a linked implementation artifact.
  - [x] Document the operational guardrail that live-source credentials are environment-only and never persisted in planning artifacts.

### Review Findings

- [ ] [Review][Patch] Block runtime persistence for `legacy_db_password` so the settings API cannot store it in `app_settings` or the audit log [backend/domains/settings/service.py:122]
- [ ] [Review][Patch] Redact real live-source row previews from the probe artifact before committing customer, product, and transaction data into repo history [_bmad-output/implementation-artifacts/15-10-live-legacy-source-compatibility-probe.md:56]

## Dev Notes

- The current staging pipeline assumes file-backed discovery plus a legacy text-row parser in `backend/domains/legacy_import/staging.py`.
- The live source is PostgreSQL 8.2.23, so connector compatibility must be proven before the main implementation assumes the existing target-side asyncpg patterns can be reused unchanged.
- The contract should preserve the downstream assumptions already used by normalization, mapping, canonical import, and validation: staged rows are text-first and keyed by `_batch_id` plus `_source_row_number`.

### Project Structure Notes

- Expected code touch points are `backend/common/config.py`, `backend/domains/legacy_import/staging.py`, and focused tests under `backend/tests/domains/legacy_import/`.
- This story should not add the `live-stage` CLI yet; it is the architecture and compatibility gate for the later implementation story.

### References

- `backend/docs/SPEC-dual-source-staging.md`
- `backend/domains/legacy_import/staging.py`
- `backend/common/config.py`
- `backend/tests/domains/legacy_import/test_staging.py`
- `_bmad-output/planning-artifacts/epic-15.md`

## Dev Agent Record

### Agent Model Used

GPT-5.4

### Implementation Plan

- Add live-source `LEGACY_DB_*` settings and sensitivity metadata, including the now-proven `LEGACY_DB_CLIENT_ENCODING=BIG5` default.
- Add a focused asyncpg compatibility probe that authenticates in read-only mode, discovers `public` tables, loads column metadata, and streams text-projected rows.
- Lock the approved text-first serialization contract with tests, then record the connector decision and credential guardrails in the dual-source staging spec plus a linked implementation artifact.

### Debug Log References

- Added `LEGACY_DB_HOST`, `LEGACY_DB_PORT`, `LEGACY_DB_USER`, `LEGACY_DB_PASSWORD`, `LEGACY_DB_NAME`, and `LEGACY_DB_CLIENT_ENCODING` to `backend/common/config.py` with `legacy_import` settings metadata and password masking.
- Added live-source probe and text-projection helpers in `backend/domains/legacy_import/staging.py`; focused validation passed with `cd backend && uv run pytest tests/test_config.py tests/domains/settings/test_routes.py tests/domains/legacy_import/test_staging.py -q` (`43 passed`).
- Verified the broader touched slice with `cd backend && uv run pytest tests/domains/legacy_import tests/test_config.py tests/domains/settings/test_routes.py -q` (`125 passed`) and `cd backend && uv run ruff check common/config.py domains/legacy_import/staging.py tests/test_config.py tests/domains/settings/test_routes.py tests/domains/legacy_import/test_staging.py` (`All checks passed`).
- Ran the live compatibility probe against the PostgreSQL `8.2.23` source over Tailscale: `asyncpg 0.31.0` connected successfully in read-only mode, `server_encoding=SQL_ASCII`, `client_encoding=BIG5`, `public` tables=`528`, and the required staging tables all streamed successfully with metadata-driven `::text` projection.
- Initial probe attempts with the default UTF-8 client encoding failed with `UnicodeDecodeError`, which is now documented as the driver-specific reason `LEGACY_DB_CLIENT_ENCODING=BIG5` is mandatory.
- Attempted full backend `cd backend && uv run pytest -q`, but collection is currently blocked by an existing duplicate `test_service.py` module-name conflict between `tests/domains/intelligence/` and `tests/domains/product_analytics/`.
- Attempted full backend `cd backend && uv run ruff check`, but the repo currently has many unrelated pre-existing lint violations outside the Story 15.10 files.

### Completion Notes List

- Approved connector choice: `asyncpg 0.31.0` is compatible with the live PostgreSQL `8.2.23` source when the session is read-only and `client_encoding=BIG5`.
- Added the live-source compatibility probe, supported-type whitelist, and metadata-driven `COALESCE(column::text, 'NULL')` row contract needed by later dual-source staging stories.
- Added helper coverage proving the text projection preserves current staging semantics, including `_legacy_pk` hashing compatibility with the existing file parser.
- Sanitized the dual-source staging spec, added safe `.env.example` placeholders, and recorded the live probe results in `_bmad-output/implementation-artifacts/15-10-live-legacy-source-compatibility-probe.md` without persisting secrets.
- Full backend pytest and full backend Ruff remain blocked by unrelated pre-existing repo issues outside the Story 15.10 change set.

### File List

- `.env.example`
- `backend/common/config.py`
- `backend/domains/legacy_import/staging.py`
- `backend/docs/SPEC-dual-source-staging.md`
- `backend/tests/test_config.py`
- `backend/tests/domains/settings/test_routes.py`
- `backend/tests/domains/legacy_import/test_staging.py`
- `_bmad-output/implementation-artifacts/15-10-live-legacy-source-compatibility-probe.md`
- `_bmad-output/implementation-artifacts/15-10-live-legacy-source-compatibility-contract.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

### Change Log

- 2026-04-18: Added live-source `LEGACY_DB_*` settings metadata, the focused asyncpg compatibility probe, and the metadata-driven text-row contract for future dual-source staging.
- 2026-04-18: Validated the contract against the live PostgreSQL `8.2.23` source, documented the required `BIG5` client encoding, removed committed credential examples from the spec, and added a linked probe artifact with rerun guidance.
