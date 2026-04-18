# Story 4.20: Reorder Point Bulk Admin UI

**Status:** backlog

**Story ID:** 4.20

**Epic:** Epic 4 - Inventory Operations

---

## Story

As a warehouse manager,
I want to review computed reorder suggestions alongside current settings and apply overrides safely,
so that reorder points stay accurate without editing every stock row manually.

---

## Best-Practice Update

- Build on the reorder-point admin primitives that already exist in the repo: `POST /api/v1/inventory/reorder-points/compute`, `PUT /api/v1/inventory/reorder-points/apply`, `PATCH /api/v1/inventory/stocks/{stock_id}`, and the existing `ReorderPointAdmin` component.
- Keep computed-versus-manual comparison grounded in the current preview: compare `current_reorder_point` to `computed_reorder_point` and expose the delta. Do not add a new persistence field unless a later requirement explicitly needs durable source provenance.
- Reuse the existing settings editor for manual overrides where possible instead of creating a second stock-settings write flow.

## Acceptance Criteria

1. Given I run reorder-point preview, when results load, then I see `current_reorder_point`, `computed_reorder_point`, difference, and the main demand inputs that produced the suggestion.
2. Given I select multiple preview rows, when I apply suggestions in bulk, then the existing apply endpoint updates only the selected rows and reports updated/skipped counts.
3. Given I want to override one row manually, when I edit that stock setting, then the new current reorder point is saved through the stock-settings write path and the UI refreshes to show the new comparison.
4. Given I review the preview output, when a row was skipped or has low-confidence demand data, then the UI shows the reason instead of hiding the row.
5. Given I am working inside inventory admin, when I move between preview and settings actions, then warehouse context is preserved.

## Tasks / Subtasks

- [ ] **Task 1: Align the story to existing backend contracts** (AC: 1, 2, 3, 4)
  - [ ] Reuse `compute_reorder_points_preview()` and `apply_reorder_points()` in `backend/domains/inventory/reorder_point.py`.
  - [ ] Reuse `PATCH /api/v1/inventory/stocks/{stock_id}` for manual overrides instead of inventing a separate bulk-update endpoint for single-row edits.
  - [ ] Extend preview rows only if additional display data is truly missing.

- [ ] **Task 2: Mature the existing admin UI** (AC: 1, 2, 4, 5)
  - [ ] Extend `src/domain/inventory/components/ReorderPointAdmin.tsx` rather than creating a second reorder admin screen.
  - [ ] Make the delta between current and computed values obvious.
  - [ ] Preserve warehouse filter context while moving between preview results and manual settings edits.

- [ ] **Task 3: Tighten manual override flow** (AC: 3, 5)
  - [ ] Reuse the existing settings surface for row-level edits where possible.
  - [ ] Refresh preview data after a manual override so the comparison remains trustworthy.

- [ ] **Task 4: Add focused regression tests** (AC: 1, 2, 3, 4, 5)
  - [ ] Backend tests for apply counts and manual stock-setting patch behavior.
  - [ ] Frontend tests for preview rendering, row selection, skipped-row visibility, and manual-override refresh behavior.

## Dev Notes

### Architecture Compliance

- The current inventory domain already owns reorder-point compute/apply behavior.
- Warehouse context should remain the primary filter because reorder points are warehouse-specific.
- Comparison data is advisory; the actual persisted value is `current_reorder_point`.

### Project Structure Notes

- Backend: `backend/domains/inventory/reorder_point.py`, `backend/domains/inventory/routes.py`, `backend/domains/inventory/services.py`
- Frontend: `src/domain/inventory/components/ReorderPointAdmin.tsx`, `src/domain/inventory/hooks/useReorderPointAdmin.ts`, `src/domain/inventory/components/SettingsTab.tsx`

### What NOT to implement

- Do **not** add a second reorder-point review endpoint if the existing preview payload is sufficient.
- Do **not** add background scheduling or auto-apply behavior in this story.
- Do **not** add a durable `reorder_point_source` column unless product planning explicitly asks for persisted provenance beyond current-vs-computed comparison.

### Testing Standards

- Include a regression test for skipped rows and low-confidence messaging.
- Include a manual-override test proving the UI refreshes to the new current value.

## Dependencies & Related Stories

- **Depends on:** Story 4.7 (Reorder Point Calculation), Story 4.6 (Warehouse Support)
- **Related to:** Story 4.14 (Reorder Suggestions)

## References

- `backend/domains/inventory/reorder_point.py`
- `backend/domains/inventory/routes.py`
- `backend/domains/inventory/services.py`
- `src/domain/inventory/components/ReorderPointAdmin.tsx`
- `src/domain/inventory/hooks/useReorderPointAdmin.ts`
