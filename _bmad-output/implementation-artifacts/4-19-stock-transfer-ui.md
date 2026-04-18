# Story 4.19: Stock Transfer UI

**Status:** done

**Story ID:** 4.19

**Epic:** Epic 4 - Inventory Operations

---

## Story

As a warehouse staff member,
I want a polished stock-transfer workflow and transfer history view,
so that inter-warehouse stock movement is easy to perform and audit from the UI.

---

## Best-Practice Update

- The backend already performs immediate stock transfers and records `StockTransferHistory`. This story should add the missing list/history/detail UX and refine the modal form instead of inventing a pending/cancelled workflow that does not match the current domain behavior.
- A transfer is final once created. If a user makes a mistake, correction should come from a follow-up transfer or stock adjustment, not a retroactive cancel on an already-applied movement.
- Reuse the existing `POST /api/v1/inventory/transfers` and `StockTransferForm` surface where possible.

## Acceptance Criteria

1. Given I initiate a transfer from the inventory UI, when I submit valid data, then stock moves immediately between warehouses and the UI confirms success.
2. Given transfer validation fails, when source and destination are the same or stock is insufficient, then the UI shows a clear error and no transfer history row is created.
3. Given transfers have been created, when I open `TransfersPage`, then I see transfer history with product, source warehouse, destination warehouse, quantity, actor, notes, and timestamp.
4. Given I inspect a transfer from the history list, when I open its detail view, then I can see the complete transfer metadata without needing direct database access.
5. Given a transfer completes, when I inspect product stock history, then the related transfer still appears through the existing transfer reason codes in stock adjustment history.

## Tasks / Subtasks

- [x] **Task 1: Keep the existing write path and add read queries** (AC: 1, 2, 3, 4)
  - [x] Reuse `transfer_stock()` and `POST /api/v1/inventory/transfers`.
  - [x] Add `list_transfers(session, tenant_id, ...)` and `get_transfer(session, tenant_id, transfer_id)` to `backend/domains/inventory/services.py`.
  - [x] Join product and warehouse display names for history views.

- [x] **Task 2: Add transfer-history routes** (AC: 3, 4)
  - [x] Add `GET /api/v1/inventory/transfers`.
  - [x] Add `GET /api/v1/inventory/transfers/{transfer_id}`.
  - [x] Support practical filters needed by the page (`product_id`, `warehouse_id`).

- [x] **Task 3: Refine `StockTransferForm`** (AC: 1, 2)
  - [x] Improve the existing `src/domain/inventory/components/StockTransferForm.tsx` rather than replacing it wholesale.
  - [x] Reuse warehouse and product selectors already present in the inventory module.
  - [x] Add better success/error handling and a parent callback so the opening screen can refresh after transfer completion.

- [x] **Task 4: Build transfer-history UX** (AC: 3, 4)
  - [x] Create `src/pages/inventory/TransfersPage.tsx`.
  - [x] Add a transfer list, filters, and a detail drawer or route.
  - [x] Link to the page from inventory navigation and relevant product-detail surfaces.

- [x] **Task 5: Add focused regression tests** (AC: 1, 2, 3, 4, 5)
  - [x] Backend tests for list/detail reads and existing create-path validation behavior.
  - [x] Frontend tests for `StockTransferForm` and `TransfersPage`.

## Dev Notes

### Architecture Compliance

- The source of truth is `backend/common/models/stock_transfer.py` plus the transfer service in `backend/domains/inventory/services.py`.
- Transfers are immediate and tenant-scoped.
- Stock-adjustment history already captures transfer-in and transfer-out reason codes; keep that linkage intact.

### Project Structure Notes

- Backend: `backend/common/models/stock_transfer.py`, `backend/domains/inventory/services.py`, `backend/domains/inventory/routes.py`, `backend/domains/inventory/schemas.py`
- Frontend: `src/domain/inventory/components/StockTransferForm.tsx`, `src/pages/inventory/TransfersPage.tsx`, `src/pages/InventoryPage.tsx`

### What NOT to implement

- Do **not** add `pending`, `in_transit`, or `cancelled` transfer states to the existing immediate-transfer model.
- Do **not** add multi-product batch transfers in this story.
- Do **not** add retroactive cancel for committed transfers.

### Testing Standards

- Include validation-path coverage for same-warehouse and insufficient-stock errors.
- Include a history-view test proving notes and actor metadata are visible to users.

## Dependencies & Related Stories

- **Depends on:** Story 4.6 (Warehouse Support), Story 4.4 (Stock Adjustment)
- **Related to:** Story 4.2 (Stock Detail) because transfer results should be visible in stock history

## References

- `backend/common/models/stock_transfer.py`
- `backend/domains/inventory/services.py`
- `backend/domains/inventory/routes.py`
- `src/domain/inventory/components/StockTransferForm.tsx`
- `src/pages/InventoryPage.tsx`

## Dev Agent Record

### Completion Notes

- Added transfer-history read schemas, `list_transfers`, and `get_transfer` on top of the existing immediate transfer write path.
- Added `GET /api/v1/inventory/transfers` and `GET /api/v1/inventory/transfers/{transfer_id}` with product and warehouse display names for the history UI.
- Fixed transfer actor attribution so new history rows use the authenticated actor instead of the placeholder `system` value.
- Refined `StockTransferForm` with shared selectors, success/error messaging, integer-only quantity validation, and a parent success callback.
- Added `TransfersPage` with product and warehouse filters, history table, detail sheet, and route wiring from inventory and product-detail entry points.
- Improved transfer error parsing so insufficient-stock responses and validation failures render clear operator-facing messages.
- Kept transfer visibility aligned with existing stock adjustment history through the existing `transfer_in` and `transfer_out` reason codes.

### Validation

- Backend: `/Users/changtom/Downloads/UltrERP/backend/.venv/bin/python -m pytest tests/api/test_transfers.py tests/domains/inventory/test_transfer_service.py -q`
- Frontend: `pnpm vitest run src/tests/inventory/StockTransferForm.test.tsx src/pages/inventory/TransfersPage.test.tsx src/pages/inventory/ProductDetailPage.test.tsx src/pages/InventoryPage.test.tsx`
- Diagnostics: no new editor errors in touched Story 4.19 backend/frontend files; existing unrelated route typing issues remain elsewhere in `backend/domains/inventory/routes.py`.

### Files Changed

- `backend/domains/inventory/schemas.py`
- `backend/domains/inventory/services.py`
- `backend/domains/inventory/routes.py`
- `backend/tests/api/test_transfers.py`
- `src/domain/inventory/types.ts`
- `src/lib/api/inventory.ts`
- `src/domain/inventory/components/StockTransferForm.tsx`
- `src/pages/inventory/TransfersPage.tsx`
- `src/pages/inventory/TransfersPage.test.tsx`
- `src/tests/inventory/StockTransferForm.test.tsx`
- `src/pages/inventory/ProductDetailPage.tsx`
- `src/pages/inventory/ProductDetailPage.test.tsx`
- `src/domain/inventory/components/ProductDetailDrawer.tsx`
- `src/pages/InventoryPage.tsx`
- `src/pages/InventoryPage.test.tsx`
- `src/lib/routes.ts`
- `src/lib/navigation.tsx`
- `src/App.tsx`
- `public/locales/en/common.json`
- `public/locales/zh-Hant/common.json`
