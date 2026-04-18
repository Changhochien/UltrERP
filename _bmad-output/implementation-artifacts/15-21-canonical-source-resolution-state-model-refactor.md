# Story 15.21: Canonical Source Resolution State Model Refactor

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a migration operator,
I want hold and drain state modeled explicitly outside `canonical_record_lineage`,
so that source-row transitions remain lossless, replay-safe, and crash-consistent as the legacy import pipeline evolves.

## Context

Story 15.13 hardened `canonical_record_lineage` for batch reruns, and Story 15.14 added immediate lineage coverage for held rows by writing sentinel `canonical_table = '__holding__'` entries. That closes the short-term audit gap, but it also leaves the system using one mutable lineage row for two different jobs:

- canonical destination lineage
- current resolution state for a source row

That coupling creates the long-term architectural smell behind the two remaining lineage issues:

- the current `ON CONFLICT` behavior can overwrite one source row's prior logical state when the destination changes
- holding cleanup and drain resolution are conceptually one state transition, but today they are expressed as separate table operations instead of a single first-class transition model

This story is the profound fix: introduce an explicit source-resolution state model plus an append-only transition log, keep `canonical_record_lineage` focused on canonical destination lineage, and move hold/drain behavior behind one shared transaction-owned boundary.

## Acceptance Criteria

1. Given a batch-scoped legacy source row is processed, when the import pipeline persists its current resolution, then exactly one migration-owned state row exists for that source identity in a new table such as `raw_legacy.source_row_resolution` (or an approved equivalent), and that row exposes explicit status such as `holding`, `resolved`, or `failed` rather than inferring state from `canonical_record_lineage.canonical_table`.
2. Given a row is held, drained, retried, or manually repaired, when the transition completes, then an append-only event row is written to a new table such as `raw_legacy.source_row_resolution_events` capturing batch, tenant, run, source identity, prior state, new state, and canonical or holding references, and prior transitions remain queryable instead of being overwritten.
3. Given a held row drains into a canonical target, when the shared transition helper executes, then the canonical write, current-state update, event append, and `unsupported_history_holding` cleanup commit atomically in one transaction, and any failure leaves the row in its previous consistent state.
4. Given historical batches already contain `canonical_record_lineage` and `unsupported_history_holding` rows, when the migration and backfill run, then the new state/event tables are populated without losing tenant, batch, or run provenance, existing canonical lineage remains queryable for canonical records, and ambiguous source-identity collisions fail loudly with actionable diagnostics instead of being silently merged.
5. Given operators or validation code need to know whether a row is currently held or resolved, when they query the post-refactor system, then they use the new source-resolution state surface instead of `canonical_table='__holding__'`, and no new sentinel `__holding__` lineage rows are written after cutover.
6. Given the legacy-import regression slice is run after the refactor, when focused tests exercise hold creation, drain transition, rerun idempotency, migration backfill, and rollback-on-failure behavior, then the new state model is covered without regressing existing batch-scoped canonical lineage guarantees.

## Tasks / Subtasks

- [x] Task 1: Define the durable data model and migration plan (AC: 1, 2, 4, 5)
  - [x] Add a new current-state table in `raw_legacy` for one row per batch-scoped source identity.
  - [x] Add a new append-only event table in `raw_legacy` for hold, resolve, retry, and repair transitions.
  - [x] Decide and document the authoritative source-row identity before coding. Current tables disagree: `canonical_record_lineage` keys on `(batch_id, tenant_id, canonical_table, source_table, source_identifier)` while `unsupported_history_holding` uniqueness also includes `source_row_number`. The new model must choose one consistent identity shape and enforce it everywhere.
  - [x] Write an Alembic migration that creates the new tables and backfills current rows from `canonical_record_lineage` plus `unsupported_history_holding`.
  - [x] Make the migration fail loudly if backfill detects ambiguous duplicates for the chosen source identity.

- [x] Task 2: Introduce one shared source-resolution transition boundary (AC: 1, 2, 3, 5)
  - [x] Add a backend-owned helper or module for source-resolution transitions. Prefer extracting this into a dedicated legacy-import module rather than expanding `canonical.py` further.
  - [x] Route hold writes through the shared helper so holding payload persistence, current-state updates, and event appends happen together.
  - [x] Route drain writes through the same helper so canonical record persistence, current-state updates, event appends, and holding cleanup happen together.
  - [x] Preserve the existing transaction boundary in `run_ap_payment_import`; do not weaken it by introducing partial commits inside the new helper.
  - [x] Stop encoding hold state as `canonical_table = '__holding__'` for new writes after cutover.

- [x] Task 3: Re-scope `canonical_record_lineage` to canonical lineage only (AC: 1, 4, 5)
  - [x] Update lineage-writing call sites so `canonical_record_lineage` continues to describe canonical destination mapping, not temporary quarantine state.
  - [x] Remove or retire new `__holding__` sentinel writes once the source-resolution state model is active.
  - [x] Decide whether historical sentinel rows remain as legacy evidence or are migrated out; whichever choice is made, document it and keep reader behavior deterministic.
  - [x] Ensure Story 15.13's batch-scoped idempotency guarantee remains intact for canonical lineage after the refactor.

- [x] Task 4: Update readers, repair surfaces, and operator docs (AC: 4, 5)
  - [x] Update validation and operator-facing read paths to query current hold/resolved status from the new state table.
  - [x] Review batch reset and repair scripts that currently depend on `canonical_record_lineage` semantics, and update them if they need the new state/event tables.
  - [x] Update legacy-import docs to explain the new contract: current state lives in the resolution table, transition history lives in the event table, canonical lineage remains canonical only.
  - [x] Document any manual recovery/reconciliation query patterns against the new tables.

- [x] Task 5: Add focused migration and behavioral coverage (AC: 3, 4, 6)
  - [x] Add focused tests for:
    - hold path writes current state plus event
    - drain path atomically updates current state, appends event, and removes holding payload
    - rerunning the same batch stays idempotent at both the canonical lineage layer and the source-resolution current-state layer
    - migration backfill from existing lineage and holding rows
    - backfill failure on ambiguous source identity collisions
    - rollback behavior when the drain transition fails mid-operation
  - [x] Keep existing Story 15.13 and 15.14 regressions green or update them deliberately to the new contract rather than weakening assertions.

## Dev Notes

### Story Intent

- This is an infrastructure refactor of the shared legacy-import control model, not just an AP payment tweak.
- The core correction is architectural: separate "what is the current resolution state of this source row?" from "which canonical record(s) does this source row map to?".
- A minimal patch such as adding another unique constraint or another explanatory comment is not sufficient for this story.

### Scope Boundaries

- In scope:
  - new source-resolution current-state table
  - new source-resolution event log
  - migration/backfill from current lineage and holding rows
  - shared transition helper for hold and drain flows
  - reader and docs updates needed to use the new state model
- Out of scope:
  - redesigning the business rules of AP payment import
  - adding scheduled reconciliation jobs beyond what is needed to support the new state model
  - changing the live canonical targets defined in the target matrix
  - removing `canonical_record_lineage` entirely

### Existing Repo Constraints

- `backend/domains/legacy_import/canonical.py` currently creates both `canonical_record_lineage` and `unsupported_history_holding`, and it already contains helper-level support surfaces for hold and lineage writes.
- `backend/domains/legacy_import/ap_payment_import.py` already runs inside `async with connection.transaction()` at the command level. Preserve that atomicity and align the new transition helper to it.
- `backend/domains/legacy_import/validation.py` joins through `canonical_record_lineage` for batch validation today; any reader that needs current hold/resolved status must move to the new state table instead of continuing to read `__holding__`.
- `backend/scripts/reset_legacy_import_batch.py` and `backend/scripts/repair_inventory_snapshot_warehouses.py` both read or mutate `canonical_record_lineage`; review them carefully so the refactor does not silently strand cleanup or repair workflows.

### Design Guardrails

- `canonical_record_lineage` should describe canonical destination lineage only after this story. Do not keep using it as a mutable state machine.
- The new current-state row should be batch-scoped and tenant-scoped, just like the existing import control tables.
- The event table should be append-only. If a row transitions from hold to resolved, preserve the prior hold event instead of updating it away.
- Make the source identity decision explicit before writing migrations. Current code uses `source_identifier` in lineage and `source_identifier + source_row_number` in holding uniqueness; the new tables must not inherit both shapes inconsistently.
- Keep raw source payload storage in `unsupported_history_holding`; the new state/event tables should store references and state metadata, not duplicate large payload blobs.
- Preserve replay safety from Story 15.5 and batch-scoped lineage idempotency from Story 15.13.
- If you need a staged rollout, prefer this sequence:
  1. create and backfill new tables
  2. switch writers to the new state/event model
  3. switch readers from sentinel lineage to the state table
  4. block new `__holding__` sentinel writes

### Suggested Implementation Surfaces

- Schema and migrations:
  - `migrations/versions/` (new Alembic revision)
- Legacy-import domain code:
  - `backend/domains/legacy_import/canonical.py`
  - `backend/domains/legacy_import/ap_payment_import.py`
  - `backend/domains/legacy_import/validation.py`
  - consider adding `backend/domains/legacy_import/source_resolution.py` (or similar) for the shared transition helper
- Repair and reset scripts:
  - `backend/scripts/reset_legacy_import_batch.py`
  - `backend/scripts/repair_inventory_snapshot_warehouses.py`
- Tests:
  - `backend/tests/domains/legacy_import/test_canonical.py`
  - `backend/tests/domains/legacy_import/test_ap_payment_import.py`
  - targeted migration or script tests as needed

### Testing Notes

- Prefer focused unit/integration tests around the new transition helper and backfill logic rather than trying to prove the entire live import workflow in one test.
- Keep existing fake-connection lineage tests aligned with the new contract. If sentinel `__holding__` expectations disappear, replace them with explicit state/event assertions rather than deleting coverage.
- Add at least one test that proves a failed drain transition rolls back holding cleanup and state changes together.

### References

- `_bmad-output/planning-artifacts/epic-15.md` - Stories 15.13 and 15.14, plus this story's epic placement
- `_bmad-output/implementation-artifacts/15-13-ac4-batch-rerun-idempotency.md`
- `_bmad-output/implementation-artifacts/15-14-ac2-holding-lineage.md`
- `_bmad-output/implementation-artifacts/15-1-ac4-idempotency-analysis.md`
- `_bmad-output/implementation-artifacts/15-1-ac2-lineage-gap.md`
- `docs/legacy/canonical-import-target-matrix.md` - current lineage and holding contract
- `docs/legacy/ap-payment-model.md` - payment holding boundary and lineage expectations
- `backend/domains/legacy_import/canonical.py` - support-table DDL, `_upsert_lineage`, holding helpers, and canonical import writers
- `backend/domains/legacy_import/ap_payment_import.py` - drain path and transaction boundary
- `backend/domains/legacy_import/validation.py` - current lineage-backed validation reads
- `backend/scripts/reset_legacy_import_batch.py`
- `backend/scripts/repair_inventory_snapshot_warehouses.py`

## Dev Agent Record

### Agent Model Used

gpt-5.4

### Debug Log References

### Completion Notes List

- Added `backend/domains/legacy_import/source_resolution.py` and rewired canonical/AP payment writers so hold and drain transitions update current state, append immutable events, and clean up holding payloads atomically.
- Added Alembic revision `f3b4c5d6e7f8_add_source_row_resolution_tables.py` to widen the lineage PK with `source_row_number`, create/backfill `source_row_resolution` and `source_row_resolution_events`, and fail loudly on ambiguous source-identity collisions.
- Updated validation, batch reset, repair tooling, and legacy-import docs so current hold/resolved state is read from the new resolution surface while historical `__holding__` lineage rows remain legacy evidence only.
- Validation: `uv run pytest tests/domains/legacy_import/test_source_resolution.py tests/domains/legacy_import/test_ap_payment_import.py tests/domains/legacy_import/test_canonical.py tests/domains/legacy_import/test_validation.py tests/test_reset_legacy_import_batch.py tests/test_source_row_resolution_migration.py` -> `55 passed`.

### File List

- `_bmad-output/implementation-artifacts/15-21-canonical-source-resolution-state-model-refactor.md`
- `backend/domains/legacy_import/source_resolution.py`
- `backend/domains/legacy_import/canonical.py`
- `backend/domains/legacy_import/ap_payment_import.py`
- `backend/domains/legacy_import/validation.py`
- `backend/scripts/reset_legacy_import_batch.py`
- `backend/scripts/repair_inventory_snapshot_warehouses.py`
- `backend/tests/domains/legacy_import/test_source_resolution.py`
- `backend/tests/domains/legacy_import/test_ap_payment_import.py`
- `backend/tests/domains/legacy_import/test_canonical.py`
- `backend/tests/domains/legacy_import/test_validation.py`
- `backend/tests/test_reset_legacy_import_batch.py`
- `backend/tests/test_source_row_resolution_migration.py`
- `docs/legacy/canonical-import-target-matrix.md`
- `docs/legacy/ap-payment-model.md`
- `migrations/versions/f3b4c5d6e7f8_add_source_row_resolution_tables.py`

