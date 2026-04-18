# Story 4.12: Product Categories Management

**Status:** done

**Story ID:** 4.12

**Epic:** Epic 4 - Inventory Operations

---

## Story

As a warehouse staff,
I want to manage a shared category catalog for products,
so that product classification is consistent across create, edit, search, and reporting flows.

---

## Best-Practice Update

- Keep `Product.category` as a denormalized text field for v1, but introduce a tenant-scoped category master so product forms stop drifting into free-text spelling variants.
- Category rename/deactivate must not silently rewrite historical product rows. The product stores the category name string at the time it was saved.
- Inline category creation in product forms is acceptable only if it creates a category record first and then writes the chosen category name back to `Product.category`. Do not bypass the catalog with arbitrary unsaved strings once `CategoryCombobox` exists.

## Acceptance Criteria

1. Given I manage categories, when I create, edit, list, or deactivate a category, then the category master data persists per tenant and active categories are available to product forms.
2. Given I create or edit a product, when I open the category field, then I use `CategoryCombobox` to select an active category or create a new one inline through the category API.
3. Given a product stores a category value, when I save the product, then `Product.category` remains a text field containing the chosen category name.
4. Given a category is renamed or deactivated, when I inspect existing products that already stored the old text value, then those products keep their stored category string until a user edits them explicitly.
5. Given I browse/search products, when I filter by category, then only products whose stored `category` text matches the selected category are returned.

## Tasks / Subtasks

- [x] **Task 1: Add the category master model and migration** (AC: 1, 4)
  - [x] Create `backend/common/models/category.py` with `id`, `tenant_id`, `name`, `is_active`, `created_at`, and `updated_at`.
  - [x] Add an Alembic migration with a tenant-scoped unique constraint on category name.
  - [x] Prefer soft delete (`is_active = false`) over hard delete so the master list preserves auditability and avoids accidental reuse confusion.

- [x] **Task 2: Add category schemas and services** (AC: 1, 2, 4)
  - [x] Add `CategoryCreate`, `CategoryUpdate`, `CategoryResponse`, and `CategoryListResponse` to `backend/domains/inventory/schemas.py`.
  - [x] Add `create_category`, `list_categories`, `get_category`, `update_category`, and `set_category_status` to `backend/domains/inventory/services.py`.
  - [x] When deactivating a category that is still referenced by products, keep the category row but hide it from active selectors.

- [x] **Task 3: Add category routes** (AC: 1)
  - [x] Add `POST /api/v1/inventory/categories`
  - [x] Add `GET /api/v1/inventory/categories`
  - [x] Add `GET /api/v1/inventory/categories/{category_id}`
  - [x] Add `PUT /api/v1/inventory/categories/{category_id}`
  - [x] Add `PATCH /api/v1/inventory/categories/{category_id}/status`
  - [x] Use `ReadUser` for reads and `WriteUser` for writes.

- [x] **Task 4: Add product-category filter support** (AC: 5)
  - [x] Extend the product search/list query path with an optional category filter that compares against `Product.category`.
  - [x] Keep the comparison tenant-scoped and compatible with the denormalized text model.

- [x] **Task 5: Add frontend types and API helpers** (AC: 1, 2, 5)
  - [x] Add category types to `src/domain/inventory/types.ts`.
  - [x] Add category API helpers to `src/lib/api/inventory.ts`.
  - [x] Reuse direct category API calls in the UI instead of adding a shared category hook because this slice did not require cached cross-page category state.

- [x] **Task 6: Build `CategoryCombobox` and wire product forms** (AC: 2, 3)
  - [x] Create `src/domain/inventory/components/CategoryCombobox.tsx`.
  - [x] Replace the free-text category input in `CreateProductForm.tsx`.
  - [x] Use the same component in `EditProductForm.tsx` from Story 4.10.
  - [x] Support inline create, but persist through the category API first.

- [x] **Task 7: Add the category management page** (AC: 1)
  - [x] Create `src/pages/inventory/CategoriesPage.tsx`.
  - [x] Show list, search/filter, create, edit, and deactivate actions.
  - [x] Add an inventory navigation entry rather than burying category management inside an unrelated page.

- [x] **Task 8: Add focused regression tests** (AC: 1, 2, 3, 4, 5)
  - [x] Backend tests for CRUD, uniqueness, and deactivate behavior.
  - [x] Frontend tests for `CategoryCombobox`, inline create, and the management page.
  - [x] Product-form tests proving category values still save as text on the product record.

## Dev Notes

### Architecture Compliance

- `Product.category` remains a plain string in `backend/common/models/product.py`.
- The category master exists to standardize choices, not to normalize the product table yet.
- All category reads/writes must remain tenant-scoped.

### Project Structure Notes

- Backend: `backend/common/models/category.py`, `backend/domains/inventory/routes.py`, `backend/domains/inventory/services.py`, `backend/domains/inventory/schemas.py`
- Frontend: `src/domain/inventory/components/CategoryCombobox.tsx`, `src/pages/inventory/CategoriesPage.tsx`, `src/domain/inventory/components/CreateProductForm.tsx`, `src/domain/inventory/components/EditProductForm.tsx`

### What NOT to implement

- Do **not** add `product.category_id` or convert the product table to a foreign-key model in this story.
- Do **not** bulk rewrite existing product rows when a category is renamed.
- Do **not** add nested categories or taxonomy trees.

### Testing Standards

- Include coverage for category inline-create from the product form.
- Include coverage proving that deactivated categories disappear from comboboxes but historical product rows remain readable.

## Dependencies & Related Stories

- **Depends on:** Story 4.9 (Create Product) and Story 4.10 (Update Product)
- **Related to:** Story 4.1 (Search Products) for category filtering
- **Related to:** Story 4.18 (Unit of Measure) because both stories add product-form master-data selectors

## References

- `backend/common/models/product.py`
- `backend/domains/inventory/services.py`
- `backend/domains/inventory/routes.py`
- `src/domain/inventory/components/CreateProductForm.tsx`
- `src/domain/inventory/components/EditProductForm.tsx`

---

## Dev Agent Record

**Status:** done
**Last Updated:** 2026-04-18

### Completion Notes List

- Added a tenant-scoped `Category` master model, migration, duplicate-name contract, CRUD/status services, and inventory category routes while keeping `Product.category` as denormalized text.
- Extended the existing product search path with an optional category filter so browse/search surfaces reuse one backend query and one frontend hook instead of adding a parallel catalog path.
- Built a reusable `CategoryCombobox` with inline category creation, wired it into the shared product form, and added a dedicated `CategoriesPage` route plus an inventory header entry for category management.
- Added focused regression coverage for category CRUD/filter behavior, category combobox selection and inline create, categories page lifecycle actions, and product-form submission proving selected categories are still saved as plain text.

### Validation

- `cd backend && .venv/bin/python -m pytest tests/api/test_categories.py tests/domains/inventory/test_product_status.py -q`
- `pnpm vitest run src/tests/inventory/ProductTable.test.tsx src/tests/inventory/CategoryCombobox.test.tsx src/pages/inventory/CategoriesPage.test.tsx src/tests/inventory/CreateProductForm.test.tsx src/tests/inventory/EditProductForm.test.tsx`

### File List

- `backend/common/models/category.py`
- `backend/common/models/__init__.py`
- `backend/common/errors.py`
- `backend/domains/inventory/schemas.py`
- `backend/domains/inventory/services.py`
- `backend/domains/inventory/routes.py`
- `migrations/versions/d3e8f9a1b2c4_add_category_master_table.py`
- `backend/tests/api/test_categories.py`
- `backend/tests/domains/inventory/test_product_status.py`
- `src/domain/inventory/types.ts`
- `src/lib/api/inventory.ts`
- `src/domain/inventory/components/CategoryCombobox.tsx`
- `src/domain/inventory/components/ProductForm.tsx`
- `src/domain/inventory/hooks/useProductSearch.ts`
- `src/domain/inventory/components/ProductTable.tsx`
- `src/domain/inventory/components/ProductSearch.tsx`
- `src/pages/inventory/CategoriesPage.tsx`
- `src/pages/InventoryPage.tsx`
- `src/lib/routes.ts`
- `src/lib/navigation.tsx`
- `src/App.tsx`
- `src/tests/inventory/ProductTable.test.tsx`
- `src/tests/inventory/CategoryCombobox.test.tsx`
- `src/tests/inventory/CreateProductForm.test.tsx`
- `src/tests/inventory/EditProductForm.test.tsx`
- `src/pages/inventory/CategoriesPage.test.tsx`
- `public/locales/en/common.json`
- `public/locales/zh-Hant/common.json`
