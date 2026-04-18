# Story 4.13: Supplier CRUD UI

**Status:** backlog

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

- [ ] **Task 1: Complete backend supplier CRUD around the existing model** (AC: 1, 2, 3, 4)
  - [ ] Reuse `backend/common/models/supplier.py`; do not create a second supplier entity.
  - [ ] Add `create_supplier`, `get_supplier`, `update_supplier`, and `set_supplier_status` to `backend/domains/inventory/services.py`.
  - [ ] Extend `list_suppliers()` to support `q`, `active_only`, `limit`, and `offset`.
  - [ ] Validate `default_lead_time_days >= 0` and keep all queries tenant-scoped.

- [ ] **Task 2: Add request/response schemas and routes** (AC: 1, 2, 3, 4)
  - [ ] Add `SupplierCreate`, `SupplierUpdate`, and any list/detail response models missing from `backend/domains/inventory/schemas.py`.
  - [ ] Add `POST /api/v1/inventory/suppliers`
  - [ ] Add `GET /api/v1/inventory/suppliers`
  - [ ] Add `GET /api/v1/inventory/suppliers/{supplier_id}`
  - [ ] Add `PUT /api/v1/inventory/suppliers/{supplier_id}`
  - [ ] Add `PATCH /api/v1/inventory/suppliers/{supplier_id}/status`

- [ ] **Task 3: Add frontend supplier types and API helpers** (AC: 1, 2, 3, 5)
  - [ ] Extend `src/domain/inventory/types.ts` with create/update payloads and list-query options.
  - [ ] Extend `src/lib/api/inventory.ts` with supplier CRUD helpers.
  - [ ] Add a supplier-management hook or extend the existing supplier hooks so list/detail pages share request logic.

- [ ] **Task 4: Build shared supplier form primitives** (AC: 2, 3)
  - [ ] Create `src/domain/inventory/components/SupplierForm.tsx`.
  - [ ] Reuse the same form for create and edit.
  - [ ] Include fields for name, email, phone, address, and default lead time days.

- [ ] **Task 5: Build `SuppliersPage` and `SupplierDetailPage`** (AC: 1, 3, 4)
  - [ ] Create `src/pages/inventory/SuppliersPage.tsx` for list/search/create.
  - [ ] Create `src/pages/inventory/SupplierDetailPage.tsx` for detail/edit/status actions.
  - [ ] Add inventory navigation entry points for supplier management.

- [ ] **Task 6: Build `SupplierCombobox`** (AC: 5)
  - [ ] Create `src/domain/inventory/components/SupplierCombobox.tsx`.
  - [ ] Default to active suppliers only, with an opt-in inactive mode if an admin workflow needs it later.
  - [ ] Reuse it in `SupplierOrderForm.tsx` and future product-supplier association flows.

- [ ] **Task 7: Add focused regression tests** (AC: 1, 2, 3, 4, 5)
  - [ ] Backend service/API tests for create, update, search, deactivate/reactivate, and not-found behavior.
  - [ ] Frontend tests for `SupplierForm`, `SuppliersPage`, `SupplierDetailPage`, and `SupplierCombobox`.

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
