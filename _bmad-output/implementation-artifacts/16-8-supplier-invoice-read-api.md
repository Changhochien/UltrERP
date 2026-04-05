# Story 16.8: Supplier Invoice Read API

Status: done

## Story

As a finance or warehouse operator,
I want read-only API access to imported supplier invoices,
So that I can inspect and verify migrated AP history after canonical import completes.

## Acceptance Criteria

**AC1:** Supplier invoice list endpoint returns paginated AP summaries
**Given** supplier invoices exist in the canonical AP tables
**When** I call `GET /api/v1/purchases/supplier-invoices`
**Then** the API returns paginated supplier invoice summaries with supplier name, totals, status, and line count
**And** the list supports status, supplier, page, page_size, and sort filters

**AC2:** Supplier invoice detail returns line-level enrichment
**Given** a supplier invoice exists in the canonical AP tables
**When** I call `GET /api/v1/purchases/supplier-invoices/{invoice_id}`
**Then** the API returns supplier invoice detail with line-level product-name enrichment
**And** the response includes invoice totals, notes, and imported line pricing/tax fields

**AC3:** Access is role-scoped and read-only
**Given** a caller does not have finance, warehouse, or owner access
**When** they request the supplier invoice read API
**Then** the RBAC dependency rejects the request
**And** the purchases surface introduces no write-side supplier-invoice endpoints

**AC4:** Missing supplier invoices return 404
**Given** a supplier invoice ID is unknown
**When** I request the detail endpoint
**Then** the API returns a 404 response with a clear not-found message

## Tasks / Subtasks

- [x] **Task 1: Add a dedicated purchases domain** (AC1, AC2, AC3, AC4)
  - [x] Create purchases schemas for supplier invoice list and detail responses
  - [x] Create purchases service helpers for list/detail reads
  - [x] Create purchases routes under `/api/v1/purchases`

- [x] **Task 2: Add read-side enrichment** (AC1, AC2)
  - [x] Resolve supplier display names for list and detail responses
  - [x] Resolve product display names for supplier invoice lines
  - [x] Expose line counts in the list response and full lines in detail

- [x] **Task 3: Wire the purchases router into the FastAPI app** (AC1, AC2, AC3, AC4)
  - [x] Register the purchases router in `backend/app/main.py`
  - [x] Keep the new API surface read-only

- [x] **Task 4: Add focused route validation** (AC1, AC2, AC4)
  - [x] Add route test coverage for list serialization
  - [x] Add route test coverage for detail enrichment
  - [x] Add route test coverage for 404 handling

## Dev Notes

### Repo Reality

- Before this story, the repo had an AP canonical landing zone but no backend domain exposing it for verification or read-side consumption.
- The closest reusable patterns were the existing invoice and inventory route/service/schema modules.
- The resulting purchases surface is intentionally read-only because write-side AP workflow is still deferred.

### Critical Warnings

- Do **not** add write-side supplier invoice endpoints until AP workflow, approvals, and payment semantics are designed.
- Do **not** bypass the shared RBAC dependency model; this surface is limited to finance/warehouse roles plus owner override.
- Do **not** duplicate the canonical import logic inside the purchases domain; it is a read model over already-imported AP data.

### Implementation Direction

- `GET /api/v1/purchases/supplier-invoices` returns paginated, filtered summaries.
- `GET /api/v1/purchases/supplier-invoices/{invoice_id}` returns supplier invoice detail plus product-name enrichment.
- The router is registered directly in `backend/app/main.py` alongside the rest of the API domains.

### Validation Follow-up

- `uv run pytest tests/domains/purchases/test_supplier_invoices_api.py -q`

## References

- `_bmad-output/planning-artifacts/epics.md` - Epic 16 / Story 16.8
- `backend/domains/purchases/routes.py` - purchases API routes
- `backend/domains/purchases/service.py` - supplier invoice read service
- `backend/domains/purchases/schemas.py` - response schemas
- `backend/app/main.py` - router registration
- `backend/tests/domains/purchases/test_supplier_invoices_api.py` - focused purchases route tests
- `docs/legacy/purchase-invoice-canonical-target.md` - AP target and endpoint note

## Dev Agent Record

### Agent Model Used

GPT-5.4

### Completion Notes List

- Added a new read-only purchases backend domain for imported supplier invoices.
- Exposed paginated list/detail routes with supplier-name and product-name enrichment.
- Guarded the new API surface with finance/warehouse RBAC and kept it read-only.
- Added focused API tests covering list serialization, detail enrichment, and 404 behavior.

### File List

- backend/domains/purchases/__init__.py
- backend/domains/purchases/schemas.py
- backend/domains/purchases/service.py
- backend/domains/purchases/routes.py
- backend/app/main.py
- backend/tests/domains/purchases/test_supplier_invoices_api.py
- docs/legacy/purchase-invoice-canonical-target.md

### Change Log

- 2026-04-05: Documented the new purchases read API as a dedicated Epic 16 story artifact after implementing the backend list/detail surface.