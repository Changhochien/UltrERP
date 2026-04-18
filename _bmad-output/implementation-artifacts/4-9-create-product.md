# Story 4.9: Create Product

**Status:** ready-for-dev

**Story ID:** 4.9

**Epic:** Epic 4 - Inventory Operations

---

## Story

As a warehouse staff,
I want to add new products to the inventory with code, name, category, and unit,
so that the product catalog stays current as new items are stocked.

---

## Acceptance Criteria

**AC1:** Product creation with required fields
**Given** I am adding a new product
**When** I fill in code (required), name (required), unit (default: "pcs"), and submit
**Then** the product is persisted with a stable UUID and tenant_id
**And** I receive a 201 response with the created product

**AC2:** Product code uniqueness per tenant
**Given** a product with code "WIDGET-001" already exists for my tenant
**When** I try to create another product with code "WIDGET-001"
**Then** the system returns a 409 conflict with a clear error message
**And** no duplicate product is created

**AC3:** Optional fields — category and description
**Given** I am creating a product
**When** I optionally set category and description
**Then** those fields are persisted and returned in the response

**AC4:** Validation — missing required fields
**Given** I am creating a product without a code or name
**When** I submit the form
**Then** the system returns a 422 with field-level validation errors
**And** no product is created

**AC5:** Default status
**Given** I create a product without specifying status
**When** the product is persisted
**Then** status defaults to "active"

**AC6:** Read-after-create consistency
**Given** I just created a product successfully
**When** I search for it by its code
**Then** it appears in the product search results

---

## Tasks / Subtasks

- [ ] **Task 1: Backend — ProductCreate schema** (AC: 1, 3, 4, 5)
  - [ ] Add `ProductCreate` Pydantic schema to `backend/domains/inventory/schemas.py`
  - [ ] Fields: `code` (string, required, max 100 chars), `name` (string, required, max 500 chars), `category` (string | null, optional, max 200 chars), `description` (string | null, optional), `unit` (string, default "pcs", max 50 chars)
  - [ ] **`tenant_id` is NOT part of ProductCreate** — it is injected server-side by the route dependency, same pattern as `create_warehouse`
  - [ ] Add `ProductResponse` schema (used for the created resource response) — explicitly include only: `id`, `code`, `name`, `category | null`, `description | null`, `unit`, `status`, `created_at`; **exclude** `legacy_master_snapshot` and `search_vector`
  - [ ] Do NOT add reorder_point here — that is managed by Story 4.7

- [ ] **Task 2: Backend — create_product service function** (AC: 1, 2, 3, 5)
  - [ ] Add `DuplicateProductCodeError(existing_id, existing_code)` to `backend/common/errors.py` following the same `DuplicateBusinessNumberError` pattern
  - [ ] Add `duplicate_product_code_response(err)` helper returning `{"error": "duplicate_product_code", "existing_product_id": str, "existing_product_code": str}`
  - [ ] Add `create_product(session, tenant_id, data)` to `backend/domains/inventory/services.py`
  - [ ] Trim `code` before all checks (strip whitespace) — prevents `" WIDGET-001 "` from bypassing the duplicate guard
  - [ ] Validate code is not blank after trimming; raise `ValidationError` if blank
  - [ ] Check for duplicate code within same tenant; raise `DuplicateProductCodeError` if duplicate (HTTP 409)
  - [ ] **Populate `search_vector` on insert** — either via a PostgreSQL trigger on the `product` table, or by explicitly setting the tsvector value in the insert statement: `search_vector=func.to_tsvector('simple', data.name || ' ' || data.code)`
  - [ ] Insert `Product` row with `status = "active"` default
  - [ ] Return the created `Product` object

- [ ] **Task 3: Backend — POST /products endpoint** (AC: 1, 2, 3, 4, 5, 6)
  - [ ] Add `POST /api/v1/inventory/products` to `backend/domains/inventory/routes.py`
  - [ ] Use `WriteUser` auth dependency (warehouse staff can write)
  - [ ] Return `ProductResponse` with HTTP 201 on success
  - [ ] Return 409 on duplicate code, 422 on validation failure
  - [ ] Wire to `create_product` service function
  - [ ] Register error handler: `DuplicateProductCodeError → 409` via `duplicate_product_code_response()` in the router's exception handlers

- [ ] **Task 4: Frontend — product types and API client** (AC: 1, 2, 3, 4)
  - [ ] Add `ProductCreate` and `ProductResponse` types to `src/domain/inventory/types.ts`
  - [ ] Add `createProduct(data: ProductCreate): Promise<ProductResponse>` to `src/lib/api/inventory.ts`

- [ ] **Task 5: Frontend — CreateProductForm component** (AC: 1, 2, 3, 4)
  - [ ] Create `src/domain/inventory/components/CreateProductForm.tsx`
  - [ ] Fields: code (text), name (text), category (text, optional), description (textarea, optional), unit (text, default "pcs")
  - [ ] Inline validation errors displayed per field
  - [ ] Submit calls `createProduct`, shows loading state during request
  - [ ] On success: return/navigate so the product appears in ProductTable search
  - [ ] On 409 duplicate: display friendly "Product code already exists" message
  - [ ] Use the same form patterns as `CustomerForm` in `src/components/customers/CustomerForm.tsx` (Story 3.3) — prefer react-hook-form + zod if that is the established epic pattern; otherwise use React state consistent with the rest of the inventory module

- [ ] **Task 6: Frontend — Add Product button on InventoryPage** (AC: 1)
  - [ ] Add "Add Product" button next to the `WarehouseSelector` in `InventoryPage.tsx` header actions
  - [ ] Clicking opens `CreateProductForm` in a modal (reuse the existing modal pattern from `StockAdjustmentForm` in `InventoryPage.tsx`)
  - [ ] Only visible if `canWrite("inventory")` permission is true
  - [ ] On successful create: close modal, product is immediately searchable

- [ ] **Task 7: Tests** (AC: 1, 2, 3, 4, 5, 6)
  - [ ] Backend: service unit tests in `backend/tests/domains/inventory/test_create_product.py` — valid create, duplicate code, missing required fields
- [ ] Backend: API integration tests for `POST /api/v1/inventory/products`
- [ ] Frontend: `CreateProductForm.test.tsx` — validation, submit, 409 handling
- [ ] Verify existing product search tests still pass (read-after-create AC6)

### Review Findings

- [ ] [Review][Patch] Inventory router registers a non-existent `APIRouter.exception_handler`, which breaks module import before the backend can start [`backend/domains/inventory/routes.py:111`]
- [ ] [Review][Patch] Whitespace-only product codes raise a service `ValidationError` that the new endpoint never translates into the required HTTP 422 response [`backend/domains/inventory/routes.py:533`]
- [ ] [Review][Patch] Successful product creation only closes the modal and never refreshes inventory search results, so the new item is not immediately searchable as required by AC6 [`src/pages/InventoryPage.tsx:115`]
- [ ] [Review][Patch] Duplicate-code handling stops at the optimistic pre-check and does not convert unique-index races into `DuplicateProductCodeError`, so concurrent creates can still leak a 500 instead of the required 409 [`backend/domains/inventory/services.py:145`]
- [ ] [Review][Patch] The new API test session double omits `flush()` and `commit()`, so the create-product happy path cannot execute the real service and route logic [`backend/tests/api/test_create_product.py:45`]
- [ ] [Review][Patch] The duplicate-code API test asserts `existing_code`, but the implemented 409 envelope returns `existing_product_code`, so the test does not match the documented contract [`backend/tests/api/test_create_product.py:181`]

---

## Dev Notes

### Architecture Compliance

- **API Pattern:** FastAPI `POST /api/v1/inventory/products` with async/await, `WriteUser` auth
- **Database:** PostgreSQL 17 via async SQLAlchemy 2.0+ (`statement_cache_size=0` inherited from shared engine)
- **ORM:** Use the existing `Product` model at `backend/common/models/product.py` — no new table needed
- **Tenant isolation:** All product queries must filter by `tenant_id`; the create service must inject it
- **Error contract:** Reuse `DuplicateError` from `backend/common/errors.py` or follow the same pattern

### Project Structure Notes

**Backend:**
- Route: `backend/domains/inventory/routes.py` — add `create_product_endpoint`
- Service: `backend/domains/inventory/services.py` — add `create_product`, `DuplicateProductCodeError`
- Schema: `backend/domains/inventory/schemas.py` — add `ProductCreate`, `ProductResponse`
- Model: `backend/common/models/product.py` — already exists, reuse as-is

**Frontend:**
- Types: `src/domain/inventory/types.ts` — add `ProductCreate`, `ProductResponse`
- API: `src/lib/api/inventory.ts` — add `createProduct`
- Component: `src/domain/inventory/components/CreateProductForm.tsx` — new
- Page: `src/pages/InventoryPage.tsx` — add "Add Product" button and modal

**Database:**
- No new table or migration required — the `product` table already exists with all needed columns
- A PostgreSQL trigger or application-level tsvector assignment is needed to populate `search_vector` on insert — if a migration is needed for the trigger, add it under `migrations/versions/`

### What NOT to implement (Scope Guardrails)

- Do **not** add reorder_point, safety_factor, or stock level in this story — those are Story 4.7 (auto-calculate reorder points)
- Do **not** add a full ProductDetailPage create tab here — the modal on InventoryPage is sufficient
- Do **not** add product image upload or AEO content in this story
- Do **not** add a separate "Create Product" route/page — the modal workflow on InventoryPage matches the existing pattern for `StockAdjustmentForm` and `StockTransferForm`

### Dependency Notes

- No backend dependency on other Epic 4 stories — `Product` model and `tenant_id` column already exist
- Frontend depends on `canWrite("inventory")` permission hook (already in `InventoryPage.tsx`)
- Related: Story 4.1 (search) is the read path that confirms AC6; no circular dependency

### Testing Standards

- Backend: focused unit + API tests for create, duplicate, validation
- Frontend: focused component tests for form validation and 409 handling
- Do not add E2E tests unless the existing inventory E2E test suite already covers product create

---

## Dependencies & Related Stories

- **Depends on:** Nothing (Product model already exists from Story 4.1 or earlier)
- **Related to:** Story 4.1 (Search Products) — create feeds search (AC6)
- **Related to:** Story 4.7 (Auto-calculate Reorder Points) — reorder point is set separately, not in create
- **Pattern reference:** Story 3.3 (Create Customer) for form/modal patterns, Story 4.4 (Stock Adjustment) for modal pattern on InventoryPage

---

## Technology Stack Summary

| Technology | Version | Purpose |
|------------|---------|---------|
| FastAPI | 0.135+ | Backend API |
| PostgreSQL | 17+ | Primary data store |
| asyncpg | latest | Async database driver |
| SQLAlchemy | 2.0+ | ORM with async support |
| React | 19 | Frontend UI |
| react-hook-form or React state | latest | Form handling |

---

## References

- [Epic 4: Inventory Operations](../planning-artifacts/epics.md#epic-4-inventory-operations)
- [Story 4.1: Search Products](./4-1-search-products.md) — Product model already exists
- [Story 3.3: Create Customer Record](../implementation-artifacts/3-3-create-customer-record.md) — form/modal patterns reference
- [Story 4.4: Record Stock Adjustment](./4-4-record-stock-adjustment.md) — modal-on-InventoryPage pattern reference
- [Architecture: Technology Stack](../../docs/superpowers/specs/2026-03-30-erp-architecture-design-v2.md#3-technology-stack)
- [Product Model: backend/common/models/product.py](../../backend/common/models/product.py)

---

## Dev Agent Record

### Agent Model Used

claude-haiku-4.5

### Debug Log References

### Completion Notes List

- Story 4.9 created to address missing "Add Product" UI feature in inventory module
- No new database table or migration required — Product model already exists
- Scope intentionally excludes reorder_point (Story 4.7) and product variants
- Modal pattern on InventoryPage follows existing StockAdjustmentForm precedent

### File List

- `backend/domains/inventory/schemas.py` — add ProductCreate, ProductResponse
- `backend/domains/inventory/services.py` — add create_product, DuplicateProductCodeError
- `backend/domains/inventory/routes.py` — add POST /products endpoint
- `backend/common/errors.py` — add DuplicateProductCodeError and duplicate_product_code_response helper
- `backend/tests/domains/inventory/test_create_product.py` — new
- `backend/tests/api/test_create_product.py` — new
- `src/domain/inventory/types.ts` — add ProductCreate, ProductResponse
- `src/lib/api/inventory.ts` — add createProduct
- `src/domain/inventory/components/CreateProductForm.tsx` — new
- `src/pages/InventoryPage.tsx` — add Add Product button and modal
- `src/tests/inventory/CreateProductForm.test.tsx` — new
