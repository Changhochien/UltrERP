# Story 4.14: Reorder Suggestions Generation

**Status:** done

**Story ID:** 4.14

**Epic:** Epic 4 - Inventory Operations

---

## Story

As a procurement planner,
I want a warehouse-aware reorder suggestion list with actionable quantities,
so that I can turn low-stock signals into draft supplier orders quickly.

---

## Best-Practice Update

- Reorder suggestions should be derived data over existing inventory/reorder state, not a new persisted table with synthetic suggestion IDs.
- Suggested quantity must use one deterministic inventory-position formula and avoid double-counting demand already baked into `target_stock_qty` or reorder-point calculations.
- One-click order creation should create draft supplier orders only when supplier resolution is clear; otherwise the UX should open a prefilled order form for human review instead of guessing a supplier.

## Acceptance Criteria

1. Given products are at or below their warehouse reorder threshold, when I open the reorder suggestions view, then I see product, warehouse, current stock, reorder point, inventory position, target stock, suggested quantity, and supplier hint data.
2. Given a product has stock-planning data, when a suggestion is generated, then `suggested_qty = max(0, target_stock_qty - inventory_position)` and falls back to reorder-point shortfall only when `target_stock_qty` is unavailable.
3. Given a single suggestion has a resolvable supplier, when I use the one-click action, then the system creates or opens a draft supplier order prefilled with product, warehouse, and suggested quantity.
4. Given multiple suggestions are selected, when I create orders in bulk, then rows are grouped by supplier and unresolved rows are surfaced back to the user for manual follow-up rather than silently skipped.
5. Given reorder alerts already exist, when suggestions are shown, then the data comes from the same warehouse-aware inventory signals instead of a second independent low-stock implementation.

## Tasks / Subtasks

- [x] **Task 1: Add a derived suggestion service** (AC: 1, 2, 5)
  - [x] Add `list_reorder_suggestions(session, tenant_id, warehouse_id=None)` to `backend/domains/inventory/services.py`.
  - [x] Reuse existing `InventoryStock` fields such as `quantity`, `reorder_point`, `target_stock_qty`, `on_order_qty`, `in_transit_qty`, and `reserved_qty`.
  - [x] Compute `inventory_position = current_stock + on_order_qty + in_transit_qty - reserved_qty`.
  - [x] Resolve supplier hints through the current product-supplier helper and leave the hint empty when none is known.

- [x] **Task 2: Add suggestion read and draft-order endpoints** (AC: 1, 3, 4)
  - [x] Add `GET /api/v1/inventory/reorder-suggestions`.
  - [x] Add `POST /api/v1/inventory/reorder-suggestions/orders` that accepts selected suggestion rows, groups them by supplier, and returns created draft-order IDs plus unresolved rows.
  - [x] Do not introduce a `suggestion_id` route unless suggestions become persisted entities in a later design change.

- [x] **Task 3: Reuse supplier-order infrastructure** (AC: 3, 4)
  - [x] Reuse `create_supplier_order()` for draft creation rather than forking a second purchase-order write path.
  - [x] If supplier resolution fails, return a payload the frontend can hand off to `SupplierOrderForm` with prefilled lines and a blank supplier selection.

- [x] **Task 4: Add frontend types, API helpers, and hook** (AC: 1, 3, 4)
  - [x] Add reorder-suggestion types to `src/domain/inventory/types.ts`.
  - [x] Add reorder-suggestion API helpers to `src/lib/api/inventory.ts`.
  - [x] Add `useReorderSuggestions` under `src/domain/inventory/hooks/`.

- [x] **Task 5: Build the reorder suggestions page** (AC: 1, 3, 4)
  - [x] Create `src/pages/inventory/ReorderSuggestionsPage.tsx`.
  - [x] Show warehouse filter, row selection, supplier hint, and single/bulk action buttons.
  - [x] Make unresolved rows visible in the UI instead of failing silently.

- [x] **Task 6: Link suggestions from existing inventory signals** (AC: 5)
  - [x] Add a navigation path from reorder alerts or inventory admin surfaces into the suggestions page.
  - [x] Reuse the same warehouse filter context already used by the inventory module.

- [x] **Task 7: Add focused regression tests** (AC: 1, 2, 3, 4, 5)
  - [x] Backend tests for quantity calculation, supplier grouping, and unresolved-row handling.
  - [x] Frontend tests for page rendering, bulk selection, draft-order handoff, and unresolved-state UX.

## Dev Notes

### Architecture Compliance

- Suggestions are advisory/read-model data over existing stock settings and supplier-order flows.
- Keep the calculation warehouse-aware and tenant-scoped.
- Reuse the existing supplier-order draft/create path; do not create a shadow purchase-order subsystem.

### Project Structure Notes

- Backend: `backend/domains/inventory/services.py`, `backend/domains/inventory/routes.py`, `backend/domains/inventory/schemas.py`
- Frontend: `src/pages/inventory/ReorderSuggestionsPage.tsx`, `src/domain/inventory/hooks/useReorderSuggestions.ts`, `src/lib/api/inventory.ts`
- Existing touchpoints to reuse: `backend/domains/inventory/services.py#get_product_supplier`, `src/domain/inventory/components/SupplierOrderForm.tsx`

### What NOT to implement

- Do **not** persist reorder suggestions in a new table for v1.
- Do **not** auto-confirm supplier orders or submit receipts from this story.
- Do **not** invent a second reorder formula separate from the inventory stock settings already in the repo.

### Testing Standards

- Validate both the quantity formula and the supplier-resolution edge cases.
- Include at least one regression test for unresolved supplier rows in bulk mode.

## Dependencies & Related Stories

- **Depends on:** Story 4.3 (Reorder Alerts), Story 4.5 (Supplier Orders), Story 4.7 (Reorder Point Calculation)
- **Related to:** Story 4.21 (Default Supplier per Product), which should become the preferred supplier source once implemented

## References

- `backend/common/models/inventory_stock.py`
- `backend/domains/inventory/services.py`
- `backend/domains/inventory/routes.py`
- `src/domain/inventory/components/SupplierOrderForm.tsx`
- `src/domain/inventory/context/WarehouseContext.tsx`

---

## Dev Agent Record

**Status:** done
**Last Updated:** 2026-04-18

### Completion Notes List

- Added a derived reorder-suggestions backend read model over existing `InventoryStock` fields, including the deterministic inventory-position formula, supplier-hint reuse, and grouped draft-order creation through the current supplier-order service.
- Shipped a warehouse-aware reorder suggestions page with row selection, single-row and bulk draft actions, created-order feedback, and explicit unresolved-row handling that hands prefilled lines into `SupplierOrderForm` instead of guessing a supplier.
- Linked the new suggestions flow from existing inventory entry points so planners can jump from alerts or the inventory workspace into the same warehouse-scoped recommendation surface.

### Validation

- `cd backend && . .venv/bin/activate && pytest -q tests/domains/inventory/test_reorder_suggestions.py tests/api/test_reorder_suggestions.py`
- `pnpm vitest run src/pages/inventory/ReorderSuggestionsPage.test.tsx src/domain/inventory/components/SupplierOrderForm.test.tsx`
- VS Code diagnostics: no new errors in the touched backend/frontend files for the 4.14 slice

### File List

- `backend/domains/inventory/schemas.py`
- `backend/domains/inventory/services.py`
- `backend/domains/inventory/routes.py`
- `backend/tests/domains/inventory/test_reorder_suggestions.py`
- `backend/tests/api/test_reorder_suggestions.py`
- `src/domain/inventory/types.ts`
- `src/lib/api/inventory.ts`
- `src/domain/inventory/hooks/useReorderSuggestions.ts`
- `src/domain/inventory/components/SupplierOrderForm.tsx`
- `src/domain/inventory/components/SupplierOrderForm.test.tsx`
- `src/domain/inventory/components/AlertPanel.tsx`
- `src/pages/InventoryPage.tsx`
- `src/pages/inventory/ReorderSuggestionsPage.tsx`
- `src/pages/inventory/ReorderSuggestionsPage.test.tsx`
- `src/lib/routes.ts`
- `src/lib/navigation.tsx`
- `src/App.tsx`
- `public/locales/en/common.json`
- `public/locales/zh-Hant/common.json`
