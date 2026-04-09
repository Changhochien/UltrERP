# Story 17.5: Cash Flow Endpoint

Status: done

## Implementation Status

**Backend:** DONE — `GET /api/v1/dashboard/cash-flow` endpoint implemented

**Files modified:**

1. `backend/domains/dashboard/schemas.py` — added `CashFlowItem`, `RunningBalanceItem`, `CashFlowResponse` Pydantic schemas
2. `backend/domains/dashboard/services.py` — added `get_cash_flow()` async function with:
   - Cash inflows query: `Payment` grouped by `payment_date`, filtered by `tenant_id` and `match_status IN ('matched', 'auto_matched')`
   - Cash outflows query: `SupplierPayment` grouped by `payment_date`, filtered by `tenant_id` and `status = 'applied'`
   - Running balance forward-fill for all dates in range (including dates with no transactions)
3. `backend/domains/dashboard/routes.py` — added `GET /dashboard/cash-flow` route with `start_date` and `end_date` Query parameters

**AC Coverage:**
- AC-1: Response includes `period_start`, `period_end`, `cash_inflows`, `cash_outflows`, `net_cash_flow`, `running_balance_by_date`
- AC-2: Dates with no transactions appear in `running_balance_by_date` with previous cumulative balance carried forward
- AC-3: Inflows filtered to `match_status IN ('matched', 'auto_matched')`
- AC-4: Outflows filtered to `status = SupplierPaymentStatus.APPLIED`
- AC-5: All queries filtered by `tenant_id`

## Story

As a backend developer,
I want to expose a `GET /api/v1/dashboard/cash-flow` endpoint,
So that the owner can see money in vs. money out over a date range.

## Acceptance Criteria

1. [AC-1] **Given** a valid authenticated request
   **When** `GET /api/v1/dashboard/cash-flow?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD` is called
   **Then** the response returns:
   - `period_start`: the start_date parameter
   - `period_end`: the end_date parameter
   - `cash_inflows`: array of `{date: string, amount: Decimal}` objects, one per date in range with at least one payment, summing all `Payment.amount` for that date
   - `cash_outflows`: array of `{date: string, amount: Decimal}` objects, one per date in range with at least one supplier payment, summing all `SupplierPayment.gross_amount` for that date
   - `net_cash_flow`: total cash_inflows amount minus total cash_outflows amount for the period
   - `running_balance_by_date[]`: array of `{date: string, cumulative_balance: Decimal}` objects in chronological order, where `cumulative_balance` is the running sum of net daily flows from `period_start` through that date

2. [AC-2] **Given** a date in the range that has no transactions
   **When** `running_balance_by_date` is computed
   **Then** that date is still represented in the array with the previous cumulative balance carried forward

3. [AC-3] **Given** the `cash_inflows` calculation
   **Then** only `Payment` records with `match_status IN ('matched', 'auto_matched')` are included (pending/unmatched payments are not yet received)

4. [AC-4] **Given** the `cash_outflows` calculation
   **Then** only `SupplierPayment` records with `status = 'applied'` are included (unapplied/prepayment supplier payments are not yet disbursed)

5. [AC-5] **Given** a valid authenticated request
   **Then** only records belonging to the authenticated tenant are included (tenant isolation via `tenant_id` filter on all queries)

## Tasks / Subtasks

- [x] Task 1 (AC: 1, 2, 5)
  - [x] Subtask 1.1: Define `CashFlowItem` (date + amount), `RunningBalanceItem` (date + cumulative_balance), and `CashFlowResponse` Pydantic schemas in `domains/dashboard/schemas.py`
  - [x] Subtask 1.2: Implement `get_cash_flow` async function in `domains/dashboard/services.py`
  - [x] Subtask 1.3: Query `Payment` grouped by `payment_date` for inflows (filter by tenant_id and match_status)
  - [x] Subtask 1.4: Query `SupplierPayment` grouped by `payment_date` for outflows (filter by tenant_id and status)
  - [x] Subtask 1.5: Merge the two result sets to produce a continuous date range from `period_start` to `period_end` with running cumulative balance
  - [x] Subtask 1.6: Add the route `GET /dashboard/cash-flow` with `start_date` and `end_date` Query params in `domains/dashboard/routes.py`
- [x] Task 2 (AC: 3)
  - [x] Subtask 2.1: Filter inflows: `Payment.match_status IN ('matched', 'auto_matched')`
- [x] Task 3 (AC: 4)
  - [x] Subtask 3.1: Filter outflows: `SupplierPayment.status = 'applied'`
- [x] Task 4 (AC: 5)
  - [x] Subtask 4.1: Filter all queries by `tenant_id`

## Dev Notes

- Relevant architecture patterns and constraints
  - All backend routes use `router = APIRouter(dependencies=[Depends(get_current_user)])` for auth
  - Tenant isolation via `tenant_id` column; inject via `get_tenant_id` dependency
  - Use SQLAlchemy 2.0 async with `AsyncSession`
  - Use `func.coalesce(func.sum(...), 0)` to avoid NULL in sums
  - Use `func.date()` or the native `Date` column type for grouping by payment date
  - `Payment` model: `domains/payments/models.py` → class `Payment`; fields: `tenant_id`, `amount` (Numeric 20,2), `payment_date` (Date), `match_status`
  - `SupplierPayment` model: `common/models/supplier_payment.py` → class `SupplierPayment`; fields: `tenant_id`, `gross_amount` (Numeric 20,2), `payment_date` (Date), `status` (SupplierPaymentStatus enum: UNAPPLIED/APPLIED/PARTIALLY_APPLIED/VOIDED)
  - The running balance must carry forward the last known balance on dates with no transactions (use a loop or pandas-like forward-fill approach in Python after fetching the merged daily totals)
  - `SupplierPaymentStatus` values: `UNAPPLIED`, `PARTIALLY_APPLIED`, `APPLIED`, `VOIDED` — only `APPLIED` counts as disbursed cash outflow

- Source tree components to touch
  - `domains/dashboard/schemas.py` — add `CashFlowItem`, `RunningBalanceItem`, `CashFlowResponse`
  - `domains/dashboard/services.py` — add `get_cash_flow` function
  - `domains/dashboard/routes.py` — add `GET /dashboard/cash-flow` route

- Testing standards summary
  - Unit test: mock DB sessions for Payment and SupplierPayment, assert inflows, outflows, and running balance values
  - Integration test: `GET /dashboard/cash-flow?start_date=...&end_date=...` with auth → 200, correct period dates, running balance monotonically increases/decreases correctly

### Project Structure Notes

- Alignment with unified project structure (paths, modules, naming)
  - Dashboard domain: `/Volumes/2T_SSD_App/Projects/UltrERP/backend/domains/dashboard/`
  - Route file: `/Volumes/2T_SSD_App/Projects/UltrERP/backend/domains/dashboard/routes.py`
  - Service file: `/Volumes/2T_SSD_App/Projects/UltrERP/backend/domains/dashboard/services.py`
  - Schema file: `/Volumes/2T_SSD_App/Projects/UltrERP/backend/domains/dashboard/schemas.py`
  - Payment model: `/Volumes/2T_SSD_App/Projects/UltrERP/backend/domains/payments/models.py`
  - SupplierPayment model: `/Volumes/2T_SSD_App/Projects/UltrERP/backend/common/models/supplier_payment.py`

- Detected conflicts or variances (with rationale)
  - None

### References

- Source: `domains/payments/models.py` — `Payment` class; `amount` is `Numeric(20, 2)`, `payment_date` is `Date`, `match_status` available for filtering
- Source: `common/models/supplier_payment.py` lines 40-103 — `SupplierPayment` class; `gross_amount` is `Numeric(20, 2)`, `payment_date` is `Date`, `status` is `SupplierPaymentStatus` enum
- Source: `domains/dashboard/services.py` lines 1-138 — reference pattern for async SQLAlchemy service functions with `tenant_id`
- Source: `domains/dashboard/routes.py` lines 1-97 — reference pattern for `APIRouter` with `Query` parameters
- Source: Epic 17 Story 17.5 (lines 2061-2078 of `_bmad-output/planning-artifacts/epics.md`)

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

N/A

### Completion Notes List

N/A

### File List

- `/Volumes/2T_SSD_App/Projects/UltrERP/backend/domains/dashboard/schemas.py` — modified (add cash flow schemas)
- `/Volumes/2T_SSD_App/Projects/UltrERP/backend/domains/dashboard/services.py` — modified (add `get_cash_flow`)
- `/Volumes/2T_SSD_App/Projects/UltrERP/backend/domains/dashboard/routes.py` — modified (add route)
- `/Volumes/2T_SSD_App/Projects/UltrERP/_bmad-output/implementation-artifacts/17-5-cash-flow-endpoint.md` — created
