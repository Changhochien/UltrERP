# Story 18.1: Legacy Receiving Audit Trail Import

Status: review

## Story

As a migration operator,
I want every historical purchase invoice line from the legacy system to appear as a stock-receiving event in UltrERP,
So that the inventory audit trail is complete even for goods received before the new system was deployed.

## Problem Statement

The legacy system (鼎新-style ERP) had no separate "goods receipt" transaction. When a container arrived, warehouse staff typed the purchase invoice into the system — the purchase invoice IS the receiving record. The system's `tbsstkhouse` table stored only a **current-state snapshot** (cumulative `fcurqty`), not a movement ledger.

The current migration (Epic 15 + Story 16.4) imports:
- `tbsstkhouse.fcurqty` → `inventory_stock.quantity` (static snapshot, correct current stock)
- `tbsslipj/tbsslipdtj` → `SupplierOrder` + `SupplierOrderLine` (Story 16.4, already done)

What is **missing**: `StockAdjustment` records with `ReasonCode.SUPPLIER_DELIVERY` for each historical receiving event. Without these, the new app's inventory history is blank for all legacy goods.

## Why This Matters

- In the new app, `receive_supplier_order()` creates `StockAdjustment(reason_code=SUPPLIER_DELIVERY)` as an immutable audit trail
- For legacy goods, this trail is empty — operators cannot see when/which deliveries arrived
- `dtslipdate` (invoice date in `tbsslipdtj`) is the historically accurate receiving date — the legacy workflow had no separate receiving step, the invoice entry WAS the receipt

## Solution

A new migration step `_import_legacy_receiving_audit()` in `canonical.py` that runs **after** the inventory snapshot import:

For each `tbsslipdtj` row:
1. Resolve `product_id` from product code mapping (already done in Epic 15/16)
2. Resolve `warehouse_id` from `shouseno` (already done in Epic 15/16)
3. Create `StockAdjustment`:
   - `tenant_id` = target tenant
   - `product_id` = resolved product UUID
   - `warehouse_id` = resolved warehouse UUID
   - `quantity_change` = `fstkqty` (quantity received, from column 22 of tbsslipdtj)
   - `reason_code` = `ReasonCode.SUPPLIER_DELIVERY`
   - `actor_id` = `"legacy_import"` (consistent with all other Epic 15/16 actors)
   - `notes` = `f"Legacy import: invoice {sslipno}"`
   - `created_at` = `dtslipdate` (invoice date = delivery date in legacy system)

**Why no double-counting**: `inventory_stock.quantity` is already set from the snapshot import. `StockAdjustment` records are **additive audit entries** — they record history, they do not change current stock. The snapshot import sets the destination; the audit trail provides the journey.

**Idempotency**: Use the same `legacy_import_batch` + `source_table` + `source_id` lineage key that Epic 15 uses for all other import steps. A `UNIQUE` constraint on `(tenant_id, product_id, warehouse_id, reason_code, source_table, source_id)` prevents duplicates on replay.

## Acceptance Criteria

**AC1: Audit trail is complete**
**Given** the canonical import is run for a batch that includes `tbsslipdtj` rows
**When** the receiving audit step executes
**Then** every `tbsslipdtj` row produces exactly one `StockAdjustment` with `reason_code = SUPPLIER_DELIVERY`
**And** the `quantity_change` equals `fstkqty` for that row
**And** `created_at` equals `dtslipdate` for that row
**And** `notes` contains the invoice number `sslipno`

**AC2: Stock is not double-counted**
**Given** `inventory_stock.quantity` has already been set from the `tbsstkhouse` snapshot import
**When** the receiving audit step runs
**Then** `inventory_stock.quantity` is **not** modified by this step
**And** `StockAdjustment` records do not trigger `StockChangedEvent` or reorder alert checks

**AC3: Import is idempotent**
**Given** a previous import run created `StockAdjustment` records for a batch
**When** the same batch is re-imported
**Then** no duplicate `StockAdjustment` records are created
**And** the `legacy_import_batch` / lineage key ensures deterministic replay

**AC4: Actor is consistent**
**Given** all other Epic 15/16 import steps use `actor_id = "legacy_import"`
**When** `StockAdjustment` records are created by this step
**Then** `actor_id` is set to `"legacy_import"` (not a user UUID)

**AC5: Lineage is preserved**
**Given** a `StockAdjustment` is created from a `tbsslipdtj` row
**When** an auditor inspects the record
**Then** the record links back to `source_table = 'tbsslipdtj'` and `source_id = sslipno + ':' + iidno`

## Column Mapping Reference (tbsslipdtj CREATE TABLE, 78 columns)

| Position | Column Name | tbsslipdtj value used |
|---|---|---|
| col 0 | `skind` | Document type ('4' = purchase invoice) |
| col 1 | `sslipno` | Invoice number (used in notes + as source_id key component) |
| col 2 | `iidno` | Line sequence number (used as source_id key component: sslipno:iidno) |
| col 3 | `dtslipdate` | **Invoice date = receiving date** → `created_at` |
| col 5 | `sstkno` | Product code → resolve to `product_id` via product mapping |
| col 15 | `shouseno` | Warehouse code → resolve to `warehouse_id` via warehouse mapping |
| col 21 | `fstkqty` | **Quantity received** → `quantity_change` |

**Source**: `legacy data/cao50001.sql` line ~13086 CREATE TABLE tbsslipdtj

## Tasks / Subtasks

- [x] **Task 1: Add StockAdjustment lineage tracking to canonical import** (AC3, AC5)
  - [ ] Add `source_table` and `source_id` columns to `StockAdjustment` model (via migration)
  - [x] OR use a separate `legacy_import_lineage` sidecar table keyed by `(tenant_id, source_table, source_id)`
  - [x] Ensure the idempotency key covers `(tenant_id, product_id, warehouse_id, reason_code, source_table, source_id)`

- [x] **Task 2: Implement `_import_legacy_receiving_audit()` in canonical.py** (AC1, AC2, AC4, AC5)
  - [x] Add function after `_import_inventory` in `canonical.py`
  - [x] Iterate over `tbsslipdtj` rows from normalized staging data
  - [x] Resolve `product_id` and `warehouse_id` using existing Epic 15/16 mapping lookups
  - [x] Create `StockAdjustment` records with `reason_code = ReasonCode.SUPPLIER_DELIVERY`
  - [x] Set `actor_id = "legacy_import"`, `created_at = dtslipdate`
  - [x] Do NOT update `inventory_stock.quantity` (snapshot already set)
  - [x] Do NOT emit `StockChangedEvent` (not a live transaction)

- [x] **Task 3: Wire into `run_migration()` pipeline** (AC1, AC3)
  - [x] Call `_import_legacy_receiving_audit()` after inventory snapshot import step
  - [x] Use same `batch_id`, `run_id`, `tenant_id` context as other steps
  - [x] Record lineage in `legacy_import_lineage` with `source_table='tbsslipdtj'`

- [x] **Task 4: Add focused tests** (AC1–AC5)
  - [x] Test that `StockAdjustment` records are created for all tbsslipdtj rows
  - [x] Test that `quantity_change` matches `fstkqty`
  - [x] Test that `created_at` matches `dtslipdate`
  - [x] Test that replay is idempotent (no duplicates)
  - [x] Test that `inventory_stock.quantity` is unchanged after the step
  - [x] Test that `actor_id = "legacy_import"`

## Dev Notes

### Repo Reality

- `StockAdjustment` model exists at `backend/common/models/stock_adjustment.py` with `ReasonCode.SUPPLIER_DELIVERY`
- `ReasonCode.SUPPLIER_DELIVERY` is already in `system_only()` list — it is a valid reason code
- The existing migration pipeline in `canonical.py` follows the pattern: stage → normalize → map → import
- `actor_id = "legacy_import"` is already used consistently across Epic 15/16 steps
- The pipeline currently creates `SupplierOrder` (Story 16.4) but no `StockAdjustment` records

### Critical Warnings

- Do **not** update `inventory_stock.quantity` in this step — the snapshot import already set the correct value
- Do **not** emit `StockChangedEvent` — this is historical data, not a live transaction
- Do **not** use a real user's UUID as `actor_id` — use `"legacy_import"` for all Epic 15/16 imports
- The `dtslipdate` may be `1900-01-01` (sentinel) for some rows — filter or handle sentinel dates

### Implementation Direction

The cleanest approach is a new async function `_import_legacy_receiving_audit()` in `canonical.py` that:
1. Queries `normalized.tbsslipdtj` rows (or raw staging if not yet normalized — this step should run after normalization)
2. For each row, computes the idempotency key and inserts `StockAdjustment` with `ON CONFLICT DO NOTHING`
3. Records lineage in `legacy_import_lineage`

If `source_table`/`source_id` columns don't yet exist on `StockAdjustment`, use the existing `legacy_import_lineage` sidecar table pattern from Story 15.4.

### Sentinel Date Handling

Some `dtslipdate` values may be `1900-01-01` (the PostgreSQL NULL sentinel used in this ERP). The import should:
- Log a warning for sentinel dates
- Use a sensible fallback (e.g., the batch's `created_at` date) as `created_at`
- Continue processing rather than failing the import

## References

- `backend/common/models/stock_adjustment.py` — StockAdjustment model and ReasonCode enum
- `backend/common/models/inventory_stock.py` — inventory_stock model (snapshot target)
- `backend/domains/inventory/services.py:1398` — `receive_supplier_order()` creates `StockAdjustment(reason_code=SUPPLIER_DELIVERY)`
- `backend/domains/legacy_import/canonical.py` — existing migration pipeline (Task 1–4 reference this)
- `docs/legacy/CSV_VS_SQL_COLUMN_MAPPING.md` — positional column mapping for tbsslipdtj
- `docs/legacy/SQL_SCHEMA_AUDIT.md` — CREATE TABLE schema for tbsslipdtj (78 columns, line ~13086)
- `legacy-migration-pipeline/src/parser.py` — updated to generate header rows from CREATE TABLE (Story 16.9 dependency)
- Epic 16 Story 16.4 (Canonical Purchase Order Import) — existing SupplierOrder creation for tbsslipdtj
- Story 15.4 (Canonical Historical Transaction Import) — lineage and idempotency patterns

## Dev Agent Record

### Debug Log

- Chose the existing `canonical_record_lineage` sidecar pattern instead of adding redundant lineage columns to `stock_adjustment`.
- Added `tbsslipdtj.col_4` receipt-date loading, deterministic `stock_adjustment` upserts, and sentinel-date fallback to the purchase-header invoice date with warnings.
- Kept the import path raw-SQL only so historical replay creates audit rows without touching `inventory_stock` or emitting inventory-domain events.

### Completion Notes

- Story 18.1 is implemented with the repo's existing lineage mechanism: `canonical_record_lineage` is the actual sidecar table used for `tbsslipdtj` provenance.
- The unchecked Task 1 subtask is the unchosen schema-expansion alternative; the implemented best-practice path is the checked sidecar-lineage option.
- Validation passed:
  - `cd backend && uv run pytest tests/domains/legacy_import/test_canonical.py -q`
  - `cd backend && uv run ruff check domains/legacy_import/canonical.py tests/domains/legacy_import/test_canonical.py`
  - `cd backend && uv run pytest tests/domains/legacy_import -q`
- Broader backend validation is currently blocked by unrelated pre-existing failures outside this story:
  - `cd backend && uv run pytest -q` fails during collection in `tests/test_mcp_customers.py` because `customers_list.fn` is missing.
  - `cd backend && uv run pytest -q --ignore=tests/test_mcp_customers.py` still exposes unrelated inventory and MCP failures not caused by this legacy-import change.

## File List

- backend/domains/legacy_import/canonical.py
- backend/tests/domains/legacy_import/test_canonical.py

## Change Log

- 2026-04-12: Added legacy receiving audit import with deterministic stock-adjustment upserts, sentinel-date fallback, lineage recording, and focused regression coverage.
