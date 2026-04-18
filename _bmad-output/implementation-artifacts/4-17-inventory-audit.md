# Story 4.17: Physical Count / Inventory Audit

**Status:** backlog

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

- [ ] **Task 1: Add the physical-count models and migration** (AC: 1, 2, 3, 4, 5)
  - [ ] Add `PhysicalCountSession` and `PhysicalCountLine` under `backend/common/models/`.
  - [ ] Include `system_qty_snapshot`, `counted_qty`, `variance_qty`, `status`, actor/timestamp fields, and one-warehouse-per-session design.
  - [ ] Add an Alembic migration and guard against multiple open sessions for the same warehouse if business rules require exclusivity.

- [ ] **Task 2: Add schemas and service lifecycle** (AC: 1, 2, 3, 4, 5)
  - [ ] Add count-session request/response models to `backend/domains/inventory/schemas.py`.
  - [ ] Add service methods for create, list, detail, update line, submit, and approve.
  - [ ] On approval, lock the affected `inventory_stock` rows and compare live quantity to `system_qty_snapshot` before creating adjustments.
  - [ ] Make approval idempotent so the same session cannot create duplicate adjustments on retry.

- [ ] **Task 3: Add the routes** (AC: 1, 2, 3, 4, 5)
  - [ ] Add `POST /api/v1/inventory/count-sessions`
  - [ ] Add `GET /api/v1/inventory/count-sessions`
  - [ ] Add `GET /api/v1/inventory/count-sessions/{session_id}`
  - [ ] Add `PATCH /api/v1/inventory/count-sessions/{session_id}/lines/{line_id}`
  - [ ] Add `POST /api/v1/inventory/count-sessions/{session_id}/submit`
  - [ ] Add `POST /api/v1/inventory/count-sessions/{session_id}/approve`

- [ ] **Task 4: Build the count-session UI** (AC: 1, 2, 3, 4, 5)
  - [ ] Create `src/pages/inventory/CountSessionsPage.tsx` for list/start flow.
  - [ ] Create `src/pages/inventory/CountSessionDetailPage.tsx` for line entry, variance review, submit, and approve actions.
  - [ ] Surface stale-session approval conflicts clearly in the UI.

- [ ] **Task 5: Reuse stock-adjustment audit behavior** (AC: 4)
  - [ ] Reuse `StockAdjustment` and audit-log patterns from Story 4.4.
  - [ ] Ensure `physical_count` is present as a valid system reason code.

- [ ] **Task 6: Add focused regression tests** (AC: 1, 2, 3, 4, 5)
  - [ ] Backend tests for session creation, line updates, submit, approval, double-approval retry, and stale-snapshot 409 behavior.
  - [ ] Frontend tests for count entry and approval conflict messaging.

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
