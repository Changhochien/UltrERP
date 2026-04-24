# Story 15.14: AC2 Holding Path Lineage — Record Lineage at Hold Time

Status: done

## Story

As a migration operator,
I want every row placed in `unsupported_history_holding` to also create a `canonical_record_lineage` entry at hold time,
so that held rows are visible in the lineage audit trail and the AC2 guarantee ("every source row has a lineage record") holds even for quarantine-path rows.

## Context

Story 15.1 AC2 requires that every source row produce a lineage record. Currently, rows routed to `unsupported_history_holding` (blank doc_number in receiving audit, payment-adjacent rows without a mapping) have **no lineage entry** at hold time. Lineage is only created if the drain path (`ap_payment_import.py`) successfully processes the row and calls `_upsert_lineage` after deleting it from holding.

This means permanently held rows (no drain path, or drain never invoked) have no lineage record — violating AC2's intent.

Full analysis: `_bmad-output/implementation-artifacts/15-1-ac2-lineage-gap.md`

## Acceptance Criteria

1. Given a row is placed in `unsupported_history_holding` (blank doc_number in `_import_legacy_receiving_audit` or payment-adjacent in `_hold_payment_adjacent_history`), when the row is held, then a corresponding entry is created in `canonical_record_lineage` with `canonical_table = '__holding__'` and the holding row's identifiers.
2. Given the drain path in `ap_payment_import.py` processes a held row, when the row is drained, then the existing lineage record is UPDATED (not duplicated) to reflect the canonical `supplier_payment` record, using `ON CONFLICT DO UPDATE` with the holding entry as the conflict target.
3. Given a held row has a lineage entry with `canonical_table = '__holding__'`, when an operator queries the lineage table, then they can identify which rows are in holding and which have been drained.

## Tasks / Subtasks

- [x] Task 1 (AC: 1)
  - [x] Added `_upsert_lineage_record_for_holding` function with `canonical_table = '__holding__'` sentinel value
  - [x] Modified `_try_upsert_holding_and_lineage` to call `_upsert_lineage_record_for_holding` after `hold_source_row` within the same savepoint
  - [x] Added unique index `canonical_record_lineage_source_identity` on `(batch_id, tenant_id, source_table, source_identifier, source_row_number)` for ON CONFLICT matching
- [x] Task 2 (AC: 2)
  - [x] Added `_lineage_record_query_for_holding` function with source-identifier-only conflict matching
  - [x] Updated `ap_payment_import.py` drain path to use `_lineage_record_query_for_holding` which UPDATE the holding lineage entry instead of creating duplicates
- [x] Task 3 (AC: 1, 2, 3)
  - [x] Updated `test_holding_state_created_on_blank_doc_number_hold` to expect `__holding__` lineage entry
  - [x] Updated `test_holding_state_created_on_payment_adjacent_hold` to expect `__holding__` lineage entry
  - [x] Updated `test_holding_state_payment_adjacent_no_col2` to expect `__holding__` lineage entry
  - [x] Updated `test_holding_and_drained_rows_are_distinguishable_holding` to expect `__holding__` lineage entry
  - [x] Added `test_drain_updates_holding_lineage_entry` for AC2 verification
  - [x] All 34 tests pass in `test_canonical.py` and `test_ap_payment_import.py`

## Dev Notes

- `canonical_table = '__holding__'` is a sentinel value. It indicates the row is in quarantine. When the drain path succeeds, the lineage entry's `canonical_table` should be updated to the real canonical table name (e.g., `supplier_payment`).
- The drain path (`ap_payment_import.py`) already calls `_upsert_lineage` after `_delete_holding_row`. The key change is ensuring the `ON CONFLICT` target matches the existing holding lineage entry, so the update replaces the `__holding__` entry rather than creating a new one.
- Alternatively, add `canonical_id = <holding_id>` to the holding lineage entry, and update it during drain. But using source identifiers as the conflict key is simpler and matches the existing lineage pattern.
- `_upsert_lineage` is in `canonical.py`. It should NOT need modification — the fix is in the call sites.

### Project Structure Notes

- Touch: `backend/domains/legacy_import/canonical.py` (`_import_legacy_receiving_audit` call site, `_hold_payment_adjacent_history` call site)
- Touch: `backend/domains/legacy_import/ap_payment_import.py` (`_upsert_supplier_payment` drain path)
- Touch: `backend/tests/domains/legacy_import/test_canonical.py` (new tests)
- Touch: `backend/tests/domains/legacy_import/test_ap_payment_import.py` (new/updated tests)

### References

- `_bmad-output/implementation-artifacts/15-1-ac2-lineage-gap.md`
- `backend/domains/legacy_import/canonical.py` (`_upsert_holding_row`, line 593)
- `backend/domains/legacy_import/canonical.py` (`_import_legacy_receiving_audit`, line 1501 — call site)
- `backend/domains/legacy_import/canonical.py` (`_hold_payment_adjacent_history`, line 2381 — call site)
- `backend/domains/legacy_import/canonical.py` (`_upsert_lineage`, line 544)
- `backend/domains/legacy_import/ap_payment_import.py` (`_upsert_supplier_payment`, line 403)

## Dev Agent Record

### Agent Model Used

sonnet

### Debug Log References

### Completion Notes List

**2026-04-24**: Story 15-14 implemented successfully.

Key changes:
1. **canonical.py**: Added `HOLDING_LINEAGE_TABLE = "__holding__"` sentinel constant, `_lineage_record_query_for_holding()` function with source-identifier-only conflict matching, `_upsert_lineage_record_for_holding()` async function, and unique index creation in `_ensure_canonical_support_tables()`.

2. **canonical.py**: Modified `_try_upsert_holding_and_lineage()` to call `_upsert_lineage_record_for_holding()` after `hold_source_row()` within the same savepoint, ensuring AC1 is satisfied.

3. **ap_payment_import.py**: Updated drain path to use `_lineage_record_query_for_holding()` instead of `_upsert_lineage_record()`, ensuring AC2 is satisfied (holding entry is UPDATEd not duplicated).

4. **Test updates**: Updated 4 existing tests to expect `__holding__` lineage entries and added 1 new test `test_drain_updates_holding_lineage_entry` verifying AC2.

### File List

**Modified:**
- `backend/domains/legacy_import/canonical.py`
- `backend/domains/legacy_import/ap_payment_import.py`
- `backend/tests/domains/legacy_import/test_canonical.py`
- `backend/tests/domains/legacy_import/test_ap_payment_import.py`
