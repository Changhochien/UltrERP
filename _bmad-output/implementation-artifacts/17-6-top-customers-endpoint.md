# Story 17.6: Top Customers Endpoint

Status: done

## Implementation Status

**Backend:** DONE — `GET /dashboard/top-customers` implemented

**Critical Issues:**
- `backend/domains/dashboard/schemas.py` missing `TopCustomerItem`, `TopCustomersResponse` schemas
- `backend/domains/dashboard/services.py` missing `get_top_customers` function
- `backend/domains/dashboard/routes.py` missing `GET /dashboard/top-customers` route

## Story

As a backend developer,
I want to expose a `GET /dashboard/top-customers` endpoint,
So that the owner can see which customers generate the most revenue.

## Acceptance Criteria

**AC1:** Endpoint returns top customers by revenue
**Given** a valid authenticated request
**When** `GET /api/v1/dashboard/top-customers?period=month&limit=10` is called
**Then** the response returns a JSON object with a `customers` array sorted by `total_revenue` descending
**And** each customer object contains: `customer_id`, `company_name`, `total_revenue`, `invoice_count`, `last_invoice_date`
**And** results are limited to `limit` items (default 10, max 100)

**AC2:** Period filtering
**Given** a valid period parameter
**When** `period` is one of: `month` (current calendar month), `quarter` (current quarter), `year` (current year)
**Then** only invoices with `invoice_date` within the period are included in the aggregation
**And** invalid period values return HTTP 422

**AC3:** Revenue calculation
**Given** invoices in the period for a customer
**When** `total_revenue` is computed
**Then** it equals `SUM(invoices.total_amount)` for invoices with `status IN ('paid', 'issued')` (non-voided)
**And** voided invoices are excluded

**AC4:** Default values
**Given** the request has no `period` query parameter
**When** the endpoint is called
**Then** `period` defaults to `month`
**And** `limit` defaults to `10`

**AC5:** Empty result handling
**Given** no invoices exist for the period
**When** the endpoint is called
**Then** an empty `customers` array is returned with HTTP 200

## Tasks / Subtasks

- [x] **Task 1: Dashboard Domain — Top Customers Schema** (AC1, AC4)
  - [x] Add to `backend/domains/dashboard/schemas.py`:
    ```python
    class TopCustomerItem(BaseModel):
        customer_id: uuid.UUID
        company_name: str
        total_revenue: Decimal
        invoice_count: int
        last_invoice_date: date

    class TopCustomersResponse(BaseModel):
        period: str
        start_date: date
        end_date: date
        customers: list[TopCustomerItem]
    ```

- [x] **Task 2: Top Customers Service** (AC2, AC3, AC5)
  - [x] Implement `get_top_customers(session, tenant_id, period, limit) -> TopCustomersResponse`:
    - Call `await set_tenant(session, tenant_id)` first
    - Compute `start_date` and `end_date` from period (month/quarter/year)
    - Query: aggregate invoices by customer_id, join Customer for company_name
    - Filter: `invoice_date BETWEEN start_date AND end_date AND status IN ('paid', 'issued')`
    - Aggregate: SUM(total_amount), COUNT(*), MAX(invoice_date)
    - Order: total_revenue DESC, limit
    - Return TopCustomersResponse

- [x] **Task 3: Top Customers Route** (AC1, AC2, AC4)
  - [x] Add to `backend/domains/dashboard/routes.py`:
    ```python
    @router.get("/top-customers", response_model=TopCustomersResponse)
    async def get_top_customers(
        period: Literal["month", "quarter", "year"] = Query(default="month"),
        limit: int = Query(default=10, ge=1, le=100),
        ...
    ):
    ```

- [x] **Task 4: Backend Tests** (AC1-AC5)
  - [x] Create `backend/tests/domains/dashboard/test_top_customers.py`
  - [x] Test: returns top N customers sorted by revenue
  - [x] Test: period=month filters by current calendar month
  - [x] Test: period=quarter filters by current quarter
  - [x] Test: period=year filters by current year
  - [x] Test: voided invoices excluded from aggregation
  - [x] Test: empty result returns empty array

## Dev Notes

### Architecture Compliance

- **Domain:** `backend/domains/dashboard/` — same domain used by stories 7.1, 17.2, 17.3, 17.4, 17.5
- **Router mount:** already mounted at `/dashboard` in `api_v1`; no change needed
- **tenant_id:** `set_tenant(session, tid)` called at start of service function
- **Transaction pattern:** `async with session.begin():` wrapping reads

### Invoice and Customer Model References

- **Invoice model:** `backend/domains/invoices/models.py` — fields: `id`, `tenant_id`, `invoice_number`, `invoice_date`, `total_amount`, `status`
- **Invoice status values:** `'issued'`, `'paid'`, `'partial'`, `'overdue'`, `'voided'` (from `domains/invoices/models.py`)
- **Customer model:** `backend/domains/customers/models.py` — fields: `id`, `company_name`
- **Join:** invoices JOIN customers ON invoices.customer_id = customers.id

### Revenue Source Decision

- **Revenue source:** `invoices.total_amount` — same as story 7.1, invoices are the canonical financial record
- **Status filter:** `status IN ('paid', 'issued')` — only non-voided, actively issued invoices count as revenue
- **Period date field:** `invoices.invoice_date` (DATE type)

### Decimal Serialization

- Pydantic v2 serializes `Decimal` to strings in JSON. Frontend must parse with `parseFloat()`.
- Format all monetary fields as Decimal with 2 decimal places.

### Project Structure Notes

- Backend: `backend/domains/dashboard/schemas.py` (extend), `backend/domains/dashboard/services.py` (extend), `backend/domains/dashboard/routes.py` (extend)
- Tests: `backend/tests/domains/dashboard/test_top_customers.py`
- Frontend consumer: story 17.12 (Top Customers Card Frontend)

### Previous Story Intelligence (Story 7.1)

- `set_tenant` pattern: Every service function calls `await set_tenant(session, tid)` as first line
- Tests use `FakeAsyncSession` with deterministic result queuing
- Router uses dependency injection via `Depends(get_db)`
- Actor_id hardcoded as "system" in MVP

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 17.6] AC definitions
- [Source: backend/domains/invoices/models.py] Invoice model
- [Source: backend/domains/customers/models.py] Customer model
- [Source: backend/domains/dashboard/routes.py] Dashboard router (existing mount pattern)
- [Source: _bmad-output/implementation-artifacts/7-1-morning-dashboard-revenue-comparison.md] Revenue query patterns, set_tenant pattern
