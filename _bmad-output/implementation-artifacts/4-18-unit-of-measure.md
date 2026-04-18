# Story 4.18: Unit of Measure Management

**Status:** backlog

**Story ID:** 4.18

**Epic:** Epic 4 - Inventory Operations

---

## Story

As a warehouse staff member,
I want a shared unit-of-measure master list,
so that product units are chosen consistently across the inventory module.

---

## Best-Practice Update

- Narrow this story to UOM master data, default seeding, and product-form selection. Full unit-conversion logic is a separate problem and should not be smuggled into this CRUD story.
- Keep `Product.unit` as a string for v1, but standardize it around UOM `code` values from the master list.
- Use soft deactivation for units that were already used by products so historical product rows keep readable unit values.

## Acceptance Criteria

1. Given I manage units of measure, when I create, edit, list, or deactivate a unit, then the UOM master data persists per tenant with unique unit codes.
2. Given a tenant has no UOM data yet, when units are first seeded or first requested, then a default set is created idempotently: `pcs`, `kg`, `g`, `box`, `carton`, `pallet`, `liter`, `ml`, `meter`, `cm`.
3. Given I create or edit a product, when I open the unit field, then I use `UnitCombobox` and the stored value is the selected UOM code.
4. Given a unit is deactivated, when I open product forms, then inactive units are hidden from normal selection while existing products keep their stored unit code.
5. Given a product already has a unit, when I view inventory detail or supplier-order lines, then the unit display remains consistent with the stored code.

## Tasks / Subtasks

- [ ] **Task 1: Add the UOM model and migration** (AC: 1, 2, 4)
  - [ ] Create `backend/common/models/unit_of_measure.py` with `id`, `tenant_id`, `code`, `name`, `decimal_places`, `is_active`, `created_at`, and `updated_at`.
  - [ ] Add an Alembic migration with a tenant-scoped unique constraint on `code`.

- [ ] **Task 2: Add schemas and service methods** (AC: 1, 2, 4)
  - [ ] Add `UnitOfMeasureCreate`, `UnitOfMeasureUpdate`, `UnitOfMeasureResponse`, and `UnitOfMeasureListResponse` to `backend/domains/inventory/schemas.py`.
  - [ ] Add `create_unit`, `list_units`, `get_unit`, `update_unit`, `set_unit_status`, and `seed_default_units` to `backend/domains/inventory/services.py`.
  - [ ] Make `seed_default_units` safe to call multiple times.

- [ ] **Task 3: Add UOM routes** (AC: 1, 2)
  - [ ] Add `POST /api/v1/inventory/units`
  - [ ] Add `GET /api/v1/inventory/units`
  - [ ] Add `GET /api/v1/inventory/units/{unit_id}`
  - [ ] Add `PUT /api/v1/inventory/units/{unit_id}`
  - [ ] Add `PATCH /api/v1/inventory/units/{unit_id}/status`

- [ ] **Task 4: Add frontend types, API helpers, and `UnitCombobox`** (AC: 3, 4, 5)
  - [ ] Add UOM types to `src/domain/inventory/types.ts`.
  - [ ] Add UOM API helpers to `src/lib/api/inventory.ts`.
  - [ ] Create `src/domain/inventory/components/UnitCombobox.tsx`.

- [ ] **Task 5: Wire UOM into product forms and management UI** (AC: 2, 3, 4, 5)
  - [ ] Replace free-text unit entry in `CreateProductForm.tsx` and `EditProductForm.tsx`.
  - [ ] Add `src/pages/inventory/UnitsPage.tsx` for CRUD management.
  - [ ] Keep existing product rows readable even if a unit later becomes inactive.

- [ ] **Task 6: Add focused regression tests** (AC: 1, 2, 3, 4, 5)
  - [ ] Backend tests for CRUD, seed idempotency, and inactive filtering.
  - [ ] Frontend tests for `UnitCombobox` and the units page.

## Dev Notes

### Architecture Compliance

- `Product.unit` remains a string field in `backend/common/models/product.py`.
- UOM master data is tenant-scoped.
- This story does not change stock quantities or introduce conversion ratios.

### Project Structure Notes

- Backend: `backend/common/models/unit_of_measure.py`, `backend/domains/inventory/services.py`, `backend/domains/inventory/routes.py`, `backend/domains/inventory/schemas.py`
- Frontend: `src/domain/inventory/components/UnitCombobox.tsx`, `src/pages/inventory/UnitsPage.tsx`, `src/domain/inventory/components/CreateProductForm.tsx`, `src/domain/inventory/components/EditProductForm.tsx`

### What NOT to implement

- Do **not** add unit-conversion tables or quantity-conversion logic here.
- Do **not** migrate `Product.unit` to a foreign key in this story.
- Do **not** auto-convert supplier-order quantities between units.

### Testing Standards

- Include seed-idempotency coverage.
- Include product-form coverage proving the stored product value remains the UOM code string.

## Dependencies & Related Stories

- **Depends on:** Story 4.9 (Create Product), Story 4.10 (Update Product)
- **Related to:** Story 4.12 (Product Categories) because both stories standardize product-form master-data selectors

## References

- `backend/common/models/product.py`
- `backend/domains/inventory/services.py`
- `backend/domains/inventory/routes.py`
- `src/domain/inventory/components/CreateProductForm.tsx`
