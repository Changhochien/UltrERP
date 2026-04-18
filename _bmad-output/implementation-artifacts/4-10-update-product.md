# Story 4.10: Update Product

**Status:** done

**Story ID:** 4.10

**Epic:** Epic 4 - Inventory Operations

---

## Story

As a warehouse staff,
I want to edit an existing product's master data,
so that code, name, category, description, and unit stay accurate over time.

---

## Best-Practice Update

- Keep the requested `PUT /api/v1/inventory/products/{product_id}` contract, but have the UI submit a full editable payload from a pre-populated form. Do not mix a `PUT` route with sparse patch semantics in the form layer.
- Reuse the create-product patterns from Story 4.9: trim inputs, reuse `DuplicateProductCodeError`, preserve tenant isolation, and refresh `search_vector` when `code` or `name` changes.
- Extend the product-detail read model first. The current product-detail payload does not expose `description` or `unit`, so the edit form cannot pre-populate correctly until that gap is closed.

## Acceptance Criteria

1. Given an existing product, when I open `EditProductForm` from the inventory product-detail experience, then `code`, `name`, `category`, `description`, and `unit` are pre-populated from the current record.
2. Given I submit a valid edit through `PUT /api/v1/inventory/products/{product_id}`, when the update succeeds, then the API returns HTTP 200 with the updated product and the product keeps the same `id`, `tenant_id`, and `status`.
3. Given I keep the same code or change it to a unique code, when I save, then the update succeeds and the product search/detail views reflect the new values immediately.
4. Given another product in the same tenant already owns the requested code, when I attempt the update, then the API returns HTTP 409 using the duplicate-code error contract already established in Story 4.9.
5. Given required fields are blank or whitespace-only, when I submit the edit, then the API returns HTTP 422 with field-level validation errors and the stored record remains unchanged.

## Tasks / Subtasks

- [x] **Task 1: Extend the product read/write contracts** (AC: 1, 2, 5)
  - [x] Add `ProductUpdate` to `backend/domains/inventory/schemas.py` for the full editable payload: `code`, `name`, `category | null`, `description | null`, `unit`.
  - [x] Extend `ProductDetailResponse` in `backend/domains/inventory/schemas.py` and `ProductDetail` in `src/domain/inventory/types.ts` to include `description` and `unit`.
  - [x] Keep `tenant_id`, `status`, and stock settings out of the write contract for this story.

- [x] **Task 2: Add the backend update path** (AC: 2, 3, 4, 5)
  - [x] Add `update_product(session, tenant_id, product_id, data)` to `backend/domains/inventory/services.py`.
  - [x] Load the product by `id` and `tenant_id`; return `None` for unknown products so the route can emit HTTP 404.
  - [x] Trim `code`, `name`, and `unit` before validation; reject whitespace-only required values with the same 422 behavior used in Story 4.9.
  - [x] Re-check code uniqueness case-insensitively while excluding the current product's own row.
  - [x] Recompute `search_vector` when `code` or `name` changes.
  - [x] Convert unique-index race failures into `DuplicateProductCodeError` rather than leaking a 500.

- [x] **Task 3: Add the inventory route** (AC: 2, 4, 5)
  - [x] Add `PUT /api/v1/inventory/products/{product_id}` to `backend/domains/inventory/routes.py`.
  - [x] Use the existing `WriteUser` dependency and route-level `session.commit()` pattern already used by inventory writes.
  - [x] Return HTTP 200 with `ProductResponse`, HTTP 404 when the product is missing, HTTP 409 for duplicate code, and HTTP 422 for validation failures.

- [x] **Task 4: Add the frontend API/types** (AC: 1, 2, 3, 4)
  - [x] Add `ProductUpdate` to `src/domain/inventory/types.ts`.
  - [x] Add `updateProduct(productId, data)` to `src/lib/api/inventory.ts`.
  - [x] Keep the response type aligned to `ProductResponse` so create/update share the same success shape.

- [x] **Task 5: Build `EditProductForm`** (AC: 1, 2, 4, 5)
  - [x] Create `src/domain/inventory/components/EditProductForm.tsx`.
  - [x] Reuse the same field layout and validation style as `CreateProductForm.tsx`; do not fork a second unrelated product-form implementation.
  - [x] Surface 409 duplicate-code feedback inline with a clear, friendly message.
  - [x] Expose `onSuccess(updatedProduct)` and `onCancel()` callbacks so the same form can be reused from multiple product-detail surfaces.

- [x] **Task 6: Wire the edit experience into product detail** (AC: 1, 2, 3)
  - [x] Add the primary edit entry point to `src/pages/inventory/ProductDetailPage.tsx`.
  - [x] Refresh the active product view after save so the header, tabs, and stock context continue using the updated product data.
  - [x] If the inventory drawer later adds edit support, reuse `EditProductForm` rather than creating a second edit UI.

- [x] **Task 7: Add focused regression tests** (AC: 1, 2, 3, 4, 5)
  - [x] Backend service tests: unchanged-code update, unique-code update, duplicate-code conflict, whitespace validation, product-not-found.
  - [x] Backend API tests for `PUT /api/v1/inventory/products/{id}` covering 200/404/409/422.
  - [x] Frontend tests for edit-form prefill, validation, duplicate-code handling, and success-refresh behavior.

## Dev Notes

### Architecture Compliance

- Keep all backend work inside `backend/domains/inventory/` and reuse `backend/common/models/product.py`.
- Preserve tenant scoping on every product lookup and mutation.
- Follow the existing async SQLAlchemy pattern already used by inventory services and routes; do not invent a separate data-access layer for product edit only.

### Project Structure Notes

- Backend: `backend/domains/inventory/routes.py`, `backend/domains/inventory/services.py`, `backend/domains/inventory/schemas.py`
- Frontend: `src/domain/inventory/components/EditProductForm.tsx`, `src/domain/inventory/types.ts`, `src/lib/api/inventory.ts`, `src/pages/inventory/ProductDetailPage.tsx`
- Existing dependencies to reuse: `src/domain/inventory/components/CreateProductForm.tsx`, `src/domain/inventory/hooks/useProductDetail.ts`

### What NOT to implement

- Do **not** add product status changes here. Active/inactive lifecycle belongs to Story 4.11.
- Do **not** add `standard_cost`; that belongs to Story 4.16.
- Do **not** move category/unit to master-data foreign keys here. Category/UOM master data belong to Stories 4.12 and 4.18.

### Testing Standards

- Keep backend coverage focused on the service and route contract.
- Keep frontend coverage focused on pre-filled state, inline validation, duplicate handling, and read-after-write refresh.
- Do not add E2E coverage unless the existing inventory test stack already has a product-detail flow worth extending.

## Dependencies & Related Stories

- **Depends on:** Story 4.9 (Create Product) for product validation/error-contract patterns
- **Related to:** Story 4.11 (Deactivate Product) for product lifecycle state
- **Related to:** Story 4.12 (Product Categories) and Story 4.18 (Unit of Measure) for future product-form field upgrades

## References

- `backend/common/models/product.py`
- `backend/domains/inventory/schemas.py`
- `backend/domains/inventory/services.py`
- `backend/domains/inventory/routes.py`
- `src/domain/inventory/components/CreateProductForm.tsx`
- `src/pages/inventory/ProductDetailPage.tsx`
- `src/domain/inventory/hooks/useProductDetail.ts`

---

## Dev Agent Record

**Status:** done
**Last Updated:** 2026-04-17

### Completion Notes List

- Added a full `PUT /api/v1/inventory/products/{product_id}` flow with shared normalization, duplicate-code handling, and whitespace validation aligned to Story 4.9.
- Extended the product-detail read model so edit forms can preload `description` and `unit` from the current record.
- Extracted a shared `ProductForm` so create and edit flows stay aligned rather than drifting into two separate implementations.
- Wired edit-product UX into the product detail page with optimistic local refresh plus full detail reload after save.
- Fixed the inventory create-product route to return Story 4.9-style 422 responses from the shared `ValidationError` contract.

### Validation

- `cd backend && uv run pytest tests/domains/inventory/test_product_detail.py tests/domains/inventory/test_update_product.py tests/api/test_update_product.py -q`
- `pnpm vitest run src/tests/inventory/CreateProductForm.test.tsx src/tests/inventory/EditProductForm.test.tsx src/pages/inventory/ProductDetailPage.test.tsx`
- VS Code diagnostics: no editor errors in touched backend/frontend files

### File List

- `backend/domains/inventory/schemas.py`
- `backend/domains/inventory/services.py`
- `backend/domains/inventory/routes.py`
- `backend/tests/domains/inventory/test_product_detail.py`
- `backend/tests/domains/inventory/test_update_product.py`
- `backend/tests/api/test_update_product.py`
- `src/domain/inventory/types.ts`
- `src/lib/api/inventory.ts`
- `src/domain/inventory/components/ProductForm.tsx`
- `src/domain/inventory/components/CreateProductForm.tsx`
- `src/domain/inventory/components/EditProductForm.tsx`
- `src/domain/inventory/hooks/useProductDetail.ts`
- `src/pages/inventory/ProductDetailPage.tsx`
- `src/pages/inventory/ProductDetailPage.test.tsx`
- `src/tests/inventory/EditProductForm.test.tsx`
- `public/locales/en/common.json`
- `public/locales/zh-Hant/common.json`
