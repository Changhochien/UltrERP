# Story 2.8: Advanced Invoice & Order List Filter UI

**Status:** in-progress

**Story ID:** 2.8

---

## Story

As a finance clerk or sales rep,
I want to filter, search, and sort invoices and orders using multiple criteria simultaneously,
so that I can quickly find specific records without navigating through large datasets.

---

## Story (Cross-Epic Note)

This story spans Epic 2 (Invoice Lifecycle) and Epic 5 (Order to Cash). It is filed under Epic 2 for sprint-tracking purposes but its implementation serves both epics equally.

---

## Acceptance Criteria

**AC1: Invoice list — status multi-select filter**
**Given** the invoice list is displayed
**When** the user clicks the status filter control
**Then** a multi-select popover shows all status options (All, Unpaid, Partial, Paid, Overdue) as checkboxes
**And** multiple statuses can be selected simultaneously
**And** the selected statuses filter the list server-side (comma-separated or repeated query param)

**AC2: Invoice list — customer filter**
**Given** the invoice list is displayed
**When** the user opens the customer filter
**Then** the existing `CustomerCombobox` component renders in a popover
**And** selecting a customer filters the list to that customer only
**And** a clear/× button removes the customer filter

**AC3: Invoice list — date range filter**
**Given** the invoice list is displayed
**When** the user enters a from-date and/or to-date
**Then** the list is filtered to invoices with `invoice_date` within the range
**And** the backend `list_invoices` service is called with `date_from` and `date_to` params (see Dev Notes)

**AC4: Invoice list — free-text search**
**Given** the invoice list is displayed
**When** the user types in a search field
**Then** after 300 ms debounce the list is filtered server-side by `invoice_number` (partial match, case-insensitive)
**And** the search term is reflected in the URL

**AC5: Order list — status multi-select filter**
**Given** the order list is displayed
**When** the user clicks the status filter control
**Then** the same multi-select pattern as AC1 applies for order statuses (Pending, Confirmed, Shipped, Fulfilled, Cancelled)

**AC6: Order list — customer filter**
**Given** the order list is displayed
**When** the user opens the customer filter
**Then** the existing `CustomerCombobox` component is reused
**And** selecting a customer filters the order list to that customer only

**AC7: Order list — date range filter**
**Given** the order list is displayed
**When** the user enters a from-date and/or to-date
**Then** the list is filtered to orders with `created_at` within the range

**AC8: Order list — free-text search**
**Given** the order list is displayed
**When** the user types in a search field
**Then** after 300 ms debounce the list is filtered server-side by `order_number` (partial match, case-insensitive)

**AC9: URL as source of truth**
**Given** any filter is applied to the invoice or order list
**When** the page URL is bookmarked or shared
**Then** all filter state (status[], customer_id, date_from, date_to, search, sort_by, sort_order, page) is encoded in URL query params
**And** loading the URL restores the exact filtered view

**AC10: Active filter chips**
**Given** one or more filters are applied
**When** the filter bar is displayed
**Then** each active filter shows as a dismissible chip (label + ×)
**And** clicking × on a chip removes that individual filter
**And** a "Clear all" link appears when 2+ filters are active

**AC11: Backend — orders endpoint sort support**
**Given** the frontend sends `sort_by` and `sort_order` params
**When** `GET /api/v1/orders` is called
**Then** the results are sorted by the specified column and direction
**And** valid `sort_by` values are: `created_at`, `order_number`, `total_amount`, `status`
**And** `sort_order` is `asc` or `desc`

**AC12: Invoice list — sort integration**
**Given** the invoice list is displayed
**When** the user clicks a sortable column header
**Then** the `sortState` is synced to URL params (`sort_by`, `sort_order`)
**And** the backend is called with those params (already supported by backend)

---

## Tasks / Subtasks

### Task 1: Backend — add sort support to orders endpoint (AC: 11)
- [ ] Add `sort_by: Literal["created_at", "order_number", "total_amount", "status"] | None = Query(default=None)` to `list_orders_endpoint` in `backend/domains/orders/routes.py`
- [ ] Add `sort_order: str = Query(default="desc", pattern="^(asc|desc)$")` to the same endpoint
- [ ] Update `list_orders` service in `backend/domains/orders/services.py` to accept `sort_by` and `sort_order` params
- [ ] Apply ORDER BY clause in the SQL query based on sort param
- [ ] Add backend unit tests for sort behavior in `backend/tests/domains/orders/`
- [ ] Verify existing order API tests still pass

### Task 2: Backend — add date range filter to invoices endpoint (AC: 3, 7)
- [ ] Add `date_from: date | None = Query(default=None)` and `date_to: date | None = Query(default=None)` to `list_all` in `backend/domains/invoices/routes.py`
- [ ] Update `list_invoices` service in `backend/domains/invoices/service.py` to filter by `invoice_date` range
- [ ] Add `date_from: date | None` and `date_to: date | None` params to `list_orders` service in `backend/domains/orders/services.py` (for orders `created_at` range)
- [ ] Add date range query params to `GET /api/v1/orders` route in `backend/domains/orders/routes.py`

### Task 3: Shared filter UI primitives (AC: 1, 5, 10)
- [ ] Create `src/components/filters/ActiveFilterChip.tsx` — pill with label + × dismiss button
- [ ] Create `src/components/filters/ActiveFilterBar.tsx` — renders array of `ActiveFilterChip` + "Clear all" link
- [ ] Create `src/components/filters/StatusMultiSelect.tsx` — popover + checklist of status options; replaces the plain `<select>` in both list components
- [ ] Create `src/components/filters/DateRangeFilter.tsx` — two date inputs (from/to) with label
- [ ] Create `src/components/filters/SearchInput.tsx` — text input with debounce (300 ms) and optional search icon

### Task 4: Frontend — update InvoiceList (AC: 1–4, 6, 9, 10, 12)
- [ ] Add `useSearchParams` from `react-router-dom` to `InvoiceList.tsx`
- [ ] Replace `useState` filter hooks with filter state derived from and synced to `useSearchParams`
- [ ] Replace the plain `<select>` status filter with `StatusMultiSelect` (payment statuses)
- [ ] Add `CustomerCombobox` as a filter control (popover trigger showing selected customer name)
- [ ] Add `SearchInput` for `invoice_number` search
- [ ] Add `DateRangeFilter` for `date_from`/`date_to`
- [ ] Add `ActiveFilterBar` showing all active filters as chips
- [ ] Sync column-header sort state to URL params (`sort_by`, `sort_order`)
- [ ] Update `useInvoices` hook to accept `date_from`, `date_to`, and `search` params and pass them to `fetchInvoices`
- [ ] Update `fetchInvoices` in `src/lib/api/invoices.ts` to accept and pass `date_from`, `date_to` params
- [ ] Verify existing `InvoiceList` tests still pass; add tests for filter combinations

### Task 5: Frontend — update OrderList (AC: 5–10)
- [ ] Add `useSearchParams` from `react-router-dom` to `OrderList.tsx`
- [ ] Replace `useState` filter hooks with filter state derived from and synced to `useSearchParams`
- [ ] Replace the plain `<select>` status filter with `StatusMultiSelect` (order statuses)
- [ ] Add `CustomerCombobox` as a filter control
- [ ] Add `SearchInput` for `order_number` search
- [ ] Add `DateRangeFilter` for `date_from`/`date_to`
- [ ] Add `ActiveFilterBar` showing all active filters as chips
- [ ] Sync column sort state to URL params (`sort_by`, `sort_order`) — new behavior since backend now supports it
- [ ] Update `useOrders` hook to accept `date_from`, `date_to`, `sort_by`, `sort_order` params and pass them to `fetchOrders`
- [ ] Update `fetchOrders` in `src/lib/api/orders.ts` to accept and pass all new params
- [ ] Add tests for filter combinations

---

## Dev Notes

### Backend sort support gap

The invoices endpoint (`list_all` in `backend/domains/invoices/routes.py:60–89`) already accepts `sort_by` and `sort_order`. The orders endpoint (`list_orders_endpoint` in `backend/domains/orders/routes.py:117–157`) does NOT — this needs to be added in Task 1.

### Invoice date_from/date_to backend

`list_invoices` service (`backend/domains/invoices/service.py`) filters by `invoice_date`. Pass `date_from` and `date_to` as `date` objects or ISO strings and filter as `invoice_date >= date_from AND invoice_date <= date_to`. The existing `list_invoices` service signature needs to be updated to accept these params.

### Orders date_from/date_to backend

Orders filter by `created_at`. Apply the same pattern as invoices but filter on `Order.created_at`.

### Frontend URL encoding for array params

For multi-select status (e.g., `["unpaid", "overdue"]`), encode as repeated query params:
```
?payment_status=unpaid&payment_status=overdue
```
The backend `list_invoices` route already uses a `Literal` union — if multi-select is needed, change `payment_status: Literal["paid", "unpaid", "partial", "overdue"] | None` to `payment_status: list[Literal["paid", "unpaid", "partial", "overdue"]] | None = Query(default=None)` in the route. Same pattern for order status in `OrderStatus` enum.

### Debounce

Use a 300 ms debounce on the `SearchInput` before updating URL params. Use `useDeferredValue` from React or a simple `setTimeout`-based custom hook to avoid excessive API calls.

### Shared filter components location

Create `src/components/filters/` as a new directory. All filter primitives are shared between InvoiceList and OrderList.

### Existing patterns to follow

- `CustomerCombobox` at `src/components/customers/CustomerCombobox.tsx` — already implemented, reuse as-is
- `DataTableToolbar` at `src/components/layout/DataTable.tsx:73` — filter bar slots in here
- `Badge` at `src/components/ui/badge.tsx` — used for status pills
- `useSearchParams` usage in `src/pages/inventory/ProductDetailPage.tsx:2` — pattern to follow for URL sync

### Files to modify

**Backend:**
- `backend/domains/orders/routes.py` — add sort_by, sort_order, date_from, date_to query params
- `backend/domains/orders/services.py` — update list_orders to support sorting and date filtering
- `backend/domains/invoices/routes.py` — add date_from, date_to query params
- `backend/domains/invoices/service.py` — update list_invoices date range filter
- `backend/domains/orders/schemas.py` — may need new query param schemas

**Frontend:**
- `src/lib/api/invoices.ts` — add date_from, date_to params
- `src/lib/api/orders.ts` — add sort_by, sort_order, date_from, date_to params
- `src/domain/invoices/hooks/useInvoices.ts` — accept new filter params
- `src/domain/orders/hooks/useOrders.ts` — accept new filter params
- `src/domain/invoices/components/InvoiceList.tsx` — wire up all filters + URL sync
- `src/domain/orders/components/OrderList.tsx` — wire up all filters + URL sync
- `src/components/filters/ActiveFilterChip.tsx` — new
- `src/components/filters/ActiveFilterBar.tsx` — new
- `src/components/filters/StatusMultiSelect.tsx` — new
- `src/components/filters/DateRangeFilter.tsx` — new
- `src/components/filters/SearchInput.tsx` — new

### Testing

- Backend: add pytest for orders sort + date filter in `backend/tests/domains/orders/`
- Backend: add pytest for invoice date range filter in `backend/tests/domains/invoices/`
- Frontend: add Vitest tests for filter chip rendering and URL sync behavior
- Existing tests must continue to pass (no regression)

---

## Review Findings

### Senior Developer Review (AI)

**Review Outcome:** Changes Requested
**Review Date:** 2026-04-13
**Reviewers:** blind-hunter, edge-hunter, acceptance-auditor
**Files Reviewed:** 12 files + 6 new filter components (~1183 insertions)

---

### Action Items

- [ ] [Review][Patch] Backend `search` param not accepted — AC4/AC8 broken [`backend/domains/invoices/routes.py`, `backend/domains/invoices/service.py`, `backend/domains/orders/routes.py`, `backend/domains/orders/services.py`]
- [x] [Review][Patch] CustomerCombobox missing clear/× button — **FIXED** [`CustomerCombobox.tsx`, `InvoiceList.tsx`, `OrderList.tsx`]
- [x] [Review][Patch] `customerId` filter chip shows raw UUID not customer name — **FIXED** [`InvoiceList.tsx`, `OrderList.tsx` via `onCustomersLoaded` callback]
- [ ] [Review][Patch] Invoice `payment_status` sends array but backend Literal is single-value — **PARTIAL** [`invoices/routes.py` — needs `list[Literal[...]]`]
- [x] [Review][Patch] `clearAllFilters` preserves sort params — **FIXED** [`InvoiceList.tsx` — now clears all]
- [x] [Review][Defer] Warehouse race condition in `_get_default_warehouse_id` [`orders/services.py:566`] — deferred, pre-existing
- [x] [Review][Defer] No `date_from <= date_to` cross-validation [`invoices/routes.py`, `orders/routes.py`] — deferred, pre-existing
- [x] [Review][Defer] `updated_count=0` in dry_run when no candidates [`invoices/service.py:413`] — deferred, pre-existing
- [x] [Review][Dismiss] `statusValues` cast bypasses TypeScript type safety [`OrderList.tsx:1357`] — dismissed, FastAPI validates server-side
- [x] [Review][Dismiss] Debounce timer cleanup depends on stable `onChange` [`SearchInput.tsx:21`] — dismissed, `onChange` is `useCallback` stabilized

**Additional fixes applied during review:**
- Removed misleading "Type at least 3 characters" prompt in `CustomerCombobox` — search now works on any input length; BAN search was already functional but hidden behind the 3-char UX gate
- Added `aria-label` to `StatusMultiSelect` button to match existing test expectations

---

### Summary

| AC | Status |
|---|---|
| AC1 Invoice status multi-select | PARTIAL — frontend correct, backend Literal mismatch (patch pending) |
| AC2 CustomerCombobox clear button | **FIXED** |
| AC3 Invoice date range | OK |
| AC4 Invoice search | MISSING backend (patch pending) |
| AC5 Order status multi-select | OK |
| AC6 Order CustomerCombobox clear | **FIXED** |
| AC7 Order date range | OK |
| AC8 Order search | MISSING backend (patch pending) |
| AC9 URL as source of truth | OK |
| AC10 Active filter chips + Clear all | **FIXED** |
| AC11 Order backend sort | OK |
| AC12 Invoice sort URL sync | OK |

**Remaining blockers:** AC4/AC8 (backend `search` param not implemented), AC1 (backend `payment_status` Literal single-value mismatch)

---

## Dev Agent Record

### Agent Model Used

sonnet

### Debug Log References

### Completion Notes List

### File List

Backend:
- backend/domains/orders/routes.py
- backend/domains/orders/services.py
- backend/domains/invoices/routes.py
- backend/domains/invoices/service.py

Frontend:
- src/lib/api/invoices.ts
- src/lib/api/orders.ts
- src/domain/invoices/hooks/useInvoices.ts
- src/domain/orders/hooks/useOrders.ts
- src/domain/invoices/components/InvoiceList.tsx
- src/domain/orders/components/OrderList.tsx
- src/components/filters/ActiveFilterChip.tsx (new)
- src/components/filters/ActiveFilterBar.tsx (new)
- src/components/filters/StatusMultiSelect.tsx (new)
- src/components/filters/DateRangeFilter.tsx (new)
- src/components/filters/SearchInput.tsx (new)
