# Story 4.17: Physical Count / Inventory Audit

**Status:** done

**Story ID:** 4.17

**Epic:** Epic 4 - Inventory Operations

---

## Story

As a warehouse manager,
I want controlled physical count sessions with approval-based reconciliation,
so that inventory adjustments from count discrepancies are deliberate and auditable.

---

## Best-Practice Update

- Snapshot the system quantity onto each count line when the session is created. Physical count review should compare against a stable baseline, not a moving stock number.
- Approval must be idempotent. A submitted session can be approved once, and approval should fail loudly if live stock changed after the snapshot in a way that makes the count stale.
- Reuse the stock-adjustment infrastructure for final reconciliation rather than inventing a second adjustment mechanism.

## Acceptance Criteria

1. Given I start a count for one warehouse, when the session is created, then the session enters `in_progress` and pre-populates count lines with `system_qty_snapshot` for that warehouse's products.
2. Given a count session is in progress, when I enter counted quantities and notes, then the line data persists without changing live stock.
3. Given I submit a count session, when submission succeeds, then the session becomes `submitted`, line editing is locked, and variance totals are available for review.
4. Given a submitted session is approved, when the live stock still matches the snapshot baseline, then stock adjustments are created for non-zero variances with reason code `physical_count` and the session becomes `approved`.
5. Given live stock changed after the count snapshot, when approval is attempted, then the API returns HTTP 409 and the user must review or recount rather than applying stale adjustments silently.

## Tasks / Subtasks

- [x] **Task 1: Add the physical-count models and migration** (AC: 1, 2, 3, 4, 5)
  - [x] Add `PhysicalCountSession` and `PhysicalCountLine` under `backend/common/models/`.
  - [x] Include `system_qty_snapshot`, `counted_qty`, `variance_qty`, `status`, actor/timestamp fields, and one-warehouse-per-session design.
  - [x] Add an Alembic migration and guard against multiple open sessions for the same warehouse if business rules require exclusivity.

- [x] **Task 2: Add schemas and service lifecycle** (AC: 1, 2, 3, 4, 5)
  - [x] Add count-session request/response models to `backend/domains/inventory/schemas.py`.
  - [x] Add service methods for create, list, detail, update line, submit, and approve.
  - [x] On approval, lock the affected `inventory_stock` rows and compare live quantity to `system_qty_snapshot` before creating adjustments.
  - [x] Make approval idempotent so the same session cannot create duplicate adjustments on retry.

- [x] **Task 3: Add the routes** (AC: 1, 2, 3, 4, 5)
  - [x] Add `POST /api/v1/inventory/count-sessions`
  - [x] Add `GET /api/v1/inventory/count-sessions`
  - [x] Add `GET /api/v1/inventory/count-sessions/{session_id}`
  - [x] Add `PATCH /api/v1/inventory/count-sessions/{session_id}/lines/{line_id}`
  - [x] Add `POST /api/v1/inventory/count-sessions/{session_id}/submit`
  - [x] Add `POST /api/v1/inventory/count-sessions/{session_id}/approve`

- [x] **Task 4: Build the count-session UI** (AC: 1, 2, 3, 4, 5)
  - [x] Create `src/pages/inventory/CountSessionsPage.tsx` for list/start flow.
  - [x] Create `src/pages/inventory/CountSessionDetailPage.tsx` for line entry, variance review, submit, and approve actions.
  - [x] Surface stale-session approval conflicts clearly in the UI.

- [x] **Task 5: Reuse stock-adjustment audit behavior** (AC: 4)
  - [x] Reuse `StockAdjustment` and audit-log patterns from Story 4.4.
  - [x] Ensure `physical_count` is present as a valid system reason code.

- [x] **Task 6: Add focused regression tests** (AC: 1, 2, 3, 4, 5)
  - [x] Backend tests for session creation, line updates, submit, approval, double-approval retry, and stale-snapshot 409 behavior.
  - [x] Frontend tests for count entry and approval conflict messaging.

## Dev Notes

### Architecture Compliance

- Physical count approval is the only point that mutates live stock in this story.
- Count sessions are warehouse-scoped and tenant-scoped.
- Approval should reuse the same stock-adjustment and audit trail behavior already established in the inventory domain.

### Project Structure Notes

- Backend: `backend/common/models/physical_count_session.py`, `backend/common/models/physical_count_line.py`, `backend/domains/inventory/services.py`, `backend/domains/inventory/routes.py`, `backend/domains/inventory/schemas.py`
- Frontend: `src/pages/inventory/CountSessionsPage.tsx`, `src/pages/inventory/CountSessionDetailPage.tsx`

### What NOT to implement

- Do **not** auto-approve counts on submit.
- Do **not** support multi-warehouse sessions or partial line-level approvals in v1.
- Do **not** bypass stock-adjustment history when reconciling counts.

### Testing Standards

- Include an approval-conflict regression test where stock changed after snapshot creation.
- Include an idempotency test proving approval cannot double-apply adjustments.

## Dependencies & Related Stories

- **Depends on:** Story 4.4 (Stock Adjustment), Story 4.6 (Warehouse Support)
- **Related to:** Story 4.2 (View Stock Level) because count review depends on warehouse stock context

## References

- `backend/common/models/inventory_stock.py`
- `backend/common/models/stock_adjustment.py`
- `backend/domains/inventory/services.py`
- `backend/domains/inventory/routes.py`

---

## Dev Agent Record

**Status:** done
**Last Updated:** 2026-04-18

### Completion Notes List

- Added warehouse-scoped physical-count session and line models, a migration for the new tables and reason code, and inventory service flows for create, update, submit, and approval with snapshot-staleness protection and idempotent reconciliation.
- Reused the existing stock-adjustment and audit-log infrastructure so approval applies only non-zero variances through `PHYSICAL_COUNT` adjustments instead of introducing a second stock mutation path.
- Shipped count-session list and detail pages with route wiring, shell-context labels, localized copy, and explicit stale-approval error handling in the UI.

### Validation

- `cd backend && . .venv/bin/activate && pytest tests/common/test_model_registry.py tests/domains/inventory/test_stock_adjustment.py`
- `cd backend && . .venv/bin/activate && pytest tests/domains/inventory/test_physical_count_sessions.py`
- `pnpm vitest run src/pages/inventory/CountSessionsPage.test.tsx src/pages/inventory/CountSessionDetailPage.test.tsx`
- VS Code diagnostics: no new errors in the touched backend/frontend files for the 4.17 slice

### File List

- `backend/common/models/physical_count_session.py`
- `backend/common/models/physical_count_line.py`
- `backend/common/models/stock_adjustment.py`
- `backend/common/models/__init__.py`
- `backend/common/model_registry.py`
- `backend/domains/inventory/schemas.py`
- `backend/domains/inventory/services.py`
- `backend/domains/inventory/routes.py`
- `backend/tests/common/test_model_registry.py`
- `backend/tests/domains/inventory/test_stock_adjustment.py`
- `backend/tests/domains/inventory/test_physical_count_sessions.py`
- `migrations/versions/e1b2c3d4f5a6_add_physical_count_tables.py`
- `src/domain/inventory/types.ts`
- `src/lib/api/inventory.ts`
- `src/pages/InventoryPage.tsx`
- `src/pages/inventory/CountSessionsPage.tsx`
- `src/pages/inventory/CountSessionDetailPage.tsx`
- `src/pages/inventory/CountSessionsPage.test.tsx`
- `src/pages/inventory/CountSessionDetailPage.test.tsx`
- `src/lib/routes.ts`
- `src/lib/navigation.tsx`
- `src/App.tsx`
- `public/locales/en/common.json`
- `public/locales/zh-Hant/common.json`
