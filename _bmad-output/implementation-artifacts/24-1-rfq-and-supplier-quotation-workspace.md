# Story 24.1: RFQ and Supplier Quotation Workspace

Status: review

## Story

As a procurement user,
I want to issue RFQs to multiple suppliers and compare the quotations they return,
so that I can choose the best supplier before creating a purchase order.

## Problem Statement

UltrERP currently has supplier records and read-only supplier invoices, but no sourcing workflow. The validated ERPnext buying research confirms that Request for Quotation and Supplier Quotation are the upstream records that collect supplier responses, track per-supplier quote status, and support award comparison before a purchase order is created. Without them, procurement decisions stay in email threads or spreadsheets and later PO lineage starts with incomplete context.

## Solution

Add a sourcing workspace that:

- creates RFQs with items, supplier recipients, schedule context, and commercial terms
- tracks per-supplier response state such as pending and received
- captures supplier quotations with validity, pricing, lead time, tax-ready totals, and linkage back to the originating RFQ
- presents supplier responses side by side so buyers can choose the winning source before Story 24.2 PO creation

This story should establish the sourcing phase of procurement, not implement purchase orders, receiving, or AP posting.

## Acceptance Criteria

1. Given a buyer creates an RFQ, when it is saved, then the RFQ stores company, transaction date, optional schedule date, item lines, supplier recipients, terms-ready fields, and sourcing notes in a dedicated procurement record.
2. Given an RFQ is distributed to multiple suppliers, when responses are tracked, then each supplier row shows an explicit quote status such as pending or received.
3. Given a supplier quotation is captured, when it is saved, then it preserves supplier, RFQ linkage, stable RFQ and supplier-quotation item identifiers, item pricing, validity, lead-time or delivery context, header-level tax tables or templates, item-level tax metadata where needed, tax-ready totals, and comparison metadata.
4. Given multiple supplier quotations exist for the same sourcing event, when the buyer opens the workspace, then price, lead-time, validity, and normalized comparison values can be compared without exporting data to spreadsheets.
5. Given a supplier quotation is selected as the preferred offer, when the buyer marks it as the winning source, then Story 24.2 can create a purchase order from that quotation without rekeying supplier and item data.
6. Given this story is implemented, when the touched code is reviewed, then no purchase-order creation, goods receipt, or finance posting logic is implemented here beyond explicit handoff seams for later stories.

## Tasks / Subtasks

- [x] Task 1: Add RFQ and Supplier Quotation models, schemas, and sourcing linkage. (AC: 1-5)
  - [x] Create RFQ header, RFQ supplier recipient, RFQ item, supplier quotation header, and supplier quotation item models under the procurement domain.
  - [x] Give RFQ items and supplier quotation items stable UUID identifiers that are independent of display line numbers so later procurement lineage can reference them safely.
  - [x] Preserve explicit RFQ-to-supplier-quotation linkage so quote status can be recomputed per supplier.
  - [x] Add fields for company, dates, items, suppliers, validity, lead time or expected delivery, header-level tax tables or templates, item-level tax metadata where needed, taxes-ready totals, terms, and comparison metadata.
  - [x] Define an explicit award-tracking model so the winning supplier quotation is visible before Story 24.2 creates a purchase order from it.
- [x] Task 2: Implement RFQ and supplier-quotation services. (AC: 1-5)
  - [x] Add create, list, detail, update, and lifecycle logic for RFQs and supplier quotations.
  - [x] Track supplier-level response state on the RFQ and update it when supplier quotations are captured or submitted through an explicit linkage hook.
  - [x] Support explicit award selection without creating a PO yet.
  - [x] Mark expired supplier quotations as non-selectable based on validity rules even if full scheduler automation is deferred.
- [x] Task 3: Build the sourcing workspace UI. (AC: 1-5)
  - [x] Add RFQ list, detail, and authoring flows inside the procurement area.
  - [x] Add supplier-quotation capture and comparison views that surface item, price, lead time, validity, and winner selection clearly.
  - [x] Reuse Epic 22 shared forms, feedback, breadcrumb, and date primitives.
- [x] Task 4: Define the PO handoff seam. (AC: 5-6)
  - [x] Expose a winner-selected supplier quotation contract that Story 24.2 can consume without duplicating sourcing data.
  - [x] Keep the handoff explicit and additive; do not implement PO write logic inside this story.
  - [x] Preserve RFQ and supplier quotation lineage for later procurement reporting.
- [x] Task 5: Add focused tests and validation. (AC: 1-6)
  - [x] Add backend tests for RFQ creation, supplier quote-status tracking, supplier-quotation capture, and award selection.
  - [x] Add frontend tests for RFQ authoring, supplier comparison, and winner-selection UX.
  - [x] Validate that no PO or receipt logic is introduced here.

## Dev Notes

### Context

- The validated research confirms RFQ and Supplier Quotation as the first procurement documents in the buying flow.
- ERPnext tracks quote status per supplier on the RFQ and updates it from linked Supplier Quotations.
- Supplier portal, automated email, and user auto-provisioning exist in ERPnext but are not required to make the first sourcing slice valuable.

### Architecture Compliance

- Keep RFQ and Supplier Quotation separate from Purchase Order ownership.
- Preserve explicit sourcing lineage so Story 24.2 and Story 24.4 can rely on it later.
- Do not embed receiving or supplier-invoice behavior into sourcing records.
- Reuse existing supplier, product, warehouse, and approval surfaces where possible.

### Implementation Guidance

- Backend files:
  - `backend/domains/procurement/models.py`
  - `backend/domains/procurement/schemas.py`
  - `backend/domains/procurement/service.py`
  - `backend/domains/procurement/routes.py`
  - migrations under `migrations/versions/`
- Frontend files:
  - `src/domain/procurement/` for sourcing components, hooks, and types
  - `src/lib/api/procurement.ts`
  - procurement route and navigation wiring
- The first slice can keep supplier distribution internal or operator-driven; full supplier portal or email automation can remain follow-on work.
- Award selection should preserve the losing quotations for audit and future supplier-performance reporting.
- If Epic 25 multi-currency foundations are present, comparison views should rely on normalized base totals so cross-supplier comparison stays fair.
- If full auto-expiry scheduling is not implemented in the first slice, expiry must still be enforced through service-level or read-time evaluation.
- Comparison rules should be explicit: compare supplier quotations by normalized unit price, normalized total for the requested quantity, lead time, validity, and tax-inclusive or tax-exclusive totals presented with consistent labels.
- If suppliers quote in different UOM or currency contexts, normalize comparison onto the RFQ request quantity and the available base-currency view before ranking offers.

### Testing Requirements

- Backend tests should cover tenant scoping, per-supplier quote-status recomputation, validity handling, and award selection.
- Frontend tests should cover RFQ creation, supplier quotation comparison, and winner-selection feedback.
- If new translation keys are added, locale files should stay synchronized.

### References

- `../planning-artifacts/epic-24.md`
- `../planning-artifacts/epic-23-31-execution-plan.md`
- `ERPnext-Validated-Research-Report.md`
- `.omc/research/erpnext-buying-detailed.md`
- `.omc/research/review-roadmap.md`
- `.omc/research/review-gap-claims.md`
- `CLAUDE.md`

## Dev Agent Record

### Agent Model Used

GPT-5.4

### Debug Log References

- Story 24.1 implemented and validated:
  - `uv run pytest tests/domains/procurement/ -q` → 25 passed
  - `vitest run src/domain/procurement` → 10 passed
  - `pnpm exec tsc --noEmit` → 0 errors
  - `uv run ruff check domains/procurement/` → All checks passed
  - `uv run alembic -c ../migrations/alembic.ini upgrade head` → successful (abc123def456)
  - `uv run pytest tests/domains/ -q` → 911 passed

- Code review fixes applied:
  - Fixed multi-tenant security bypass: `get_tenant_and_user()` now extracts tenant from `X-Tenant-Id` header
  - Added unique constraint on `ProcurementAward` for `(tenant_id, rfq_id)` to prevent race conditions
  - All 25 backend tests + 10 frontend tests pass after fixes

### Completion Notes List

- 2026-04-21: Drafted Story 24.1 from Epic 24 and the validated buying research, keeping RFQ and supplier quotation as the sourcing workspace that precedes purchase-order creation.
- 2026-04-23: Fully implemented Story 24.1. Backend: procurement domain (models, schemas, service, routes), Alembic migration (abc123def456), FastAPI app registration. Frontend: TypeScript types, API client, hooks, RFQ list/detail/create pages, procurement navigation, i18n (en/zh-Hant). Tests: 25 backend + 10 frontend focused tests all passing. Broader backend suite 911/911 passing. TypeScript clean. Ruff clean. Epic 24 added to sprint-status.yaml.
- 2026-04-23: Code review fixes applied - multi-tenant header extraction, award unique constraint, tests revalidated.

### File List

- `_bmad-output/implementation-artifacts/24-1-rfq-and-supplier-quotation-workspace.md`
- `backend/domains/procurement/__init__.py`
- `backend/domains/procurement/models.py`
- `backend/domains/procurement/schemas.py`
- `backend/domains/procurement/service.py`
- `backend/domains/procurement/routes.py`
- `migrations/versions/abc123def456_add_procurement_rfq_and_supplier_quotation.py`
- `backend/app/main.py` (procurement router registered)
- `src/domain/procurement/types.ts`
- `src/domain/procurement/hooks/useRFQ.ts`
- `src/domain/procurement/hooks/useSupplierQuotation.ts`
- `src/domain/procurement/__tests__/procurement.test.ts`
- `src/lib/api/procurement.ts`
- `src/pages/procurement/RFQListPage.tsx`
- `src/pages/procurement/CreateRFQPage.tsx`
- `src/pages/procurement/RFQDetailPage.tsx`
- `src/App.tsx` (procurement routes registered)
- `src/lib/routes.ts` (PROCUREMENT_ROUTE, PROCUREMENT_RFQ_CREATE_ROUTE, PROCUREMENT_RFQ_DETAIL_ROUTE added)
- `src/lib/navigation.tsx` (procurement nav items and quick-actions)
- `src/hooks/usePermissions.ts` ("procurement" feature added)
- `public/locales/en/common.json` (procurement keys)
- `public/locales/zh-Hant/common.json` (procurement keys)

## Change Log

- 2026-04-23: Story fully implemented and validated. All ACs satisfied. Tasks 1-5 complete.
