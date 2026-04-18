# Story 4.19: Stock Transfer UI

**Status:** backlog

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

- [ ] **Task 1: Keep the existing write path and add read queries** (AC: 1, 2, 3, 4)
  - [ ] Reuse `transfer_stock()` and `POST /api/v1/inventory/transfers`.
  - [ ] Add `list_transfers(session, tenant_id, ...)` and `get_transfer(session, tenant_id, transfer_id)` to `backend/domains/inventory/services.py`.
  - [ ] Join product and warehouse display names for history views.

- [ ] **Task 2: Add transfer-history routes** (AC: 3, 4)
  - [ ] Add `GET /api/v1/inventory/transfers`.
  - [ ] Add `GET /api/v1/inventory/transfers/{transfer_id}`.
  - [ ] Support practical filters such as product, warehouse, and date range if they are needed by the page.

- [ ] **Task 3: Refine `StockTransferForm`** (AC: 1, 2)
  - [ ] Improve the existing `src/domain/inventory/components/StockTransferForm.tsx` rather than replacing it wholesale.
  - [ ] Reuse warehouse and product selectors already present in the inventory module.
  - [ ] Add better success/error handling and a parent callback so the opening screen can refresh after transfer completion.

- [ ] **Task 4: Build transfer-history UX** (AC: 3, 4)
  - [ ] Create `src/pages/inventory/TransfersPage.tsx`.
  - [ ] Add a transfer list, filters, and a detail drawer or route.
  - [ ] Link to the page from inventory navigation and relevant product-detail surfaces.

- [ ] **Task 5: Add focused regression tests** (AC: 1, 2, 3, 4, 5)
  - [ ] Backend tests for list/detail reads and existing create-path validation behavior.
  - [ ] Frontend tests for `StockTransferForm` and `TransfersPage`.

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
