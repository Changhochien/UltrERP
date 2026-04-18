# Story 15.14: AC2 Holding Path Lineage — Record Lineage at Hold Time

Status: ready-for-dev

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

- [ ] Task 1 (AC: 1)
  - [ ] Read `_upsert_holding_row` (canonical.py:593) — it does NOT call `_upsert_lineage`
  - [ ] Read both callers of `_upsert_holding_row`:
    - `_import_legacy_receiving_audit` (line 1501, blank doc_number path)
    - `_hold_payment_adjacent_history` (line 2381, payment-adjacent rows)
  - [ ] Add `_upsert_lineage` calls at both call sites, using `canonical_table = '__holding__'` and the same identifiers as the holding row
  - [ ] The holding row's `row_identity` (source_row_number or line_number) should be passed as `source_row_number`
- [ ] Task 2 (AC: 2)
  - [ ] In `ap_payment_import.py:_upsert_supplier_payment`, after deleting from holding and before/after upserting the canonical record, change the existing `_upsert_lineage` call to use `ON CONFLICT DO UPDATE` targeting `(tenant_id, batch_id, canonical_table, source_table, source_identifier)` where `canonical_table = '__holding__'` — this updates the holding lineage entry to point to the canonical record
  - [ ] Or: add a new `_upsert_lineage` call with `canonical_table = 'supplier_payment'` using the same source identifiers so the conflict fires on the existing holding-row entry and updates it
- [ ] Task 3 (AC: 1, 2, 3)
  - [ ] Add focused tests: one for blank doc_number holding creates a `__holding__` lineage entry, one for payment-adjacent holding, one for drain path updating the holding lineage entry
  - [ ] Run the existing legacy-import test suite to confirm no regressions

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

### File List
