# Story 4.15: Below-Reorder-Point Reporting

**Status:** backlog

**Story ID:** 4.15

**Epic:** Epic 4 - Inventory Operations

---

## Story

As a warehouse manager,
I want a previewable below-reorder report with CSV export,
so that I can share actionable low-stock data with procurement and management.

---

## Best-Practice Update

- Use one shared query service for both the on-screen preview and the CSV export. The export route should be a different representation of the same report, not a second implementation.
- Keep CSV output Excel-friendly with a UTF-8 BOM and a stable column order.
- Prefer a lightweight inventory reports page over one-off export buttons scattered across unrelated screens.

## Acceptance Criteria

1. Given inventory stock exists, when I open the below-reorder report, then I see only rows where warehouse stock is below that warehouse's reorder point.
2. Given I filter by warehouse, when I preview or export the report, then both the table and CSV use the same filtered dataset.
3. Given I export the report, when the CSV is downloaded, then it includes `Product Code`, `Product Name`, `Category`, `Warehouse`, `Current Stock`, `Reorder Point`, `Shortage Qty`, `On Order Qty`, `In Transit Qty`, and `Default Supplier`.
4. Given the CSV contains Traditional Chinese text, when I open it in Excel, then it renders correctly because the file is encoded as UTF-8 with BOM.
5. Given no default supplier is known for a row, when I export or preview the report, then the supplier column is blank rather than guessed.

## Tasks / Subtasks

- [ ] **Task 1: Add a shared below-reorder report query** (AC: 1, 2, 3, 5)
  - [ ] Add `list_below_reorder_products(session, tenant_id, warehouse_id=None)` to `backend/domains/inventory/services.py`.
  - [ ] Reuse the same warehouse-aware low-stock logic used by inventory detail and alert views.
  - [ ] Join product, warehouse, and stock-setting data and enrich with default-supplier display when available.

- [ ] **Task 2: Add JSON and CSV routes over the shared query** (AC: 1, 2, 3, 4, 5)
  - [ ] Add `GET /api/v1/inventory/reports/below-reorder` for preview JSON.
  - [ ] Add `GET /api/v1/inventory/reports/below-reorder/export` for CSV download.
  - [ ] Keep query params aligned across both endpoints.
  - [ ] Prefix the CSV body with `\ufeff` and return a download-friendly filename.

- [ ] **Task 3: Add frontend types and API helpers** (AC: 1, 2, 3)
  - [ ] Add below-reorder report types to `src/domain/inventory/types.ts`.
  - [ ] Add preview/export helpers to `src/lib/api/inventory.ts`.

- [ ] **Task 4: Build the report page** (AC: 1, 2, 3, 4, 5)
  - [ ] Create `src/pages/inventory/BelowReorderReportPage.tsx`.
  - [ ] Show warehouse filter, preview table, shortage summary, and `Export CSV` action.
  - [ ] Add an inventory reports navigation entry.

- [ ] **Task 5: Add focused regression tests** (AC: 1, 2, 3, 4, 5)
  - [ ] Backend tests for the filtered query, CSV headers, BOM prefix, and blank-supplier behavior.
  - [ ] Frontend tests for filter state, preview rendering, and export action wiring.

## Dev Notes

### Architecture Compliance

- Treat this as a reporting/read-model story; do not change stock state.
- Keep the report warehouse-aware because reorder points already live per warehouse in `inventory_stock`.
- Reuse supplier-resolution helpers rather than duplicating supplier lookup rules in the export code.

### Project Structure Notes

- Backend: `backend/domains/inventory/services.py`, `backend/domains/inventory/routes.py`, `backend/domains/inventory/schemas.py`
- Frontend: `src/pages/inventory/BelowReorderReportPage.tsx`, `src/lib/api/inventory.ts`, `src/domain/inventory/types.ts`

### What NOT to implement

- Do **not** add scheduled emails, PDFs, or archival snapshots in this story.
- Do **not** create a second low-stock query path separate from reorder alerts/report preview.

### Testing Standards

- Verify that preview and CSV export use the same filtered dataset.
- Verify the UTF-8 BOM explicitly because that is the user-visible compatibility requirement.

## Dependencies & Related Stories

- **Depends on:** Story 4.2 (View Stock Level), Story 4.3 (Reorder Alerts), Story 4.6 (Multiple Warehouse Support)
- **Related to:** Story 4.14 (Reorder Suggestions) and Story 4.21 (Default Supplier per Product)

## References

- `backend/common/models/inventory_stock.py`
- `backend/domains/inventory/services.py`
- `backend/domains/inventory/routes.py`
- `src/domain/inventory/context/WarehouseContext.tsx`
