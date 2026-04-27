# Story 15.13: AC4 Batch Rerun Idempotency — Prevent Duplicate Lineage Records

Status: done

## Story

As a migration operator,
I want a batch rerun to be idempotent at the lineage layer,
so that re-running the same import batch does not create duplicate canonical_record_lineage entries.

## Context

Story 15.1 (AC4) stated "a stage rerun alone cannot create duplicate canonical records." The canonical record layer (`stock_adjustment` etc.) is protected by deterministic UUIDs + `ON CONFLICT (id) DO NOTHING`. However, the `canonical_record_lineage` table's unique constraint and `ON CONFLICT` target use `(tenant_id, batch_id, canonical_table, canonical_id, source_table, source_identifier)`.

While `run_id` is stored as a column, it is NOT in the unique constraint. This means:
- Within the same batch: rerun → conflict → DO UPDATE → no duplicate (correct)
- Across different batch_ids: same source row → separate lineage entry per batch (intentional)

The risk is subtle: if `canonical_id` is not fully deterministic across all code paths, or if a future change introduces a non-deterministic element, the absence of `run_id` in the constraint means the wrong `import_run_id` could be overwritten on a rerun. Adding `batch_id` to the unique constraint (making it `(batch_id, tenant_id, canonical_table, source_table, source_identifier)`) is the belt-and-suspenders fix that guarantees AC4 holds regardless of `canonical_id` determinism assumptions.

Full analysis: `_bmad-output/implementation-artifacts/15-1-ac4-idempotency-analysis.md`

## Acceptance Criteria

1. Given a batch is imported and `_import_legacy_receiving_audit` runs, when the same batch is re-run, then `canonical_record_lineage` has exactly one entry per (canonical_table, source_table, source_identifier) per batch — no duplicates.
2. Given the lineage unique constraint includes `batch_id`, when a different batch processes the same source row, then each batch produces its own lineage entry (batch-scoped deduplication, not cross-batch).
3. Given the migration changes the lineage unique constraint, when the migration runs, then existing data is preserved and backfill is not required.

## Tasks / Subtasks

- [x] Task 1 (AC: 1, 2)
  - [x] Read the current `_upsert_lineage` function (canonical.py:544) and its `ON CONFLICT` clause
  - [x] Change the unique constraint and `ON CONFLICT` target to include `batch_id`: `(batch_id, tenant_id, canonical_table, source_table, source_identifier)`
  - [x] Verify all callers of `_upsert_lineage` pass `batch_id` (they already do — it's a caller parameter)
- [x] Task 2 (AC: 3)
  - [x] Write an Alembic migration to change the unique constraint on `canonical_record_lineage` from the current shape to the new shape
  - [x] The migration must be backward-compatible: existing rows must satisfy the new constraint (they should, since each (batch_id, ...) tuple is already unique)
  - [x] Test the migration on a dev database with existing lineage data
- [x] Task 3 (AC: 1, 2)
  - [x] Add a focused test that imports the same batch twice and asserts `canonical_record_lineage` has no duplicate entries for that batch
  - [x] Run the existing legacy-import test suite to confirm no regressions

## Dev Notes

- The fix is in `_upsert_lineage` (canonical.py:544) and a new Alembic migration.
- `batch_id` is already passed to `_upsert_lineage` by all callers — no caller changes needed.
- The `DO UPDATE` currently overwrites `source_row_number` and `import_run_id`. With the new constraint, reruns will still DO UPDATE (correct — latest run's metadata wins).
- The `ON CONFLICT` target change must match the new unique constraint exactly.

### Project Structure Notes

- Touch: `backend/domains/legacy_import/canonical.py` (`_upsert_lineage`)
- Touch: `backend/migrations/versions/` (new Alembic revision)
- Touch: `backend/tests/domains/legacy_import/test_canonical.py` (new test)

### References

- `_bmad-output/implementation-artifacts/15-1-ac4-idempotency-analysis.md`
- `backend/domains/legacy_import/canonical.py` (`_upsert_lineage`, line 544)
- `backend/domains/legacy_import/canonical.py` (`CanonicalImportResult`, line 27)

## Dev Agent Record

### Agent Model Used

sonnet

### Debug Log References

### Completion Notes List

- Implemented AC4 batch rerun idempotency by removing `canonical_id` from the lineage primary key and ON CONFLICT target. The constraint is now `(batch_id, tenant_id, canonical_table, source_table, source_identifier)`.
- Changed DDL PRIMARY KEY in `_ensure_canonical_support_tables` (canonical.py:372) from `(tenant_id, batch_id, canonical_table, canonical_id, source_table, source_identifier)` to `(batch_id, tenant_id, canonical_table, source_table, source_identifier)`.
- Changed `_upsert_lineage` ON CONFLICT target (canonical.py:570) to match new PK column order: `(batch_id, tenant_id, canonical_table, source_table, source_identifier)`.
- Added `test_run_canonical_import_batch_rerun_is_idempotent_at_lineage_layer` which verifies the ON CONFLICT clause excludes `canonical_id` and includes `batch_id`.
- Updated `FakeCanonicalConnection._fake_lineage_rows` key to reflect new PK column order (batch_id first, no canonical_id).
- Alembic migration `ee6f8a7b3c1d_change_lineage_pk_to_batch_id_first.py` drops old PK and adds new one with `batch_id` first.
- All 120 legacy_import tests pass, plus 2 reset_batch tests.

### File List

- `backend/domains/legacy_import/canonical.py` — DDL PK and ON CONFLICT target changed
- `backend/tests/domains/legacy_import/test_canonical.py` — Fake lineage key updated, new idempotency test added
- `migrations/versions/ee6f8a7b3c1d_change_lineage_pk_to_batch_id_first.py` — new Alembic migration
