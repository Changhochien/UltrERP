# Story 17.4: AP Aging Report Endpoint

Status: done

## Implementation Status

**Backend:** DONE — Already implemented before investigation

**Completed:**
- `get_ap_aging_report()` service function at `backend/domains/reports/services.py`
- `GET /reports/ap-aging` route at `backend/domains/reports/routes.py`
- `APAgingReportResponse` schema at `backend/domains/reports/schemas.py`
- Bucket structure: 0-30, 31-60, 61-90, 90+ days with invoice counts
- Uses `invoice_date` for age computation (AP aging basis)
- Tenant isolation via `tenant_id` filter

As a backend developer,
I want to expose a `GET /api/v1/reports/ap-aging` endpoint,
So that the owner can see outstanding payables and due-date health.

## Acceptance Criteria

1. [AC-1] **Given** a valid authenticated request
   **When** `GET /api/v1/reports/ap-aging` is called
   **Then** the response returns the same bucket structure as AR aging:
   - `bucket_0_30_days`: sum of outstanding supplier invoice amounts where age 0–30 days
   - `bucket_31_60_days`: same for 31–60 days
   - `bucket_61_90_days`: same for 61–90 days
   - `bucket_90_plus_days`: same for 90+ days
   - `total_outstanding`: sum of all open supplier invoice amounts
   - `total_overdue`: sum of amounts in any overdue bucket (age > 0)

2. [AC-2] **Given** a supplier invoice
   **When** computing its outstanding amount for AP aging
   **Then** `outstanding = SupplierInvoice.total_amount − coalesce(sum(SupplierPaymentAllocation.applied_amount), 0)` where allocations are linked via `SupplierPaymentAllocation.supplier_invoice_id`
   **And** only allocations with `allocation_kind = 'invoice_settlement'` are counted (not reversals or prepayment applications)

3. [AC-3] **Given** a supplier invoice
   **When** computing its age for AP aging
   **Then** `age_days = (today − SupplierInvoice.invoice_date)` in days (AP aging is based on invoice date, not due date — AP aging tracks how long the invoice has been in the system)
   **And** invoices with `status = 'voided'` are excluded from all calculations
   **And** invoices with `status = 'paid'` are excluded from all calculations

4. [AC-4] **Given** a valid authenticated request
   **Then** only records belonging to the authenticated tenant are included (tenant isolation via `tenant_id` filter on all queries)

## Tasks / Subtasks

- [x] Task 1 (AC: 1, 3)
  - [x] Subtask 1.1: Define `APAgingReportResponse` Pydantic schema in `domains/reports/schemas.py` with fields: `bucket_0_30_days`, `bucket_31_60_days`, `bucket_61_90_days`, `bucket_90_plus_days`, `total_outstanding`, `total_overdue`, each as `Decimal`
  - [x] Subtask 1.2: Implement `get_ap_aging_report` async function in `domains/reports/services.py`
  - [x] Subtask 1.3: Write a SQLAlchemy query that computes outstanding per supplier invoice (join `SupplierInvoice` → `SupplierPaymentAllocation` via `supplier_invoice_id`), then groups into age buckets using `case(...)` expressions with age computed from `invoice_date`
  - [x] Subtask 1.4: Add the route `GET /reports/ap-aging` in `domains/reports/routes.py`
- [x] Task 2 (AC: 2)
  - [x] Subtask 2.1: In the outstanding calculation, join `SupplierPaymentAllocation` on `supplier_invoice_id` and filter `allocation_kind = 'invoice_settlement'`
  - [x] Subtask 2.2: Use `outerjoin` to handle invoices with no allocations
- [x] Task 3 (AC: 4)
  - [x] Subtask 3.1: Filter all queries by `tenant_id`

## Dev Notes

- Relevant architecture patterns and constraints
  - All backend routes use `router = APIRouter(dependencies=[Depends(get_current_user)])` for auth
  - Tenant isolation via `tenant_id` column; inject via `get_tenant_id` dependency
  - Use SQLAlchemy 2.0 async with `AsyncSession`
  - Use `case(...)` from `sqlalchemy` for bucket assignment (age ranges → bucket names)
  - Use `func.coalesce(func.sum(...), 0)` to avoid NULL in sums
  - `SupplierInvoice` model: `common/models/supplier_invoice.py` → class `SupplierInvoice`; fields: `id`, `tenant_id`, `total_amount`, `status` (enum: OPEN/PAID/VOIDED), `invoice_date` (Date)
  - `SupplierPaymentAllocation` model: `common/models/supplier_payment.py` → class `SupplierPaymentAllocation`; fields: `supplier_invoice_id`, `applied_amount` (Numeric 20,2), `allocation_kind` (enum: INVOICE_SETTLEMENT / PREPAYMENT_APPLICATION / REVERSAL)
  - Age bucket boundaries: 0-30, 31-60, 61-90, 90+ days — matching the AR aging story 17.3 for consistency in the UI

- Source tree components to touch
  - `domains/reports/schemas.py` — add `APAgingReportResponse` (already created in story 17.3)
  - `domains/reports/services.py` — add `get_ap_aging_report` function (already created in story 17.3)
  - `domains/reports/routes.py` — add `GET /reports/ap-aging` route (already created in story 17.3)
  - No changes to existing SupplierInvoice or SupplierPayment models needed

- Testing standards summary
  - Unit test: mock DB session with known supplier invoices and allocations, assert bucket values
  - Integration test: `GET /reports/ap-aging` with auth → 200, correct bucket totals

### Project Structure Notes

- Alignment with unified project structure (paths, modules, naming)
  - Reports domain: `/Volumes/2T_SSD_App/Projects/UltrERP/backend/domains/reports/`
  - Route file: `/Volumes/2T_SSD_App/Projects/UltrERP/backend/domains/reports/routes.py`
  - Service file: `/Volumes/2T_SSD_App/Projects/UltrERP/backend/domains/reports/services.py`
  - Schema file: `/Volumes/2T_SSD_App/Projects/UltrERP/backend/domains/reports/schemas.py`
  - SupplierInvoice model: `/Volumes/2T_SSD_App/Projects/UltrERP/backend/common/models/supplier_invoice.py`
  - SupplierPaymentAllocation model: `/Volumes/2T_SSD_App/Projects/UltrERP/backend/common/models/supplier_payment.py`
  - Follows the same pattern as `domains/reports/` (created in story 17.3) and `domains/dashboard/`

- Detected conflicts or variances (with rationale)
  - Age computation differs from AR aging: AP aging uses `invoice_date` whereas AR aging uses `due_date`. This is intentional — AP aging tracks how long an invoice has been in the system awaiting payment, while AR aging tracks how long receivables have been overdue past their due date.

### References

- Source: `common/models/supplier_invoice.py` lines 38-95 — `SupplierInvoice` class; `total_amount` is `Numeric(20, 2)`, `status` is `SupplierInvoiceStatus` enum (OPEN/PAID/VOIDED), `invoice_date` is `Date`
- Source: `common/models/supplier_payment.py` lines 106-163 — `SupplierPaymentAllocation` class; `applied_amount` is `Numeric(20, 2)`, `allocation_kind` is `SupplierPaymentAllocationKind` enum
- Source: `domains/reports/` files — created by story 17.3 (same directory, re-use schemas/routes/services)
- Source: `domains/dashboard/services.py` lines 1-138 — reference pattern for async SQLAlchemy service functions
- Source: Epic 17 Story 17.4 (lines 2043-2058 of `_bmad-output/planning-artifacts/epics.md`)

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

N/A

### Completion Notes List

N/A

### File List

- `/Volumes/2T_SSD_App/Projects/UltrERP/backend/domains/reports/schemas.py` — modified (add `APAgingReportResponse`)
- `/Volumes/2T_SSD_App/Projects/UltrERP/backend/domains/reports/services.py` — modified (add `get_ap_aging_report`)
- `/Volumes/2T_SSD_App/Projects/UltrERP/backend/domains/reports/routes.py` — modified (add route)
- `/Volumes/2T_SSD_App/Projects/UltrERP/_bmad-output/implementation-artifacts/17-4-ap-aging-report-endpoint.md` — created
