# Story 7.1: Morning Dashboard — Revenue Comparison

Status: done

## Story

As an owner,
I want to see today's revenue vs. yesterday's on a morning dashboard,
So that I can quickly assess business performance.

## Acceptance Criteria

**AC1:** Dashboard page renders
**Given** I am an authenticated owner
**When** I navigate to the dashboard route (`/`)
**Then** I see the Morning Dashboard page with a revenue comparison card
**And** the page loads in < 2 seconds (p95) (NFR1)

**AC2:** Today's revenue is displayed
**Given** invoices exist with `invoice_date = today` and `status != 'voided'`
**When** the dashboard loads
**Then** I see today's total invoiced revenue as a formatted currency (TWD)
**And** the amount equals `SUM(invoices.total_amount)` for today, excluding voided invoices

**AC3:** Yesterday's revenue is displayed
**Given** invoices exist with `invoice_date = yesterday` and `status != 'voided'`
**When** the dashboard loads
**Then** I see yesterday's total invoiced revenue as a formatted currency (TWD)

**AC4:** Percentage change is calculated
**Given** today's revenue = T and yesterday's revenue = Y
**When** both values are loaded
**Then** I see a percentage change displayed as `((T - Y) / Y) * 100` rounded to 1 decimal
**And** positive change shows green with ▲ indicator
**And** negative change shows red with ▼ indicator
**And** if Y = 0 and T > 0, show "+100%" (or "N/A" if both are 0)

**AC5:** Zero-data graceful handling
**Given** no invoices exist for today or yesterday
**When** the dashboard loads
**Then** revenue shows as $0.00 TWD for the missing day(s)
**And** the percentage change shows "—" (not a division-by-zero error)

**AC6:** Backend API endpoint
**Given** the backend is running
**When** I call `GET /api/v1/dashboard/revenue-summary`
**Then** the response returns JSON with `today_revenue`, `yesterday_revenue`, `change_percent`
**And** all amounts are `Decimal` serialized as strings with 2 decimal places
**And** the response is tenant-scoped

**AC7:** Audit-safe revenue query
**Given** the revenue query executes
**When** it aggregates invoice totals
**Then** it uses `invoices.total_amount` as the canonical revenue source (not order totals)
**And** it excludes voided invoices (`status != 'voided'`)
**And** it filters by `tenant_id` via RLS (`set_tenant`)

## Tasks / Subtasks

- [ ] **Task 1: Dashboard Domain — Backend Scaffold** (AC6)
  - [ ] Create `backend/domains/dashboard/__init__.py`
  - [ ] Create `backend/domains/dashboard/schemas.py`:
    ```python
    class RevenueSummaryResponse(BaseModel):
        model_config = ConfigDict(from_attributes=True)
        today_revenue: Decimal
        yesterday_revenue: Decimal
        change_percent: Decimal | None  # None when yesterday = 0
        today_date: date
        yesterday_date: date
    ```
  - [ ] Create `backend/domains/dashboard/services.py`
  - [ ] Create `backend/domains/dashboard/routes.py`
  - [ ] Mount in `backend/app/main.py`:
    ```python
    from domains.dashboard.routes import router as dashboard_router
    api_v1.include_router(dashboard_router, prefix="/dashboard", tags=["dashboard"])
    ```

- [ ] **Task 2: Revenue Summary Service** (AC2, AC3, AC4, AC5, AC7)
  - [ ] Implement `get_revenue_summary(session, tenant_id) -> RevenueSummaryResponse`:
    - Call `await set_tenant(session, tenant_id)` first
    - Within `async with session.begin():`
    - Query: `SELECT COALESCE(SUM(total_amount), 0) FROM invoices WHERE invoice_date = :date AND status != 'voided' AND tenant_id = :tid`
    - Execute for `date.today()` and `date.today() - timedelta(days=1)`
    - Compute `change_percent`:
      - if `yesterday == 0 and today == 0`: `None`
      - if `yesterday == 0 and today > 0`: `Decimal('100.0')`
      - else: `((today - yesterday) / yesterday * 100).quantize(Decimal('0.1'))`
    - Return `RevenueSummaryResponse`

- [ ] **Task 3: Revenue Summary Route** (AC6)
  - [ ] `GET /` → `get_revenue_summary_endpoint()`:
    - Uses `Depends(get_db)` for session
    - Returns `RevenueSummaryResponse`
    - actor_id from request context (hardcode DEFAULT_TENANT_ID for MVP)

- [ ] **Task 4: Frontend — Dashboard Page Scaffold** (AC1)
  - [ ] Create `src/pages/dashboard/DashboardPage.tsx`:
    - Root page component with grid layout for KPI cards
    - Add route in App.tsx: `path="/"` renders `DashboardPage`
    - Grid layout: 2×2 or responsive single column
  - [ ] Create `src/domain/dashboard/types.ts`:
    ```typescript
    export interface RevenueSummary {
      today_revenue: string;
      yesterday_revenue: string;
      change_percent: string | null;
      today_date: string;
      yesterday_date: string;
    }
    ```
  - [ ] Create `src/lib/api/dashboard.ts`:
    - `fetchRevenueSummary(): Promise<RevenueSummary>`

- [ ] **Task 5: Frontend — Revenue Comparison Card** (AC1-AC5)
  - [ ] Create `src/domain/dashboard/components/RevenueCard.tsx`:
    - Display today's revenue formatted: `NT$ 12,345.00`
    - Display yesterday's revenue
    - Display percentage change with color/icon
    - Loading skeleton state
    - Error fallback state
  - [ ] Create `src/domain/dashboard/hooks/useDashboard.ts`:
    - `useRevenueSummary()` — fetches on mount, returns { data, isLoading, error }

- [ ] **Task 6: Backend Tests** (AC2-AC7)
  - [ ] Create `backend/tests/domains/dashboard/__init__.py`
  - [ ] Create `backend/tests/domains/dashboard/test_revenue.py`
  - [ ] Follow `FakeAsyncSession` pattern from `tests/domains/orders/_helpers.py`:
    - Queue `set_tenant` scalar(None)
    - Queue today's SUM result
    - Queue yesterday's SUM result
  - [ ] Test: revenue with invoices both days → correct totals and percentage
  - [ ] Test: zero revenue yesterday → change_percent = 100 or None
  - [ ] Test: zero revenue both days → change_percent = None
  - [ ] Test: voided invoices are excluded
  - [ ] Test: negative change (today < yesterday)

- [ ] **Task 7: Frontend Tests** (AC1, AC4, AC5)
  - [ ] Create `src/domain/dashboard/__tests__/RevenueCard.test.tsx`
  - [ ] Test: renders today's and yesterday's revenue
  - [ ] Test: shows green ▲ for positive change
  - [ ] Test: shows red ▼ for negative change
  - [ ] Test: shows "—" when change_percent is null
  - [ ] Test: loading skeleton state

## Dev Notes

### Architecture Compliance

- **New domain:** `backend/domains/dashboard/` with `__init__.py`, `schemas.py`, `services.py`, `routes.py` — matches architecture §3 pattern
- **API mount:** `api_v1.include_router(dashboard_router, prefix="/dashboard", tags=["dashboard"])` inside `create_app()` — follows customers, invoices, orders, payments pattern
- **tenant_id:** `set_tenant(session, tid)` called at start of service function
- **Transaction pattern:** `async with session.begin():` wrapping reads (even though read-only, keeps pattern consistent)
- **No new models or migrations:** Revenue query aggregates existing `invoices` table; no schema changes needed

### Revenue Source Decision

- **Source:** `invoices.total_amount` (not `orders.total_amount`) — invoices are the canonical financial record
- **Filter:** `status != 'voided'` — voided invoices must not count toward revenue
- **Date field:** `invoices.invoice_date` (DATE type, not TIMESTAMPTZ) — exact date match, no timezone issues
- **Currency:** All amounts in TWD (single-currency system per architecture §2.1)

### Critical Warnings

- **Dashboard route as root:** The dashboard REPLACES the current `HomePage` component in `App.tsx`. The current `HomePage` is a navigation stub ("Epic 3 Customer Management" with Browse Customers/Orders buttons). Replace it with `DashboardPage` at `path="/"`. Keep the navigation links to Customers and Orders as part of the dashboard layout. Update `src/lib/routes.ts` to add `DASHBOARD_ROUTE = "/"` (or reuse `HOME_ROUTE`).
- **Decimal serialization:** Pydantic v2 serializes `Decimal` to strings in JSON by default. Frontend must parse with `parseFloat()` or a currency formatter. Do NOT use `float` in the backend schema.
- **Decimal formatting:** Pydantic v2 serializes `Decimal("0")` as `"0"`, not `"0.00"`. Use a `model_serializer` or `PlainSerializer` to enforce 2-decimal-place formatting, or handle in the frontend with `Number(value).toFixed(2)`.
- **set_tenant must precede query:** Even for read-only queries, RLS requires `set_tenant()` call
- **No invoice table lock needed:** Read-only aggregation; no `with_for_update()` required
- **Performance:** Keep the query simple — two scalar aggregations on indexed `(tenant_id, invoice_date)`. If no index exists on `invoice_date`, consider adding one in a future story (NOT this one — avoid scope creep).

### Project Structure Notes

- Backend: `backend/domains/dashboard/` — new domain directory to create
- Frontend:
  - `src/pages/dashboard/DashboardPage.tsx`
  - `src/domain/dashboard/types.ts`
  - `src/domain/dashboard/hooks/useDashboard.ts`
  - `src/domain/dashboard/components/RevenueCard.tsx`
  - `src/lib/api/dashboard.ts`
- Tests backend: `backend/tests/domains/dashboard/test_revenue.py`
- Tests frontend: `src/domain/dashboard/__tests__/RevenueCard.test.tsx`

### Previous Story Intelligence (Epics 5-6)

- **set_tenant pattern:** Every service function calls `await set_tenant(session, tid)` as first line. Tests must queue `session.queue_scalar(None)` for each set_tenant call.
- **Route pattern:** Routes use dependency injection for session via `Depends(get_db)`. Actor_id is hardcoded as "system" in MVP.
- **Test pattern:** Uses `FakeAsyncSession` with deterministic result queuing. Each `session.execute()` or `session.scalar()` call must have a corresponding queued result.
- **Frontend pattern:** Hooks use `useState` + `useEffect` for data fetching; mutation hooks return `{ mutate, isLoading, error }` pattern.
- **Currency formatting:** The project uses TWD. Format as `NT$ XX,XXX.00` or the locale-appropriate equivalent.
- **Invoice model:** `Invoice` lives in `domains/invoices/models.py`, uses `Uuid` from sqlalchemy (domain model convention). Fields: `id`, `tenant_id`, `invoice_number`, `invoice_date`, `total_amount`, `status`.

### References

- [Source: _bmad-output/planning-artifacts/prd.md#Journey 1] Morning Pulse Check — today's revenue vs. yesterday
- [Source: _bmad-output/planning-artifacts/prd.md#NFR1] Dashboard loads in < 2 seconds (p95)
- [Source: _bmad-output/planning-artifacts/epics.md#Epic 7, Story 7.1] AC definitions
- [Source: _bmad-output/planning-artifacts/epics.md#FR25] Owner can view morning dashboard with today's revenue vs. yesterday
- [Source: domains/invoices/models.py] Invoice model with total_amount, invoice_date, status fields
- [Source: backend/app/main.py] Router mounting pattern: api_v1.include_router(...)

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (via GitHub Copilot)

### Completion Notes List

- Story created with exhaustive codebase analysis of Invoice model, Order model, and existing domain patterns
- Revenue source decision documented: invoices.total_amount over orders.total_amount for financial accuracy
- Dashboard page scaffold designed as root route, future stories (7.2-7.6) will add widgets to same page
- Decimal serialization warning based on Pydantic v2 behavior observed in Epic 6 schemas
- 2026-04-04 follow-up: the shared tenant helper used by dashboard services now calls `SELECT set_config('app.tenant_id', :tid, true)` because asyncpg rejects parameterized `SET LOCAL`; this restored `GET /api/v1/dashboard/revenue-summary` in the authenticated dashboard flow.
