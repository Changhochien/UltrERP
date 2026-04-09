# Story 17.2: KPI Summary Backend Endpoint

Status: done

## Implementation Status

**Backend:** NOT STARTED — `dashboard/routes.py` missing `/kpi-summary` endpoint; `dashboard/schemas.py` missing `KpiSummaryResponse`; `dashboard/services.py` missing `get_kpi_summary`

**Critical Issues:**
- `backend/domains/dashboard/schemas.py` missing `KpiSummaryResponse` schema (needs fields: today_revenue, yesterday_revenue, revenue_change_pct, open_invoice_count, open_invoice_amount, pending_order_count, pending_order_revenue, low_stock_product_count, overdue_receivables_amount)
- `backend/domains/dashboard/services.py` missing `get_kpi_summary` function
- `backend/domains/dashboard/routes.py` missing `GET /dashboard/kpi-summary` route

## Story

As a backend developer,
I want to expose a `GET /api/v1/dashboard/kpi-summary` endpoint,
So that the frontend owner dashboard can fetch all primary KPIs in a single request.

## Acceptance Criteria

1. [AC-1] **Given** a valid authenticated request with a Bearer token
   **When** `GET /api/v1/dashboard/kpi-summary` is called with optional `?date=YYYY-MM-DD` (defaults to today)
   **Then** the response returns all of the following fields:
   - `today_revenue`: sum of `Invoice.total_amount` where `invoice_date = today` and `status = 'issued'`
   - `yesterday_revenue`: same calculation for yesterday
   - `revenue_change_pct`: `(today_revenue − yesterday_revenue) / yesterday_revenue × 100`, rounded to 1 decimal place; `null` if yesterday_revenue is 0
   - `open_invoice_count`: count of `Invoice` with `status = 'issued'` and not fully paid
   - `open_invoice_amount`: sum of outstanding amount on open invoices (i.e., `total_amount − coalesce(sum(Payment.amount), 0)`)
   - `pending_order_count`: count of `Order` with `status in ('pending', 'confirmed')`
   - `pending_order_revenue`: sum of `Order.total_amount` for orders with `status in ('pending', 'confirmed')`
   - `low_stock_product_count`: count of products where `InventoryStock.quantity < InventoryStock.reorder_point`
   - `overdue_receivables_amount`: sum of `Invoice.total_amount` where `due_date < today` and `status = 'issued'`

2. [AC-2] **Given** the endpoint is called
   **Then** the response includes `Cache-Control: public, max-age=300` header
   **And** the response is cached for 5 minutes server-side

3. [AC-3] **Given** a tenant with ≤ 10,000 invoices
   **When** the endpoint is called
   **Then** response time is < 500ms under normal load

4. [AC-4] **Given** a valid authenticated request
   **When** the endpoint is called
   **Then** only records belonging to the authenticated tenant are included (tenant isolation via `tenant_id` filter on all queries)

## Tasks / Subtasks

- [x] Task 1 (AC: 1, 4)
  - [x] Subtask 1.1: Define `KpiSummaryResponse` Pydantic schema in `domains/dashboard/schemas.py` with all 9 fields listed in AC-1
  - [x] Subtask 1.2: Implement `get_kpi_summary` async function in `domains/dashboard/services.py` using the existing `get_revenue_summary` pattern as a reference
  - [x] Subtask 1.3: Add tenant_id filter to all queries (pattern: `Invoice.tenant_id == tenant_id`, `Order.tenant_id == tenant_id`, `InventoryStock.tenant_id == tenant_id`)
  - [x] Subtask 1.4: Wire the service function to a new route `GET /dashboard/kpi-summary` in `domains/dashboard/routes.py`
- [x] Task 2 (AC: 2)
  - [x] Subtask 2.1: Add a 5-minute in-memory cache using `functools.lru_cache` or `cachetools.TTLCache` keyed by `(tenant_id, date_str)`
  - [x] Subtask 2.2: Set `Cache-Control: public, max-age=300` response header on the route using FastAPI's `Response` parameter
- [x] Task 3 (AC: 3)
  - [x] Subtask 3.1: Add a SQL index on `Invoice.status` if not already present (check `Invoice` model indexes)
  - [x] Subtask 3.2: Use `func.coalesce(func.sum(...), 0)` for all sum aggregations to avoid NULL
  - [x] Subtask 3.3: Verify query plans for the 3 most expensive sub-queries

## Dev Notes

- Relevant architecture patterns and constraints
  - All backend routes under `domains/<domain>/routes.py` use `router = APIRouter(dependencies=[Depends(get_current_user)])` for auth
  - Database access uses SQLAlchemy 2.0 async with `AsyncSession` (see `domains/dashboard/services.py`)
  - Tenant isolation is enforced via `tenant_id` column on all models; `get_tenant_id` dependency injected per route
  - Existing `RevenueSummaryResponse` in `domains/dashboard/schemas.py` uses `Decimal` for monetary values
  - Existing `Invoice` model is at `domains/invoices/models.py` → `Invoice` class; `status` field uses string enum ('issued', 'voided', etc.)
  - Existing `Order` model is at `common/models/order.py`; `status` field is a string
  - `InventoryStock` model is at `common/models/inventory_stock.py`; has `quantity` and `reorder_point` columns
  - `Payment` model is at `domains/payments/models.py`; has `invoice_id`, `amount`, `tenant_id`

- Source tree components to touch
  - `domains/dashboard/schemas.py` — add `KpiSummaryResponse`
  - `domains/dashboard/services.py` — add `get_kpi_summary` function
  - `domains/dashboard/routes.py` — add `GET /dashboard/kpi-summary` route
  - No new model files needed

- Testing standards summary
  - Unit test: mock DB session, call `get_kpi_summary`, assert all 9 fields are returned
  - Integration test: call `GET /dashboard/kpi-summary` with auth, assert 200, assert cache headers
  - Performance: response time < 500ms on dataset ≤ 10k invoices

### Project Structure Notes

- Alignment with unified project structure (paths, modules, naming)
  - Dashboard domain: `/Volumes/2T_SSD_App/Projects/UltrERP/backend/domains/dashboard/`
  - Route file: `/Volumes/2T_SSD_App/Projects/UltrERP/backend/domains/dashboard/routes.py`
  - Service file: `/Volumes/2T_SSD_App/Projects/UltrERP/backend/domains/dashboard/services.py`
  - Schema file: `/Volumes/2T_SSD_App/Projects/UltrERP/backend/domains/dashboard/schemas.py`
  - Common models: `/Volumes/2T_SSD_App/Projects/UltrERP/backend/common/models/`
  - Invoice domain models: `/Volumes/2T_SSD_App/Projects/UltrERP/backend/domains/invoices/models.py`
  - Payment domain models: `/Volumes/2T_SSD_App/Projects/UltrERP/backend/domains/payments/models.py`

- Detected conflicts or variances (with rationale)
  - None

### References

- Source: `domains/dashboard/routes.py` lines 1-97 — existing route patterns with auth, tenant injection, and async session
- Source: `domains/dashboard/services.py` lines 1-138 — existing service pattern (revenue summary), shows exact SQLAlchemy async patterns to reuse
- Source: `domains/invoices/models.py` — `Invoice` model with `total_amount`, `status`, `invoice_date`, `due_date` fields
- Source: `common/models/order.py` — `Order` model with `total_amount`, `status` fields
- Source: `common/models/inventory_stock.py` — `InventoryStock` with `quantity`, `reorder_point`
- Source: `domains/payments/models.py` — `Payment` model with `invoice_id`, `amount`
- Source: Epic 17 Story 17.2 (lines 1996-2018 of `_bmad-output/planning-artifacts/epics.md`)

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

N/A

### Completion Notes List

N/A

### File List

- `/Volumes/2T_SSD_App/Projects/UltrERP/backend/domains/dashboard/schemas.py` — modified (add `KpiSummaryResponse`)
- `/Volumes/2T_SSD_App/Projects/UltrERP/backend/domains/dashboard/services.py` — modified (add `get_kpi_summary`)
- `/Volumes/2T_SSD_App/Projects/UltrERP/backend/domains/dashboard/routes.py` — modified (add route)
- `/Volumes/2T_SSD_App/Projects/UltrERP/_bmad-output/implementation-artifacts/17-2-kpi-summary-backend.md` — created

## Implementation Status

**Backend:** DONE — `dashboard/routes.py` has `GET /dashboard/kpi-summary`; `dashboard/schemas.py` has `KpiSummaryResponse`; `dashboard/services.py` has `get_kpi_summary`

**Completed:**
- `KpiSummaryResponse` Pydantic schema added to `schemas.py` with all 9 fields: `today_revenue`, `yesterday_revenue`, `revenue_change_pct`, `open_invoice_count`, `open_invoice_amount`, `pending_order_count`, `pending_order_revenue`, `low_stock_product_count`, `overdue_receivables_amount`
- `get_kpi_summary` async function in `services.py` implementing all AC queries: revenue (today/yesterday), open invoices with outstanding amount via payments subquery, pending orders, low-stock products, overdue receivables
- `GET /dashboard/kpi-summary` route in `routes.py` with optional `?date=YYYY-MM-DD` query param
- `Cache-Control: public, max-age=300` header set on response
- All queries include `tenant_id` filter for tenant isolation
- Uses `func.coalesce` for all sum aggregations to avoid NULL

**Files modified:**
- `/Volumes/2T_SSD_App/Projects/UltrERP/backend/domains/dashboard/schemas.py`
- `/Volumes/2T_SSD_App/Projects/UltrERP/backend/domains/dashboard/services.py`
- `/Volumes/2T_SSD_App/Projects/UltrERP/backend/domains/dashboard/routes.py`
