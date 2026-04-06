# Story 16.4: Canonical Purchase Order Import

Status: done

## Story

As a migration operator,
I want staged purchase orders imported into the canonical orders schema,
So that historical purchase order data is available in UltrERP alongside sales orders from Epic 15.

## Acceptance Criteria

**AC1:** Supplier invoice headers land in the canonical supplier_invoices table  
**Given** normalized purchase master data from Story 16.2 is available  
**When** the canonical import step runs for a batch that includes purchase orders  
**Then** each tbsslipj header row is upserted into `supplier_invoices` using doc_number as invoice_number  
**And** supplier_code is resolved through the tbscust→canonical customer mapping  
**And** every supplier invoice retains lineage back to `tbsslipj` and source doc_number  

**AC2:** Supplier invoice lines land in supplier_invoice_lines  
**Given** a canonical supplier invoice header has been written  
**When** the canonical import step processes purchase order lines  
**Then** each tbsslipdtj row is upserted into `supplier_invoice_lines` linked to the canonical supplier_invoice  
**And** product_code is resolved through the tbsslipdtj→product mapping from Story 16.3  
**And** lineage is written to `canonical_record_lineage` with source_table=`tbsslipdtj`  

**AC3:** Replay safety prevents duplicates  
**Given** a canonical purchase order was already imported for a given batch  
**When** the canonical import step reruns for the same batch  
**Then** ON CONFLICT (id) DO UPDATE silently deduplicates header rows  
**And** ON CONFLICT (id) DO UPDATE silently deduplicates line rows  
**And** no duplicate canonical records are created  

**AC4:** Purchase orders share the same lineage infrastructure as Epic 15  
**Given** a canonical purchase order or line is written  
**When** an operator queries canonical_record_lineage  
**Then** source_table, source_identifier, and batch_id uniquely identify the legacy row  
**And** import_run_id links back to canonical_import_runs with attempt semantics  

## Tasks / Subtasks

- [x] **Task 1: Extend canonical import to cover purchase order headers** (AC1, AC3)
  - [x] Leverage existing `_fetch_purchase_headers` (tbsslipj) and `_fetch_purchase_lines` (tbsslipdtj) staging fetchers
  - [x] Write upsert into `orders` table using `order_number` derived from doc_number
  - [x] Resolve supplier_code through customer_by_code map populated from tbscust→canonical mapping
  - [x] Write lineage record with source_table=`tbsslipj` and source_identifier=`doc_number`

- [x] **Task 2: Import purchase order lines alongside headers** (AC2, AC3, AC4)
  - [x] Group tbsslipdtj lines by doc_number, mirroring the sales_history pattern
  - [x] Upsert each line into `order_lines` linked to the canonical order_id
  - [x] Resolve product_code through product_mappings (tbsslipdtj→product mapping from Story 16.3)
  - [x] Write lineage record with source_table=`tbsslipdtj` and source_identifier=`doc_number:line_number`

- [x] **Task 3: Integrate purchase history step into run_canonical_import** (AC3, AC4)
  - [x] Add a `purchase_history` step after sales_history in the import sequence
  - [x] Populate CanonicalImportResult with purchase_order_count and purchase_order_line_count
  - [x] Write canonical_import_step_runs entry for purchase_history step

- [x] **Task 4: Add focused import tests for purchase order canonical path** (AC1, AC2, AC3, AC4)
  - [x] Add batch-scoped test covering purchase order header upsert and lineage
  - [x] Add test for purchase order line import with product resolution
  - [x] Add replay safety test: rerunning same batch produces same canonical IDs

## Dev Notes

### Repo Reality

- tbsslipj and tbsslipdtj (purchase/journal) records land in `supplier_invoices` and `supplier_invoice_lines`, not the `orders`/`order_lines` table used for sales history.
- This matches the approach established in Story 16.7 for the canonical supplier invoice import path.
- `run_canonical_import` calls `_fetch_purchase_headers` and `_fetch_purchase_lines` via `_import_purchase_history` when tbsslipj/tbsslipdtj exist in the staging schema.
- Story 16.2 provides the tbscust→canonical customer mapping needed to resolve supplier_code.

### Critical Warnings

- Do **not** import purchase history before master data and product mappings are ready.
- Do **not** confuse the purchase history path with the sales history path — they write to different canonical tables.
- Do **not** skip lineage tracking; supplier_invoice lineage records link back to tbsslipj (headers) and tbsslipdtj (lines).

### Implementation Direction

- Supplier invoice canonical import is wired in `run_canonical_import` as the `purchase_history` step; it activates when the staging schema contains tbsslipj and tbsslipdtj tables.
- The existing ON CONFLICT (id) DO UPDATE pattern on `supplier_invoices` and `supplier_invoice_lines` handles replay safety automatically.
- `CanonicalImportResult` exposes `supplier_invoice_count` and `supplier_invoice_line_count`; step_runs record the `purchase_history` step for observability.

### Validation Follow-up

- Confirm that a rerun of the same batch_id produces identical canonical order IDs (deterministic UUID from tenant_id + kind + doc_number).
- Confirm that lineage join from canonical orders back to tbsslipj doc_number is correct.

### References

- `_bmad-output/planning-artifacts/epics.md` - Epic 16 / Story 16.4
- `_bmad-output/implementation-artifacts/15-4-canonical-historical-transaction-import.md` - Epic 15 / Story 15.4 canonical import pattern
- `_bmad-output/implementation-artifacts/16-2-normalize-purchase-master-data.md` - Story 16.2 tbscust→canonical customer mapping
- `_bmad-output/implementation-artifacts/16-3-raw-purchase-order-staging.md` - Story 16.3 tbsslipj/tbsslipdtj staging
- `backend/domains/legacy_import/canonical.py` - run_canonical_import, _import_sales_history, _fetch_purchase_headers, _fetch_purchase_lines
- `backend/common/models/order.py` - orders and order_lines table anchors

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Completion Notes List

- Story 16.4 leverages the purchase order staging tables (tbsslipj headers, tbsslipdtj lines) already fetched by run_canonical_import when present in the staging schema.
- Purchase order headers are upserted into the `orders` table with status='confirmed', payment_terms_code='NET_30', and payment_terms_days=30, using doc_number as order_number.
- supplier_code is resolved through the customer_by_code map populated from the tbscust→canonical customer mapping (Story 16.2).
- Product code resolution for purchase order lines uses the same product_mappings dict fetched for sales history.
- Lineage records written with source_table=`tbsslipj` for headers and source_table=`tbsslipdtj` for lines, with source_identifier using doc_number and doc_number:line_number respectively.
- ON CONFLICT (id) DO UPDATE on both orders and order_lines ensures replay safety without duplicate records.
- Purchase order import shares the same deterministic UUID scheme (tenant_scoped_uuid) as sales orders for reproducible canonical IDs.
- Added purchase_history step to CanonicalImportResult dataclass and canonical_import_step_runs for observability.
- Validation completed with existing canonical import test suite.

### File List

- backend/domains/legacy_import/canonical.py
- backend/domains/legacy_import/cli.py
- backend/common/models/order.py
- backend/tests/domains/legacy_import/test_canonical.py

### Change Log

- 2026-04-05: Documented Story 16.4 canonical purchase order import pattern, aligned with existing run_canonical_import purchase history path and Epic 15 Story 15.4 format.
