# Story 4.21: Default Supplier per Product

**Status:** backlog

**Story ID:** 4.21

**Epic:** Epic 4 - Inventory Operations

---

## Story

As a procurement staff member,
I want products to carry explicit supplier associations with one default supplier,
so that purchase-order creation can prefill the right supplier instead of guessing.

---

## Best-Practice Update

- The repo already exposes a read-only `GET /api/v1/inventory/products/{product_id}/supplier` helper that infers the most recent supplier from orders/invoices. This story should introduce explicit product-supplier associations and make the heuristic a fallback, not the primary source of truth.
- Enforce one default supplier per product at the database/service layer so UI bugs cannot leave multiple defaults behind.
- Supplier-order prefill must only auto-select a supplier when the chosen product set resolves consistently; otherwise the form should stay blank and ask the user to choose.

## Acceptance Criteria

1. Given a product can be purchased from multiple suppliers, when I manage its supplier associations, then I can add/remove suppliers, optionally record `unit_cost` and `lead_time_days`, and mark exactly one supplier as default.
2. Given I view product settings, when supplier associations exist, then I can see the association list and which supplier is currently the default.
3. Given I create a supplier order for a single product with an explicit default supplier, when the order form opens, then the supplier field is prefilled with that default supplier.
4. Given I create a multi-line supplier order, when the selected products resolve to different default suppliers, then the form does not guess; it leaves supplier selection to the user and surfaces the conflict clearly.
5. Given a product has no explicit default supplier, when the legacy `GET /products/{product_id}/supplier` helper is called, then it falls back to the existing most-recent-supplier heuristic.

## Tasks / Subtasks

- [ ] **Task 1: Add the association model and migration** (AC: 1, 2)
  - [ ] Create `backend/common/models/product_supplier.py` with `id`, `tenant_id`, `product_id`, `supplier_id`, `unit_cost`, `lead_time_days`, `is_default`, `created_at`, and `updated_at`.
  - [ ] Add a tenant/product/supplier uniqueness constraint.
  - [ ] Add a database-level rule that enforces one default supplier per product, such as a partial unique index or equivalent service-safe invariant.

- [ ] **Task 2: Add schemas and service methods** (AC: 1, 2, 3, 4, 5)
  - [ ] Add product-supplier request/response schemas to `backend/domains/inventory/schemas.py`.
  - [ ] Add service methods to add, list, update, remove, and set default product-supplier associations.
  - [ ] Update `get_product_supplier()` so it returns explicit default supplier data first and only falls back to the existing heuristic when no association exists.

- [ ] **Task 3: Add product-supplier routes** (AC: 1, 2, 5)
  - [ ] Add `GET /api/v1/inventory/products/{product_id}/suppliers`
  - [ ] Add `POST /api/v1/inventory/products/{product_id}/suppliers`
  - [ ] Add `PATCH /api/v1/inventory/products/{product_id}/suppliers/{supplier_id}`
  - [ ] Add `DELETE /api/v1/inventory/products/{product_id}/suppliers/{supplier_id}`

- [ ] **Task 4: Add frontend types and API helpers** (AC: 1, 2, 3, 4)
  - [ ] Add product-supplier types to `src/domain/inventory/types.ts`.
  - [ ] Add product-supplier API helpers to `src/lib/api/inventory.ts`.

- [ ] **Task 5: Build the product-supplier management UI** (AC: 1, 2)
  - [ ] Create `src/domain/inventory/components/ProductSuppliersPanel.tsx`.
  - [ ] Mount it inside the inventory product settings experience, reusing `SettingsTab.tsx` or the product-detail surface already present in the repo.
  - [ ] Support add/remove/default actions without requiring a separate supplier-management subsystem.

- [ ] **Task 6: Update supplier-order prefill behavior** (AC: 3, 4, 5)
  - [ ] Update `SupplierOrderForm.tsx` so a single-product flow prefills the explicit default supplier when available.
  - [ ] For multi-line flows, prefill only when all selected products resolve to the same default supplier.
  - [ ] Surface a conflict message when product defaults disagree.

- [ ] **Task 7: Add focused regression tests** (AC: 1, 2, 3, 4, 5)
  - [ ] Backend tests for one-default enforcement, fallback behavior, and association CRUD.
  - [ ] Frontend tests for `ProductSuppliersPanel` and supplier-order prefill/conflict behavior.

## Dev Notes

### Architecture Compliance

- Explicit associations become the primary product-supplier source of truth.
- Historical supplier orders and invoices must remain readable even if associations change later.
- Keep all queries tenant-scoped and product-scoped.

### Project Structure Notes

- Backend: `backend/common/models/product_supplier.py`, `backend/domains/inventory/services.py`, `backend/domains/inventory/routes.py`, `backend/domains/inventory/schemas.py`
- Frontend: `src/domain/inventory/components/ProductSuppliersPanel.tsx`, `src/domain/inventory/components/SupplierOrderForm.tsx`, `src/domain/inventory/components/SettingsTab.tsx`, `src/lib/api/inventory.ts`

### What NOT to implement

- Do **not** auto-create product-supplier associations during generic product creation.
- Do **not** add supplier price-history analytics in this story.
- Do **not** auto-select a supplier in multi-product order flows when defaults conflict.

### Testing Standards

- Include backend coverage for one-default enforcement under concurrent updates if feasible.
- Include frontend coverage for the ambiguous multi-product prefill case.

## Dependencies & Related Stories

- **Depends on:** Story 4.13 (Supplier CRUD UI), Story 4.5 (Supplier Orders), Story 4.9 (Create Product), Story 4.10 (Update Product)
- **Related to:** Story 4.14 (Reorder Suggestions), which should consume the explicit default supplier when available

## References

- `backend/common/models/supplier.py`
- `backend/common/models/supplier_order.py`
- `backend/domains/inventory/services.py`
- `backend/domains/inventory/routes.py`
- `src/domain/inventory/components/SupplierOrderForm.tsx`
- `src/domain/inventory/hooks/useProductSupplier.ts`
