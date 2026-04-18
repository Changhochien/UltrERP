# Story 4.16: Inventory Valuation and Cost Tracking

**Status:** backlog

**Story ID:** 4.16

**Epic:** Epic 4 - Inventory Operations

---

## Story

As a finance manager,
I want inventory valuation to use a clear product cost source,
so that per-product and per-warehouse inventory values are explainable and audit-friendly.

---

## Best-Practice Update

- Store `standard_cost` as a database `NUMERIC/DECIMAL` and serialize it as a string in API responses. Do not use floating-point cost math for valuation data.
- When `standard_cost` is missing, allow reporting to fall back to the latest purchase cost, but expose the fallback as metadata instead of silently pretending it is the standard cost.
- Keep valuation read-only. Latest purchase cost can inform reporting, but it must not overwrite the product master automatically in this story.

## Acceptance Criteria

1. Given I create or edit a product, when I provide `standard_cost`, then the value is persisted on the product and returned in product read models.
2. Given inventory stock exists, when I request valuation, then the response shows per-product and per-warehouse quantity, unit cost, extended value, and total warehouse value.
3. Given a product has no `standard_cost` but has received purchase history with unit prices, when I request valuation, then the latest received purchase cost is used as a reporting fallback and the response marks `cost_source = "latest_purchase"`.
4. Given a product has neither `standard_cost` nor purchase-cost history, when I request valuation, then the product still appears with `cost_source = "missing"` and `extended_value = 0`.
5. Given I review valuation totals, when multiple warehouses hold stock, then I can see warehouse subtotals and a grand total without mixing warehouse quantities together invisibly.

## Tasks / Subtasks

- [ ] **Task 1: Add `standard_cost` to the product model and contracts** (AC: 1)
  - [ ] Add an Alembic migration for `product.standard_cost NUMERIC(19,4) NULL`.
  - [ ] Extend `backend/common/models/product.py` with `standard_cost`.
  - [ ] Extend `ProductCreate`, `ProductUpdate`, `ProductResponse`, and `ProductDetailResponse` in `backend/domains/inventory/schemas.py`.
  - [ ] Extend the matching TypeScript product types in `src/domain/inventory/types.ts`.

- [ ] **Task 2: Add product-form support for standard cost** (AC: 1)
  - [ ] Add `standard_cost` to `CreateProductForm.tsx` and `EditProductForm.tsx`.
  - [ ] Display the value in the product detail/settings experience.
  - [ ] Validate `standard_cost >= 0`.

- [ ] **Task 3: Add a valuation read model** (AC: 2, 3, 4, 5)
  - [ ] Add `get_inventory_valuation(session, tenant_id, warehouse_id=None)` to `backend/domains/inventory/services.py`.
  - [ ] Compute value per stock row as `resolved_unit_cost * quantity`.
  - [ ] Add a helper that resolves `cost_source` in this order: `standard_cost` -> latest received purchase cost -> missing.
  - [ ] Keep numeric precision in Python `Decimal` until serialization.

- [ ] **Task 4: Add the valuation route** (AC: 2, 3, 4, 5)
  - [ ] Add `GET /api/v1/inventory/reports/valuation` to `backend/domains/inventory/routes.py`.
  - [ ] Support optional `warehouse_id`.
  - [ ] Return per-row detail, warehouse subtotals, and grand total.

- [ ] **Task 5: Build the valuation page** (AC: 2, 3, 4, 5)
  - [ ] Create `src/pages/inventory/InventoryValuationPage.tsx`.
  - [ ] Show warehouse filter, row-level cost source badges, subtotal cards, and a grand total.
  - [ ] Keep missing-cost rows visible rather than filtering them out.

- [ ] **Task 6: Add focused regression tests** (AC: 1, 2, 3, 4, 5)
  - [ ] Backend tests for `standard_cost`, latest-purchase fallback, missing-cost rows, and subtotal math.
  - [ ] Frontend tests for product forms and valuation-page rendering.

## Dev Notes

### Architecture Compliance

- Cost fields must remain decimal-safe end to end.
- Warehouse valuation should be based on `inventory_stock.quantity`, not on aggregated product totals alone.
- Purchase-cost fallback should read from supplier-order receipt history and remain reporting-only in this story.

### Project Structure Notes

- Backend: `backend/common/models/product.py`, `backend/domains/inventory/services.py`, `backend/domains/inventory/routes.py`, `backend/domains/inventory/schemas.py`
- Frontend: `src/domain/inventory/components/CreateProductForm.tsx`, `src/domain/inventory/components/EditProductForm.tsx`, `src/pages/inventory/InventoryValuationPage.tsx`

### What NOT to implement

- Do **not** add FIFO, LIFO, weighted-average costing, or accounting journal posting.
- Do **not** auto-write latest purchase cost back into `standard_cost`.
- Do **not** hide missing-cost rows from the valuation output.

### Testing Standards

- Include numeric-precision coverage for decimal serialization.
- Include at least one test proving that fallback cost source metadata is surfaced to the client.

## Dependencies & Related Stories

- **Depends on:** Story 4.5 (Supplier Orders), Story 4.9 (Create Product), Story 4.10 (Update Product)
- **Related to:** Story 4.15 (Inventory Reports) because the valuation page lives in the same reporting surface

## References

- `backend/common/models/product.py`
- `backend/common/models/supplier_order.py`
- `backend/domains/inventory/services.py`
- `backend/domains/inventory/routes.py`
- `src/domain/inventory/components/CreateProductForm.tsx`
