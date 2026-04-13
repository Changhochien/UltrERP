## Epic 18: Legacy Inventory Receiving Audit Trail

### Epic Goal

Complete the inventory audit trail for all historical goods received before UltrERP deployment by creating `StockAdjustment(SUPPLIER_DELIVERY)` records from legacy purchase invoice data, filling the gap left by the legacy system's snapshot-only inventory model.

### Stories

### Story 18.1: Legacy Receiving Audit Trail Import

As a migration operator,
I want every historical purchase invoice line from the legacy system to appear as a stock-receiving event in UltrERP,
So that the inventory audit trail is complete even for goods received before the new system was deployed.

**Problem Statement:** The legacy system (鼎新-style ERP) had no separate "goods receipt" transaction. When a container arrived, warehouse staff typed the purchase invoice into the system — the purchase invoice IS the receiving record. The system's `tbsstkhouse` table stored only a **current-state snapshot** (cumulative `fcurqty`), not a movement ledger.

The current migration (Epic 15 + Story 16.4) imports:
- `tbsstkhouse.fcurqty` → `inventory_stock.quantity` (static snapshot, correct current stock)
- `tbsslipj/tbsslipdtj` → `SupplierOrder` + `SupplierOrderLine` (Story 16.4, already done)

What is **missing**: `StockAdjustment` records with `ReasonCode.SUPPLIER_DELIVERY` for each historical receiving event. Without these, the new app's inventory history is blank for all legacy goods.

**Solution:** A new migration step `_import_legacy_receiving_audit()` in `canonical.py` that runs after the inventory snapshot import. For each `tbsslipdtj` row: resolve `product_id` and `warehouse_id` via existing mappings, then create `StockAdjustment` with `quantity_change = fstkqty`, `reason_code = SUPPLIER_DELIVERY`, `created_at = dtslipdate`.

`inventory_stock.quantity` is NOT modified — the snapshot import already set the correct value. `StockAdjustment` records are additive audit entries; they provide the journey, not change the destination.

**Acceptance Criteria:**

**Given** the canonical import is run for a batch that includes `tbsslipdtj` rows
**When** the receiving audit step executes
**Then** every `tbsslipdtj` row produces exactly one `StockAdjustment` with `reason_code = SUPPLIER_DELIVERY`
**And** `quantity_change` equals `fstkqty` for that row
**And** `created_at` equals `dtslipdate` for that row
**And** `notes` contains the invoice number `sslipno`

**Given** `inventory_stock.quantity` has already been set from the `tbsstkhouse` snapshot import
**When** the receiving audit step runs
**Then** `inventory_stock.quantity` is **not** modified by this step
**And** `StockAdjustment` records do not trigger `StockChangedEvent` or reorder alert checks

**Given** a previous import run created `StockAdjustment` records for a batch
**When** the same batch is re-imported
**Then** no duplicate `StockAdjustment` records are created
**And** the deterministic UUID idempotency key prevents duplicates on replay

**Given** `StockAdjustment` records are created by this step
**Then** `actor_id` is set to `"legacy_import"` (consistent with all other Epic 15/16 actors)

**Given** a `StockAdjustment` is created from a `tbsslipdtj` row
**When** an auditor inspects the record
**Then** the record links back to `source_table = 'tbsslipdtj'` and `source_id = sslipno + ':' + iidno`

**Sentinel date handling:** Some `dtslipdate` values may be `1900-01-01` (PostgreSQL NULL sentinel). The import logs a warning and falls back to `invoice_date` from the header, then to the batch run date as last resort.

**Column mapping reference:**

| Position | Column Name | Used for |
|---|---|---|
| col 0 | `skind` | Document type ('4' = purchase invoice) |
| col 1 | `sslipno` | Invoice number (notes + source_id key) |
| col 2 | `iidno` | Line sequence number (source_id key component: sslipno:iidno) |
| col 3 | `dtslipdate` | Invoice date = delivery date → `created_at` |
| col 5 | `sstkno` | Product code → resolve to `product_id` |
| col 15 | `shouseno` | Warehouse code → resolve to `warehouse_id` |
| col 21 | `fstkqty` | Quantity received → `quantity_change` |

**Dev Notes:**
- `StockAdjustment` model exists at `backend/common/models/stock_adjustment.py` with `ReasonCode.SUPPLIER_DELIVERY`
- `ReasonCode.SUPPLIER_DELIVERY` is already in `system_only()` list — valid reason code
- Use `_tenant_scoped_uuid()` for deterministic IDs (same pattern as other Epic 15/16 steps)
- `ON CONFLICT (id) DO UPDATE` prevents duplicates on replay

**Subtasks:**
- [x] Implement `_import_legacy_receiving_audit()` in `canonical.py`
- [x] Wire into `run_migration()` pipeline after inventory snapshot step
- [x] Add focused tests in `test_canonical.py`
- [x] Handle sentinel dates with fallback chain

**Implementation status:** Story 18.1 is complete. See `_bmad-output/implementation-artifacts/18-1-legacy-receiving-audit-trail-import.md`.

---

### Story 18.2: Legacy Sales Adjustment Backfill

As a migration operator,
I want historical sales order lines from the legacy system to appear as outbound stock adjustments in UltrERP,
So that the inventory audit trail reflects both goods received AND goods shipped for the full legacy period.

**Problem Statement:** The legacy system had no formal stock reservation step. `StockAdjustment` records with `ReasonCode.SALES_RESERVATION` are not created during canonical import, leaving the outbound side of the audit trail empty. The source data is `tbsslipdtx.col_23` — a signed quantity where positive = outbound sale, negative = return.

**Solution:** A standalone `backfill_sales_issues.py` script that reads `tbsslipx`/`tbsslipdtx`, aggregates by `(product_id, warehouse_id, date)`, and inserts `StockAdjustment(SALES_RESERVATION)` records with deterministic IDs for idempotent replay. Default dry-run, `--live` flag to insert.

**Key design decisions:**
- Deterministic UUID derived from `(product_id, warehouse_id, date)` — not `uuid.uuid4()` — so `ON CONFLICT DO UPDATE` prevents duplicates
- Positive `col_23` = outbound (negative `quantity_change`), negative `col_23` = return (positive `quantity_change`)
- Gap verification: `SUM(adjustments) + current_stock` must = 0; non-zero gaps flag missing/untracked movements (scrap, floor return, dropship)

**Acceptance Criteria:**

**Given** legacy sales data in `tbsslipx`/`tbsslipdtx`
**When** `backfill_sales_issues.py --live` runs
**Then** every non-zero `col_23` row produces one `StockAdjustment`
**And** `quantity_change` = negative of `col_23`
**And** `created_at` = `col_3` (invoice date)
**And** `reason_code` = `SALES_RESERVATION`

**Given** multiple lines for the same product on the same day
**When** aggregated
**Then** one net `StockAdjustment` is created
**And** `notes` indicates the number of aggregated lines

**Given** the script has been run once
**When** run again
**Then** no duplicate records are created (deterministic IDs + `ON CONFLICT DO UPDATE`)

**Given** both Story 18.1 and 18.2 adjustments have been backfilled
**When** `verify_reconciliation.py` runs
**Then** for each `(product_id, warehouse_id)`: `SUM(StockAdjustment.quantity_change) + inventory_stock.quantity` = 0
**And** any non-zero gap is flagged for human review

**Given** a non-zero reconciliation gap exists
**When** the gap is investigated
**Then** it is categorized as either a missing outbound record or an untracked movement

**Column mapping:**

| Source table | Column | Meaning |
|---|---|---|
| `tbsslipx` | `col_3` | `invoice_date` — transaction date |
| `tbsslipdtx` | `col_7` | `product_code` — resolve to `product_id` |
| `tbsslipdtx` | `col_23` | `signed_qty` — positive = outbound, negative = return |
| `tbsslipdtx` | `col_15` | `warehouse_code` — resolve to `warehouse_id` |

**Subtasks:**
- [ ] Fix `backfill_sales_reservations.py` to use deterministic IDs instead of `uuid.uuid4()`
- [ ] Create `backfill_purchase_receipts.py` mirroring canonical's receiving audit logic as a standalone script
- [ ] Create `verify_reconciliation.py` to compute and report gaps by `(product_id, warehouse_id)`
- [ ] Run full backfill sequence and confirm reconciliation closes within tolerance

**File list:**
- `backend/scripts/backfill_sales_reservations.py` — existing template (needs deterministic IDs)
- `backend/scripts/backfill_purchase_receipts.py` — new script
- `backend/scripts/verify_reconciliation.py` — new script
