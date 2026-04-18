# AC2 Lineage Gap: unsupported_history_holding vs. main staging path

## Summary

Rows routed to `unsupported_history_holding` do NOT create a `canonical_record_lineage`
entry at the time they are held. Lineage is only recorded if the drain path
(`ap_payment_import.py`) successfully processes the row and calls `_upsert_lineage`
*after* deleting it from holding. This creates a visibility gap for rows that are
held permanently or for rows that are held but the drain path is never invoked.

## Lineage fields in each path

### Main staging path (canonical.py `_upsert_lineage`, line 516)

Records the following fields in `canonical_record_lineage`:

| Field | Source |
|---|---|
| tenant_id | caller |
| batch_id | caller |
| canonical_table | caller |
| canonical_id | caller |
| source_table | caller |
| source_identifier | caller |
| source_row_number | caller |
| import_run_id | caller |

All canonical domain insert functions (customers, suppliers, products, warehouses,
inventory, orders, invoices, order_lines, invoice_lines, stock_adjustments,
supplier_invoices, supplier_invoice_lines) call `_upsert_lineage` after the
canonical record is upserted. The source_row_number is pulled from the staging
table's `_source_row_number` column.

### Holding path (canonical.py `_upsert_holding_row`, line 565)

Records the same identifying fields in `unsupported_history_holding`:

| Field | Column in holding table |
|---|---|
| tenant_id | tenant_id |
| batch_id | batch_id |
| domain_name | domain_name |
| source_table | source_table |
| source_identifier | source_identifier |
| source_row_number | source_row_number |
| import_run_id | import_run_id |
| payload (full row) | payload JSONB |

**Key difference: `_upsert_holding_row` does NOT call `_upsert_lineage`.**
No entry is written to `canonical_record_lineage` when a row is placed in holding.

### Drain path (ap_payment_import.py `_upsert_supplier_payment`, line 403)

1. Calls `_delete_holding_row` (line 483) to remove the row from `unsupported_history_holding`
2. Calls `_upsert_lineage` (line 492) to record the lineage for the canonical `supplier_payment`

This means **only rows that successfully drain** get a lineage entry.

## What's missing

1. **No lineage record at hold time.** A row placed in `unsupported_history_holding`
   has no corresponding entry in `canonical_record_lineage`. There is no way to
   query "show me the lineage for all held rows" via the lineage table.

2. **No lineage record for permanently held rows.** If a row remains in holding
   indefinitely (no drain path exists or drain was never invoked), no lineage
   record will ever exist for it.

3. **Holding table lacks `import_run_id` linkage to canonical_record_lineage.**
   The holding table's `import_run_id` column is set when the row is placed in
   holding. However, since no lineage entry is created at hold time, there is
   no canonical_record_lineage record with the same `import_run_id` to join against.

## Functional issues arising from the gap

- **Debugging held rows requires direct holding table queries.** There is no
  lineage-driven path to understand "which import run placed this row in holding."

- **Retry/recovery has no lineage anchor.** A manual recovery procedure cannot
  use `canonical_record_lineage` to determine whether a held row corresponds to
  a specific batch/tenant/run combination — it must query `unsupported_history_holding`
  directly.

- **AC2 auditability gap.** If AC2 requires that every source row have a lineage
  record, held rows fail this requirement until they are successfully drained.

## Code locations requiring changes to fix

1. **`canonical.py:_upsert_holding_row`** (line 565): Add an `_upsert_lineage` call
   inside this function, so every row placed in holding also gets a lineage entry
   with `canonical_table = 'unsupported_history_holding'` (or a sentinel value like
   `'__holding__'`). Alternatively, have the callers invoke `_upsert_lineage` directly
   before or after calling `_upsert_holding_row`.

2. **`canonical.py:_import_legacy_receiving_audit`** (line 1499): The call to
   `_upsert_holding_row` at line 1501 has no accompanying `_upsert_lineage` call.
   Even if lineage is added inside `_upsert_holding_row`, this call site should be
   reviewed — the holding row is a different canonical type (receiving_audit holding)
   vs. the drainable payment holding (tbsspay/tbsprepay).

3. **`canonical.py:_hold_payment_adjacent_history`** (line 2355): Same — the
   `_upsert_holding_row` call at line 2381 has no accompanying `_upsert_lineage`.

4. **`ap_payment_import.py:_upsert_supplier_payment`** (line 403): After the
   `_delete_holding_row` and `_upsert_lineage` calls, the lineage record's
   `source_row_number` is correctly passed. No change needed here — this is
   the drain path and already correctly calls `_upsert_lineage`.

## Recommendation

Add `_upsert_lineage` calls at each `_upsert_holding_row` call site, using a
`canonical_table` value of `'__holding__'` (or a domain-specific value like
`'receiving_audit_holding'` or `'payment_history_holding'`) so that:

- Every held row has a lineage record from the moment it is placed in holding.
- The lineage record uses the same `import_run_id`, `batch_id`, `tenant_id`
  as the holding record, enabling joins.
- The drain path's `_upsert_lineage` call updates the existing lineage record
  (ON CONFLICT ... DO UPDATE) rather than creating a duplicate.

The `source_row_number` is available at all holding call sites because it is
pulled from the staging table's `_source_row_number` column, which is populated
by the staging layer (staging.py line 906).