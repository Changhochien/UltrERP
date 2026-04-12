# Story 18.2: Legacy Sales Adjustment Backfill

Status: pending

## Story

As a migration operator,
I want historical sales order lines from the legacy system to appear as outbound stock adjustments in UltrERP,
So that the inventory audit trail reflects both goods received AND goods shipped for the full legacy period.

## Problem Statement

The legacy system had no formal stock reservation or fulfillment step — when a sales invoice was entered, the inventory snapshot (`tbsstkhouse.fcurqty`) was not updated atomically. The current migration imports `tbsslipx`/`tbsslipdtx` as `Order`/`OrderLine` records, but `StockAdjustment` records with `ReasonCode.SALES_RESERVATION` are not created.

Without outbound adjustment records, the inventory history is incomplete: you can see what came in (Story 18.1) but not what went out.

The source data is `tbsslipdtx.col_23` — a signed quantity where positive = outbound sale, negative = return.

## Solution

A standalone backfill script `backfill_sales_issues.py` that:

1. Reads `raw_legacy.tbsslipx` (sales header, `col_3 = invoice_date`) JOIN `raw_legacy.tbsslipdtx` (sales lines, `col_7 = product_code`, `col_23 = signed_qty`)
2. Resolves `product_id` from product code via existing mapping tables
3. Aggregates by `(product_id, warehouse_id, date)` — multiple line items on the same day become one net daily adjustment
4. Inserts `StockAdjustment` with `reason_code = SALES_RESERVATION`, negative quantity (outbound), `created_at = invoice_date`

**Critical: deterministic IDs.** Use a stable UUID derived from `(product_id, warehouse_id, date)` so re-runs are idempotent via `ON CONFLICT DO UPDATE`. The existing `backfill_sales_reservations.py` uses `uuid.uuid4()` — this must be replaced.

## ID Strategy

The ID must be deterministic so that:
- Running the script twice does NOT create duplicates
- `ON CONFLICT (id) DO UPDATE SET quantity_change = EXCLUDED.quantity_change` replaces the existing row

Compute ID as:
```python
id_input = f"{product_id}:{warehouse_id}:{date.isoformat()}"
stock_adjustment_id = hash_to_uuid(tenant_id, "legacy-sales-adjustment", id_input)
```

Use the same `hash_to_uuid` / `_tenant_scoped_uuid` pattern already used in `canonical.py:1397`.

## Column Mapping

| Source table | Column | Meaning |
|---|---|---|
| `tbsslipx` | `col_3` | `invoice_date` — the transaction date |
| `tbsslipdtx` | `col_7` | `product_code` — resolve to `product_id` |
| `tbsslipdtx` | `col_23` | `signed_qty` — positive = outbound, negative = return |
| `tbsslipdtx` | `col_15` | `warehouse_code` — resolve to `warehouse_id` |

## Acceptance Criteria

**AC1: All legacy sales lines produce adjustment records**
**Given** legacy sales data in `tbsslipx`/`tbsslipdtx`
**When** `backfill_sales_issues.py` runs with `--live`
**Then** every row with a non-zero `col_23` signed quantity produces one `StockAdjustment`
**And** `quantity_change` = negative of `col_23` (outbound = negative)
**And** `created_at` = `col_3` (invoice date)
**And** `reason_code` = `SALES_RESERVATION`
**And** `actor_id` = `"backfill-script"`

**AC2: Daily aggregation produces one record per product per day**
**Given** multiple sales lines for the same product on the same day
**When** the script aggregates them
**Then** one `StockAdjustment` is created with the summed quantity
**And** the `notes` field indicates the number of aggregated lines

**AC3: Returns produce positive adjustments**
**Given** a `tbsslipdtx` row with a negative `col_23` (return)
**When** processed
**Then** the resulting `StockAdjustment` has a positive `quantity_change` (stock increases)
**And** `reason_code` = `SALES_RESERVATION`

**AC4: Runs are idempotent**
**Given** the script has been run once
**When** it is run again with the same parameters
**Then** no duplicate `StockAdjustment` records are created
**And** the existing records are updated in place (same IDs)

**AC5: Dry-run is the default**
**Given** no `--live` flag is passed
**When** the script runs
**Then** no database changes are made
**And** a preview of records that would be inserted is printed

**AC6: Reconciliation gap is measurable**
**Given** both Story 18.1 and Story 18.2 adjustments have been backfilled
**When** `verify_reconciliation.py` runs
**Then** for each `(product_id, warehouse_id)`:
**And** `SUM(StockAdjustment.quantity_change)` + `current_stock` = 0
**And** any non-zero gap is flagged for human review

## Tasks / Subtasks

- [ ] **Task 1: Fix `backfill_sales_reservations.py` ID strategy**
  - [ ] Replace `uuid.uuid4()` with deterministic hash-based UUID
  - [ ] Ensure `ON CONFLICT (id) DO UPDATE` is used in INSERT
  - [ ] Add `warehouse_id` to the deterministic ID components
  - [ ] Run existing tests to confirm no regressions

- [ ] **Task 2: Create `backfill_purchase_receipts.py`**
  - [ ] Mirror the structure of `backfill_sales_reservations.py`
  - [ ] Read from `tbsslipj` (header) + `tbsslipdtj` (lines) — same as canonical's receiving audit
  - [ ] Use `col_4 AS receipt_date` as `created_at` (already added to canonical's query)
  - [ ] Use deterministic IDs matching canonical's `_import_legacy_receiving_audit` pattern
  - [ ] Default to dry-run, `--live` flag to insert
  - [ ] Add tests

- [ ] **Task 3: Create `verify_reconciliation.py`**
  - [ ] For each `(product_id, warehouse_id)`, compute `SUM(StockAdjustment.quantity_change)`
  - [ ] Compare against `inventory_stock.quantity` (anchored to today)
  - [ ] Report products with non-zero gap
  - [ ] Categorize gap by `reason_code` to show which source tables have missing records
  - [ ] Output: CSV or table of `(product_id, warehouse_id, expected_adjustment_sum, actual_stock, gap)`

- [ ] **Task 4: Verify complete reconciliation**
  - [ ] Run purchase backfill with `--live`
  - [ ] Run sales backfill with `--live`
  - [ ] Run `verify_reconciliation.py`
  - [ ] Confirm gap is within acceptable tolerance
  - [ ] For any remaining gap, determine if a `CORRECTION` adjustment is warranted

## Dev Notes

### Why standalone scripts vs. extending canonical

- `canonical.py` is a one-shot migration pipeline — standalone backfill scripts can be run, verified, and re-run independently
- Standalone scripts are easier to test in isolation
- The reconciliation step is separate because it informs a human decision (what to do with the gap)
- Both scripts must use deterministic IDs to be safe for re-runs and to avoid conflicts if canonical ever adds equivalent steps

### Source table vs. staging table

The scripts read from `raw_legacy.tbsslipx` / `raw_legacy.tbsslipdtx` (the **raw staging layer**), not from `normalized.tbsslipx` — these are the same source tables used by the canonical pipeline. The raw staging layer is populated by `extract` + `stage` steps.

### Relationship to Story 18.1

Story 18.1 (canonical's `_import_legacy_receiving_audit`) imports purchase receipts INSIDE the canonical pipeline with deterministic IDs. Story 18.2's `backfill_purchase_receipts.py` is a standalone alternative that can run after canonical to verify or re-import. Both must use the same ID derivation to avoid duplicates.

### Gap interpretation

If `SUM(adjustments) + current_stock != 0`:
- **Gap > 0**: goods went out that aren't in the legacy sales tables (scrap, floor returns, direct shipments)
- **Gap < 0**: goods came in that aren't in the legacy purchase tables (dropship, freebies, manual additions)

The gap is not an error — it's a data quality signal. It tells you what fraction of inventory movement was captured in the legacy transaction tables vs. what was managed outside the system.

## File List

- `backend/scripts/backfill_sales_reservations.py` — existing template (needs deterministic IDs)
- `backend/scripts/backfill_purchase_receipts.py` — new script
- `backend/scripts/verify_reconciliation.py` — new script
- `backend/domains/legacy_import/canonical.py:1353` — reference for deterministic ID pattern
