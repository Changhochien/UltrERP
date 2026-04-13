# Story 18.2: Legacy Sales Adjustment Backfill

Status: in-progress

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

- [x] **Task 1: Fix `backfill_sales_reservations.py` ID strategy**
  - [x] Replace `uuid.uuid4()` with deterministic hash-based UUID
  - [x] Ensure `ON CONFLICT (id) DO UPDATE` is used in INSERT
  - [x] Add `warehouse_id` to the deterministic ID components
  - [x] Run existing tests to confirm no regressions

- [x] **Task 2: Create `backfill_purchase_receipts.py`**
  - [x] Mirror the structure of `backfill_sales_reservations.py`
  - [x] Read from `tbsslipj` (header) + `tbsslipdtj` (lines) — same as canonical's receiving audit
  - [x] Use `col_4 AS receipt_date` as `created_at` (already added to canonical's query)
  - [x] Use deterministic IDs matching canonical's `_import_legacy_receiving_audit` pattern
  - [x] Default to dry-run, `--live` flag to insert
  - [x] Add tests

- [x] **Task 3: Create `verify_reconciliation.py`**
  - [x] For each `(product_id, warehouse_id)`, compute `SUM(StockAdjustment.quantity_change)`
  - [x] Compare against `inventory_stock.quantity` (anchored to today)
  - [x] Report products with non-zero gap
  - [x] Categorize gap by `reason_code` to show which source tables have missing records
  - [x] Output: CSV or table of `(product_id, warehouse_id, expected_adjustment_sum, actual_stock, gap)`

- [ ] **Task 4: Verify complete reconciliation**
  - [x] Run purchase backfill with `--live`
  - [x] Run sales backfill with `--live`
  - [x] Run `verify_reconciliation.py`
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

## Dev Agent Record

### Debug Log

- Introduced a shared `backend/scripts/_legacy_stock_adjustments.py` helper so the sales backfill, purchase backfill, and reconciliation verifier all use the same deterministic UUID, mapping, quantity-coercion, and batched upsert logic instead of cloning raw SQL.
- Reworked `backfill_sales_reservations.py` to resolve the real legacy warehouse code, prune the stale hardcoded-warehouse rows from the previous broken backfill, and upsert deterministic daily adjustments.
- Matched purchase receipts to canonical receiving-audit semantics: deterministic line-level IDs, `legacy_import` actor/notes, receipt-date fallback to the header invoice date, UNKNOWN-product fallback, and duplicate-ID collapse before bulk upsert.
- Implemented `verify_reconciliation.py` as a read-only report with reason-code breakdowns. The verifier uses `adjustment_sum - current_stock`, because the story's `+ current_stock` formula conflicts with positive inventory quantities and with the story's own gap interpretation.
- Investigated the post-run warehouse mismatch to its real source: `domains/legacy_import/normalization.py` was dropping `tbsstkhouse.col_2` (`shouseno`) and hardcoding `LEGACY_DEFAULT` for every current-stock row.
- Fixed normalization to preserve `tbsstkhouse` warehouse codes and added `repair_inventory_snapshot_warehouses.py` so already-imported `inventory_stock` rows can be realigned from `LEGACY_DEFAULT` to the actual snapshot warehouse with lineage preserved.
- Added `reset_legacy_import_batch.py` as a dry-run-first purge helper for clean cutover rehearsals, including the extra non-lineaged Story 18.2 sales-backfill slice.
- Clean rehearsal found one more production-path defect: canonical receiving audit aborted on fractional `tbsslipdtj.qty` values from the live dataset. Fixed `domains/legacy_import/canonical.py` to coerce and annotate those receipt quantities the same way the standalone purchase backfill already does.

### Completion Notes

- Focused validation passed:
  - `cd backend && uv run pytest tests/domains/legacy_import tests/test_legacy_stock_backfill_scripts.py -q`
  - `cd backend && uv run ruff check scripts/_legacy_stock_adjustments.py scripts/backfill_sales_reservations.py scripts/backfill_purchase_receipts.py scripts/verify_reconciliation.py tests/test_legacy_stock_backfill_scripts.py`
- Warehouse-normalization validation also passed:
  - `cd backend && uv run pytest tests/domains/legacy_import/test_normalization.py -q`
  - `cd backend && uv run python -m scripts.repair_inventory_snapshot_warehouses`
- Clean-rehearsal validation also passed:
  - `cd backend && uv run python -m scripts.reset_legacy_import_batch --batch-id cao50001 --include-sales-backfill`
  - `cd backend && uv run pytest tests/domains/legacy_import/test_canonical.py tests/test_reset_legacy_import_batch.py -q`
- Dry-run validation passed after fixing real data issues in the local dataset:
  - Sales backfill now handles 12 fractional daily totals by explicit integer-schema coercion notes instead of crashing.
  - Purchase backfill now falls back to canonical `UNKNOWN` for 88 unmapped purchase product codes instead of crashing.
- Live runs completed in the local database:
  - Purchase backfill: `61727` raw rows collapsed to `61710` deterministic receipt adjustments and upserted successfully.
  - Sales backfill: `596701` raw sales rows aggregated to `482191` deterministic daily adjustments, `481754` stale wrong-warehouse sales rows were deleted, and `482191` corrected adjustments were upserted.
- Inventory snapshot warehouse repair completed live:
  - `repair_inventory_snapshot_warehouses.py --live` rebuilt `6588` `inventory_stock` rows onto warehouse code `A` and deleted the stale `LEGACY_DEFAULT` snapshot rows plus their lineage.
- Post-repair reconciliation is still blocked at the data-review stage, so Task 4 remains incomplete:
  - Strict `(product_id, warehouse_id)` report after the repair: `12064` adjustment groups, `6593` inventory groups, `2855` flagged gaps.
  - The warehouse-normalization blocker is resolved. The remaining gaps are the true residual movement differences that need operator review.
- A correction-plan generator is now available for the residual review step:
  - `propose_reconciliation_corrections.py --min-abs-gap 100 --csv /tmp/ultrerp-correction-plan-gap100.csv` produced `520` deterministic `CORRECTION` proposals for the `>=100` slice on `2026-04-12`.
  - The proposal layer is intentionally plan-only; no correction adjustments were auto-applied in this story.
- The proposal layer now treats category `6` SKUs as review-only by default after candidate profiling showed that bucket only contains non-merchandise rows like `折讓`, `運費`, and `郵寄運費`.
- A safe apply path now exists for operator-approved corrections:
  - `propose_reconciliation_corrections.py` exports a blank `approval_action` column in the CSV.
  - `apply_reconciliation_corrections.py` only applies rows explicitly marked `approval_action=apply`, rejects any non-actionable row, validates the deterministic correction ID, and stays dry-run by default.
  - Dry-running the refreshed clean-rehearsal CSV with no approvals correctly reported `Approved rows: 0` and performed no writes.
- A full clean cutover rehearsal now exists and reproduces the same residual-gap shape without carrying forward repaired dev artifacts:
  - `reset_legacy_import_batch.py --batch-id cao50001 --include-sales-backfill --live` successfully purged the batch-derived canonical rows plus the tenant-scoped sales backfill slice.
  - `legacy-import normalize --batch-id cao50001 ...` rebuilt `parties=1022`, `products=6611`, `warehouses=1`, `inventory=6588` on the fixed warehouse-aware normalization path.
  - `legacy-import canonical-import --batch-id cao50001 ...` succeeded on attempt `67` after the receiving-audit fractional-quantity fix.
  - `backfill_sales_reservations --lookback 10000 --live` reinserted `482191` deterministic daily sales adjustments.
  - Fresh reconciliation after the clean rebuild reported `2850` strict gaps, and the refined `>=100` correction proposal set contains `506` actionable rows plus `3` review-only non-merchandise rows. That confirms the residual gaps are inherent to the legacy movement history, not artifacts of the repaired dev database.
- No `CORRECTION` adjustments were created in this story. The remaining gaps need operator review to decide whether they reflect true missing movements, warehouse-normalization drift, or a separate inventory rebasing step.

## File List

- `backend/scripts/_legacy_stock_adjustments.py`
- `backend/domains/legacy_import/normalization.py`
- `backend/domains/legacy_import/canonical.py`
- `backend/scripts/backfill_sales_reservations.py`
- `backend/scripts/backfill_purchase_receipts.py`
- `backend/scripts/verify_reconciliation.py`
- `backend/scripts/repair_inventory_snapshot_warehouses.py`
- `backend/scripts/propose_reconciliation_corrections.py`
- `backend/scripts/apply_reconciliation_corrections.py`
- `backend/scripts/reset_legacy_import_batch.py`
- `backend/tests/test_legacy_stock_backfill_scripts.py`
- `backend/tests/domains/legacy_import/test_normalization.py`
- `backend/tests/domains/legacy_import/test_canonical.py`
- `backend/tests/test_apply_reconciliation_corrections.py`
- `backend/tests/test_reset_legacy_import_batch.py`
- `backend/tests/test_propose_reconciliation_corrections.py`

## Change Log

- 2026-04-12: Implemented deterministic warehouse-aware sales backfill, standalone purchase receipt backfill, shared legacy stock-adjustment helpers, and reconciliation reporting with focused regression coverage.
- 2026-04-12: Executed live purchase and sales backfills on the local legacy dataset, removed `481754` stale wrong-warehouse sales rows, and captured the remaining reconciliation blocker (`A` vs `LEGACY_DEFAULT` warehouse normalization plus non-zero residual product gaps).
- 2026-04-12: Fixed the `tbsstkhouse` warehouse-code normalization bug, added a reproducible inventory snapshot warehouse-repair script, repaired the live snapshot slice from `LEGACY_DEFAULT` to `A`, and reduced the reconciliation report to `2855` true residual gaps.
- 2026-04-12: Added plan-only `CORRECTION` proposal generation and produced a `>=100`-gap CSV plan with `520` deterministic correction candidates for operator review.
- 2026-04-12: Added a dry-run-first batch reset helper, fixed canonical receiving-audit fractional quantity handling, and completed a clean cutover rehearsal that reproduced `2850` residual gaps and `509` `>=100` correction proposals from a fresh rebuild.
- 2026-04-12: Refined correction planning so category `6` non-merchandise SKUs are review-only by default, leaving `506` actionable `>=100` candidates and `3` review-only service/discount rows in the clean rehearsal plan.
- 2026-04-12: Added the approval-driven correction apply path so refreshed proposal CSVs carry `approval_action`, `apply_reconciliation_corrections.py` only accepts explicitly approved actionable rows, and an unapproved dry run performs zero writes.
