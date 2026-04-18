# Story 4.11: Deactivate Product

**Status:** done

**Story ID:** 4.11

**Epic:** Epic 4 - Inventory Operations

---

## Story

As a warehouse manager,
I want to toggle products between active and inactive,
so that retired items disappear from day-to-day selection flows without losing historical data.

---

## Best-Practice Update

- Use one status-mutation contract instead of separate activate/deactivate RPC endpoints: `PATCH /api/v1/inventory/products/{product_id}/status` with a body of `{ "status": "active" | "inactive" }`.
- Hide inactive products from search and selectors by default, but make inclusion explicit through query/filter controls rather than creating a second inactive-only catalog.
- Treat inactive products as code-reserving records. Deactivation is a lifecycle change, not permission to reuse the code.

## Acceptance Criteria

1. Given an active product, when I set its status to `inactive`, then the product remains stored but no longer appears in default search or active-only product selectors.
2. Given an inactive product, when I set its status back to `active`, then it returns to default search results and normal selection flows.
3. Given I search products through the inventory search endpoint, when I do not request inactive rows explicitly, then inactive products are excluded by default.
4. Given I request inactive visibility explicitly, when I search or browse products, then inactive products are returned with a clear inactive status indicator.
5. Given an inactive product already holds a code, when another create/update flow attempts to reuse that code, then the API still returns HTTP 409.

## Tasks / Subtasks

- [x] **Task 1: Add the status write contract** (AC: 1, 2)
  - [x] Add `ProductStatusUpdate` to `backend/domains/inventory/schemas.py` with `status: Literal["active", "inactive"]`.
  - [x] Keep status mutation separate from the general edit payload so Story 4.10 stays focused on master-data edit fields.

- [x] **Task 2: Add backend status handling** (AC: 1, 2, 5)
  - [x] Add `set_product_status(session, tenant_id, product_id, status)` to `backend/domains/inventory/services.py`.
  - [x] Load by `id` and `tenant_id`; return `None` if the product does not exist.
  - [x] Update only the `status` field; do not change code, stock, or audit history semantics.
  - [x] Keep the existing duplicate-code rules unchanged so inactive rows still block code reuse.

- [x] **Task 3: Add the status route** (AC: 1, 2)
  - [x] Add `PATCH /api/v1/inventory/products/{product_id}/status` to `backend/domains/inventory/routes.py`.
  - [x] Use `WriteUser`, return HTTP 200 with `ProductResponse`, and return HTTP 404 for unknown products.

- [x] **Task 4: Extend product search semantics** (AC: 3, 4)
  - [x] Extend `search_products()` in `backend/domains/inventory/services.py` to accept `include_inactive: bool = False`.
  - [x] Extend the search route and `src/lib/api/inventory.ts` so the client can request inactive rows intentionally.
  - [x] Keep the default as active-only across search, comboboxes, and inventory tables.

- [x] **Task 5: Add the product-detail status UI** (AC: 1, 2, 4)
  - [x] Add an active/inactive badge and status-toggle action to `src/pages/inventory/ProductDetailPage.tsx`.
  - [x] Require explicit confirmation before deactivating.
  - [x] Refresh product-detail and product-search views after the status change completes.

- [x] **Task 6: Add search/filter UI support** (AC: 3, 4)
  - [x] Extend the product-search UI and table toolbar to expose a `Show inactive` filter.
  - [x] Make inactive rows visibly distinct in result tables and comboboxes.

- [x] **Task 7: Add focused regression tests** (AC: 1, 2, 3, 4, 5)
  - [x] Backend service/API tests for active→inactive, inactive→active, and not-found behavior.
  - [x] Backend search tests proving inactive rows are excluded by default and included only when requested.
  - [x] Frontend tests for the detail-page toggle, confirmation flow, and search filter behavior.

## Dev Notes

### Architecture Compliance

- This is a soft lifecycle toggle. Do not hard-delete product rows.
- Search and selector behavior should be driven by query filters, not by physically moving or duplicating records.
- Preserve tenant isolation on all status and search queries.

### Project Structure Notes

- Backend: `backend/domains/inventory/routes.py`, `backend/domains/inventory/services.py`, `backend/domains/inventory/schemas.py`
- Frontend: `src/lib/api/inventory.ts`, `src/domain/inventory/hooks/useProductSearch.ts`, `src/domain/inventory/components/ProductSearch.tsx`, `src/domain/inventory/components/ProductTable.tsx`, `src/pages/inventory/ProductDetailPage.tsx`

### What NOT to implement

- Do **not** add hard delete, archive tables, or code-recycling behavior.
- Do **not** cascade product deactivation into supplier orders, invoices, or stock history.
- Do **not** split this into separate `activate` and `deactivate` endpoints unless the repo's API style changes project-wide.

### Testing Standards

- Cover both status mutation and search behavior, because the user-facing value comes from both.
- Include a regression test showing that inactive rows still cause duplicate-code conflicts in create/update flows.

## Dependencies & Related Stories

- **Depends on:** Story 4.9 (Create Product) and Story 4.10 (Update Product) for product contracts
- **Related to:** Story 4.1 (Search Products) because search defaults must respect status

## References

- `backend/common/models/product.py`
- `backend/domains/inventory/services.py`
- `backend/domains/inventory/routes.py`
- `src/domain/inventory/components/ProductTable.tsx`
- `src/pages/inventory/ProductDetailPage.tsx`

---

## Dev Agent Record

**Status:** done
**Last Updated:** 2026-04-18

### Completion Notes List

- Added a dedicated product status mutation contract and `PATCH /api/v1/inventory/products/{product_id}/status` route instead of splitting activate/deactivate into separate endpoints.
- Moved product search to active-only defaults with an explicit `include_inactive` override that now flows through the backend service, API client, hook, table, and standalone product-search UI.
- Added product-detail activate/deactivate actions with explicit confirmation before deactivation and immediate detail refresh after status changes.
- Added focused regression coverage for status mutation, default search filtering, explicit inactive inclusion, and inactive-code duplicate protection.

### Validation

- `cd backend && .venv/bin/python -m pytest tests/domains/inventory/test_update_product.py tests/domains/inventory/test_product_status.py tests/api/test_product_status.py tests/domains/inventory/test_product_search.py -q`
- `pnpm vitest run src/pages/inventory/ProductDetailPage.test.tsx src/tests/inventory/ProductTable.test.tsx`
- `pnpm eslint src/domain/inventory/components/ProductSearch.tsx src/domain/inventory/components/ProductTable.tsx src/domain/inventory/hooks/useProductSearch.ts src/pages/inventory/ProductDetailPage.tsx src/tests/inventory/ProductTable.test.tsx src/pages/inventory/ProductDetailPage.test.tsx`

### File List

- `backend/domains/inventory/schemas.py`
- `backend/domains/inventory/services.py`
- `backend/domains/inventory/routes.py`
- `backend/tests/domains/inventory/test_product_status.py`
- `backend/tests/domains/inventory/test_update_product.py`
- `backend/tests/api/test_product_status.py`
- `src/domain/inventory/types.ts`
- `src/lib/api/inventory.ts`
- `src/domain/inventory/hooks/useProductSearch.ts`
- `src/domain/inventory/components/ProductTable.tsx`
- `src/domain/inventory/components/ProductSearch.tsx`
- `src/pages/inventory/ProductDetailPage.tsx`
- `src/pages/inventory/ProductDetailPage.test.tsx`
- `src/tests/inventory/ProductTable.test.tsx`
- `public/locales/en/common.json`
- `public/locales/zh-Hant/common.json`
