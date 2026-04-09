# Story 17.3: AR Aging Report Endpoint

Status: done

## Implementation Status

**Backend:** DONE — Already implemented before investigation

**Completed:**
- `get_ar_aging_report()` service function at `backend/domains/reports/services.py`
- `GET /reports/ar-aging` route at `backend/domains/reports/routes.py`
- `ARAgingReportResponse` schema at `backend/domains/reports/schemas.py`
- Bucket structure: 0-30, 31-60, 61-90, 90+ days with invoice counts
- Tenant isolation via `tenant_id` filter

As a backend developer,
I want to expose a `GET /api/v1/reports/ar-aging` endpoint,
So that the owner can see how much receivables are overdue and by how long.

## Acceptance Criteria

1. [AC-1] **Given** a valid authenticated request
   **When** `GET /api/v1/reports/ar-aging` is called
   **Then** the response returns the following bucket structure:
   - `bucket_0_30_days`: sum of outstanding invoice amounts where age 0–30 days past due
   - `bucket_31_60_days`: sum of outstanding invoice amounts where age 31–60 days past due
   - `bucket_61_90_days`: sum of outstanding invoice amounts where age 61–90 days past due
   - `bucket_90_plus_days`: sum of outstanding invoice amounts where age 90+ days past due
   - `total_outstanding`: sum of all open invoice amounts (all ages, regardless of due date status)
   - `total_overdue`: sum of amounts in any overdue bucket (age > 0)

2. [AC-2] **Given** an invoice
   **When** computing its outstanding amount for AR aging
   **Then** `outstanding = Invoice.total_amount − coalesce(sum(Payment.amount), 0)` where payments are matched to that invoice via `Payment.invoice_id`
   **And** only payments with `match_status = 'matched'` or `'auto_matched'` are counted (not pending/unmatched payments)

3. [AC-3] **Given** an invoice
   **When** computing its age for AR aging
   **Then** `age_days = (today − Invoice.due_date)` in days
   **And** invoices with `age_days <= 0` are **not** included in any bucket (they are current, not overdue)
   **And** invoices with `status = 'voided'` are excluded from all calculations

4. [AC-4] **Given** a valid authenticated request
   **Then** only records belonging to the authenticated tenant are included (tenant isolation via `tenant_id` filter on all queries)

## Tasks / Subtasks

- [x] Task 1 (AC: 1, 3)
  - [x] Subtask 1.1: Define `ARAgingReportResponse` Pydantic schema in `domains/reports/schemas.py` (create file if not exists) with fields: `bucket_0_30_days`, `bucket_31_60_days`, `bucket_61_90_days`, `bucket_90_plus_days`, `total_outstanding`, `total_overdue`, each as `Decimal`
  - [x] Subtask 1.2: Implement `get_ar_aging_report` async function in `domains/reports/services.py`
  - [x] Subtask 1.3: Write a single SQLAlchemy query (or CTE) that computes outstanding per invoice, then groups into age buckets using `case(...)` expressions
  - [x] Subtask 1.4: Add the route `GET /reports/ar-aging` in `domains/reports/routes.py`
- [x] Task 2 (AC: 2)
  - [x] Subtask 2.1: In the outstanding calculation, join `Payment` on `invoice_id` and filter `Payment.match_status IN ('matched', 'auto_matched')`
  - [x] Subtask 2.2: Use `outerjoin` to handle invoices with no payments
- [x] Task 3 (AC: 4)
  - [x] Subtask 3.1: Filter all queries by `tenant_id` from the route dependency

## Dev Notes

- Relevant architecture patterns and constraints
  - Reports domain: new subdomain at `domains/reports/` following the same pattern as `domains/dashboard/`
  - All backend routes use `router = APIRouter(dependencies=[Depends(get_current_user)])` for auth
  - Tenant isolation via `tenant_id` column; inject via `get_tenant_id` dependency
  - Use SQLAlchemy 2.0 async with `AsyncSession`
  - Use `case(...)` from `sqlalchemy` for bucket assignment (age ranges → bucket names)
  - Use `func.coalesce(func.sum(...), 0)` to avoid NULL in sums
  - Invoice model at `domains/invoices/models.py` → `Invoice` class; fields: `id`, `tenant_id`, `total_amount`, `status`, `due_date`
  - Payment model at `domains/payments/models.py` → `Payment` class; fields: `invoice_id`, `amount`, `match_status`, `tenant_id`

- Source tree components to touch
  - `domains/reports/__init__.py` — create (empty, for package)
  - `domains/reports/schemas.py` — create (add `ARAgingReportResponse`)
  - `domains/reports/services.py` — create (add `get_ar_aging_report`)
  - `domains/reports/routes.py` — create (add `GET /reports/ar-aging` route)
  - No changes to existing Invoice or Payment models needed

- Testing standards summary
  - Unit test: mock DB session with known invoices/payments, assert bucket values
  - Integration test: `GET /reports/ar-aging` with auth → 200, correct bucket totals

### Project Structure Notes

- Alignment with unified project structure (paths, modules, naming)
  - Reports domain: `/Volumes/2T_SSD_App/Projects/UltrERP/backend/domains/reports/`
  - Route file: `/Volumes/2T_SSD_App/Projects/UltrERP/backend/domains/reports/routes.py`
  - Service file: `/Volumes/2T_SSD_App/Projects/UltrERP/backend/domains/reports/services.py`
  - Schema file: `/Volumes/2T_SSD_App/Projects/UltrERP/backend/domains/reports/schemas.py`
  - Invoice model: `/Volumes/2T_SSD_App/Projects/UltrERP/backend/domains/invoices/models.py`
  - Payment model: `/Volumes/2T_SSD_App/Projects/UltrERP/backend/domains/payments/models.py`
  - Follows the same pattern as `domains/dashboard/routes.py` and `domains/dashboard/services.py`

- Detected conflicts or variances (with rationale)
  - The `domains/reports/` directory does not yet exist; this story creates it following the established `domains/<name>/` pattern

### References

- Source: `domains/invoices/models.py` — `Invoice` model; `status` is a string, `total_amount` is `Numeric(20, 2)`, `due_date` is `Date`
- Source: `domains/payments/models.py` — `Payment` model; `amount` is `Numeric(20, 2)`, `match_status` column available; note: use only `match_status IN ('matched', 'auto_matched')`
- Source: `domains/dashboard/services.py` lines 1-138 — reference pattern for async SQLAlchemy service functions
- Source: `domains/dashboard/routes.py` lines 1-97 — reference pattern for APIRouter with auth and tenant dependencies
- Source: Epic 17 Story 17.3 (lines 2021-2040 of `_bmad-output/planning-artifacts/epics.md`)

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

N/A

### Completion Notes List

N/A

### File List

- `/Volumes/2T_SSD_App/Projects/UltrERP/backend/domains/reports/__init__.py` — created
- `/Volumes/2T_SSD_App/Projects/UltrERP/backend/domains/reports/schemas.py` — created
- `/Volumes/2T_SSD_App/Projects/UltrERP/backend/domains/reports/services.py` — created
- `/Volumes/2T_SSD_App/Projects/UltrERP/backend/domains/reports/routes.py` — created
- `/Volumes/2T_SSD_App/Projects/UltrERP/_bmad-output/implementation-artifacts/17-3-ar-aging-report-endpoint.md` — created
