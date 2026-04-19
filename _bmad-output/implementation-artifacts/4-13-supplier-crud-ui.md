# Story 4.13: Supplier CRUD UI

**Status:** done

**Story ID:** 4.13

**Epic:** Epic 4 - Inventory Operations

---

## Story

As a procurement staff member,
I want to manage supplier master data through the inventory UI,
so that supplier selection, lead-time planning, and order creation use an up-to-date supplier catalog.

---

## Best-Practice Update

- The `Supplier` model already exists in the repo, and basic supplier listing already exists. This story should complete the write path and management UI instead of conditionally re-creating the data model.
- Use soft lifecycle management through `is_active`; inactive suppliers disappear from default selectors but remain valid for historical orders.
- Reuse one `SupplierForm` across create/edit flows so list and detail screens do not diverge in validation behavior.

## Acceptance Criteria

1. Given suppliers exist for my tenant, when I open `SuppliersPage`, then I see a searchable list with supplier name, primary contact info, lead time, and active status.
2. Given I create or edit a supplier, when I submit valid data, then the supplier is persisted and returned through the same tenant-scoped API surface.
3. Given I open a supplier detail view, when I inspect a supplier, then I can view and edit full supplier details including address and default lead time.
4. Given a supplier is deactivated, when I create a new supplier order or use a supplier selector, then that supplier is hidden by default while existing supplier orders remain intact.
5. Given supplier lookup is needed in forms, when I use `SupplierCombobox`, then it shows active suppliers by default and supports search by name.

## Tasks / Subtasks

- [x] **Task 1: Complete backend supplier CRUD around the existing model** (AC: 1, 2, 3, 4)
  - [x] Reuse `backend/common/models/supplier.py`; do not create a second supplier entity.
  - [x] Add `create_supplier`, `get_supplier`, `update_supplier`, and `set_supplier_status` to `backend/domains/inventory/services.py`.
  - [x] Extend `list_suppliers()` to support `q`, `active_only`, `limit`, and `offset`.
  - [x] Validate `default_lead_time_days >= 0` and keep all queries tenant-scoped.

- [x] **Task 2: Add request/response schemas and routes** (AC: 1, 2, 3, 4)
  - [x] Add `SupplierCreate`, `SupplierUpdate`, and any list/detail response models missing from `backend/domains/inventory/schemas.py`.
  - [x] Add `POST /api/v1/inventory/suppliers`
  - [x] Add `GET /api/v1/inventory/suppliers`
  - [x] Add `GET /api/v1/inventory/suppliers/{supplier_id}`
  - [x] Add `PUT /api/v1/inventory/suppliers/{supplier_id}`
  - [x] Add `PATCH /api/v1/inventory/suppliers/{supplier_id}/status`

- [x] **Task 3: Add frontend supplier types and API helpers** (AC: 1, 2, 3, 5)
  - [x] Extend `src/domain/inventory/types.ts` with create/update payloads and list-query options.
  - [x] Extend `src/lib/api/inventory.ts` with supplier CRUD helpers.
  - [x] Add a supplier-management hook or extend the existing supplier hooks so list/detail pages share request logic.

- [x] **Task 4: Build shared supplier form primitives** (AC: 2, 3)
  - [x] Create `src/domain/inventory/components/SupplierForm.tsx`.
  - [x] Reuse the same form for create and edit.
  - [x] Include fields for name, email, phone, address, and default lead time days.

- [x] **Task 5: Build `SuppliersPage` and `SupplierDetailPage`** (AC: 1, 3, 4)
  - [x] Create `src/pages/inventory/SuppliersPage.tsx` for list/search/create.
  - [x] Create `src/pages/inventory/SupplierDetailPage.tsx` for detail/edit/status actions.
  - [x] Add inventory navigation entry points for supplier management.

- [x] **Task 6: Build `SupplierCombobox`** (AC: 5)
  - [x] Create `src/domain/inventory/components/SupplierCombobox.tsx`.
  - [x] Default to active suppliers only, with an opt-in inactive mode if an admin workflow needs it later.
  - [x] Reuse it in `SupplierOrderForm.tsx` and future product-supplier association flows.

- [x] **Task 7: Add focused regression tests** (AC: 1, 2, 3, 4, 5)
  - [x] Backend service/API tests for create, update, search, deactivate/reactivate, and not-found behavior.
  - [x] Frontend tests for `SupplierForm`, `SuppliersPage`, `SupplierDetailPage`, and `SupplierCombobox`.

## Dev Notes

### Architecture Compliance

- The supplier master already lives at `backend/common/models/supplier.py`.
- Historical supplier orders must remain readable even when a supplier is deactivated.
- Supplier CRUD belongs in the inventory domain; do not duplicate supplier management under orders just to support PO entry.

### Project Structure Notes

- Backend: `backend/common/models/supplier.py`, `backend/domains/inventory/services.py`, `backend/domains/inventory/routes.py`, `backend/domains/inventory/schemas.py`
- Frontend: `src/pages/inventory/SuppliersPage.tsx`, `src/pages/inventory/SupplierDetailPage.tsx`, `src/domain/inventory/components/SupplierForm.tsx`, `src/domain/inventory/components/SupplierCombobox.tsx`
- Existing touchpoints to extend: `src/domain/inventory/components/SupplierOrderForm.tsx`, `src/lib/api/inventory.ts`

### What NOT to implement

- Do **not** add product-supplier association management here; that belongs to Story 4.21.
- Do **not** add supplier scoring, SLA analytics, or performance dashboards.
- Do **not** hard-delete suppliers that may already be referenced by supplier orders.

### Testing Standards

- Cover supplier list pagination/search and inactive filtering.
- Cover supplier-selector behavior because downstream PO flows depend on it.

## Dependencies & Related Stories

- **Depends on:** Story 4.5 (Supplier Orders) for existing supplier usage patterns
- **Related to:** Story 4.14 (Reorder Suggestions) and Story 4.21 (Default Supplier per Product)

## References

- `backend/common/models/supplier.py`
- `backend/domains/inventory/services.py`
- `backend/domains/inventory/routes.py`
- `src/domain/inventory/components/SupplierOrderForm.tsx`
- `src/lib/api/inventory.ts`

---

## Dev Agent Record

**Status:** done
**Last Updated:** 2026-04-18

### Completion Notes List

- Confirmed the initial supplier UI commit only covered the frontend surfaces, then completed the missing tenant-scoped backend supplier CRUD, list search/pagination, and status-toggle routes so the shipped UI has a real API path behind it.
- Added the missing supplier client/types layer used by the new management pages and detail hook, keeping validation errors aligned to the existing inventory field-error contract.
- Wired `SupplierCombobox` into `SupplierOrderForm` so supplier selection now defaults to active suppliers and supports search-by-name in the downstream PO flow.
- Closed the story with a focused review pass and fixed the local accessibility gap in `ProductCombobox` so labeled product selection remains testable from the supplier-order surface.

### Validation

- `cd backend && . .venv/bin/activate && pytest -q tests/domains/inventory/test_suppliers.py tests/api/test_suppliers.py tests/domains/inventory/test_supplier_orders.py::test_list_suppliers tests/domains/inventory/test_supplier_orders.py::test_list_suppliers_empty`
- `pnpm exec vitest run src/tests/inventory/SupplierForm.test.tsx src/tests/inventory/SupplierCombobox.test.tsx src/pages/inventory/SuppliersPage.test.tsx src/pages/inventory/SupplierDetailPage.test.tsx src/domain/inventory/components/SupplierOrderForm.test.tsx`
- VS Code diagnostics: supplier-specific errors cleared in the touched frontend files and new supplier backend slices; unrelated pre-existing inventory typing diagnostics remain elsewhere in `backend/domains/inventory/services.py` and `backend/domains/inventory/routes.py`

### File List

- `backend/domains/inventory/schemas.py`
- `backend/domains/inventory/services.py`
- `backend/domains/inventory/routes.py`
- `backend/tests/api/test_suppliers.py`
- `backend/tests/domains/inventory/test_suppliers.py`
- `src/domain/inventory/types.ts`
- `src/lib/api/inventory.ts`
- `src/domain/inventory/hooks/useSuppliers.ts`
- `src/domain/inventory/components/SupplierForm.tsx`
- `src/domain/inventory/components/SupplierCombobox.tsx`
- `src/domain/inventory/components/SupplierOrderForm.tsx`
- `src/domain/inventory/components/SupplierOrderForm.test.tsx`
- `src/components/products/ProductCombobox.tsx`
- `src/pages/inventory/SuppliersPage.tsx`
- `src/pages/inventory/SuppliersPage.test.tsx`
- `src/pages/inventory/SupplierDetailPage.tsx`
- `src/pages/inventory/SupplierDetailPage.test.tsx`
- `src/tests/inventory/SupplierForm.test.tsx`
- `src/tests/inventory/SupplierCombobox.test.tsx`
