# Story 23.3: Quotation Authoring and Lifecycle

Status: done

## Story

As a sales user preparing a formal offer,
I want quotations with lifecycle, validity, revision, and loss tracking,
so that UltrERP can manage commercial offers as first-class records before they become orders.

## Problem Statement

Lead and Opportunity establish pre-sale records, but UltrERP still has no formal quotation document. The validated ERPnext research confirms that quotation is where party targeting, valid-till controls, item lines, taxes, competitors, lost reasons, payment-term-ready context, and auto-repeat hooks converge. Without a quotation layer, sales offers remain informal, opportunity-to-order flow becomes brittle, and Epic 21 orders are forced to absorb pre-sale semantics that do not belong there.

## Solution

Add a quotation slice under CRM or Selling-aligned commercial ownership with:

- a formal quotation record targeting a customer, lead, or prospect through a dynamic-party contract
- base-currency quotation authoring with items, taxes, totals, contact and address context, and validity date
- explicit quotation statuses, expiry behavior, revision lineage, lost reasons, competitor context, and auto-repeat-ready metadata
- a clear backlink to the source opportunity while leaving actual order conversion to Story 23.4

This story should make quotation the canonical commercial-offer document without turning it into a sales-order or accounting record.

## Acceptance Criteria

1. Given a sales user creates a quotation, when it is saved, then the quotation stores target party context through `quotation_to` and `party_name`, plus transaction date, valid-till date, company, items, taxes, totals, contact data, billing and shipping address context, attribution fields, and opportunity backlink.
2. Given a quotation is authored in the first CRM slice, when users review commercial amounts, then the quotation runs in the existing base-currency model with explicit room for Epic 25 to add broader currency behavior later.
3. Given a quotation changes lifecycle state, when it is opened, replied to, partially ordered, ordered, lost, cancelled, or expired, then the transition follows a defined quotation status model aligned to the validated research.
4. Given a quotation is revised or amended, when the user creates the next revision, then prior quotation context remains linked through explicit revision lineage instead of silent overwrite.
5. Given a quotation is lost or expires, when the user closes it, then lost reasons, competitor context, and explanatory notes remain captured and reportable.
6. Given a quotation is configured for recurring reuse, when the record is saved, then auto-repeat-ready metadata is captured without requiring recurring document generation in this story.
7. Given this story is implemented, when the touched code is reviewed, then no sales-order creation, invoice creation, or GL posting logic is implemented inside quotation lifecycle handling beyond explicit conversion seams for Story 23.4.

## Tasks / Subtasks

- [x] Task 1: Add the quotation model, schemas, and base-currency commercial contract. (AC: 1-3, 6)
  - [x] Create a quotation model with explicit `quotation_to` and `party_name` targeting fields compatible with customer, lead, and prospect contexts.
  - [x] Add transaction date, valid-till, company, item lines, taxes, totals, contact fields, distinct billing and shipping address fields, UTM attribution fields, a reusable terms-template link plus inline terms override, opportunity backlink, and revision lineage fields.
  - [x] Keep the first slice on the current base-currency model while leaving clear extension seams for Epic 25 currency and payment-term enhancements.
  - [x] Add auto-repeat-ready metadata without implementing recurring generation here.
- [x] Task 2: Implement quotation CRUD and lifecycle services. (AC: 1-7)
  - [x] Add create, list, detail, update, and lifecycle-transition service logic for quotations.
  - [x] Enforce the validated status model `draft -> open -> replied -> partially ordered | ordered` with alternate `lost`, `cancelled`, and `expired` paths.
  - [x] Add expiry evaluation based on valid-till through service-level or read-time computation in the first slice without tying the story to a full scheduler platform.
  - [x] Compute `partially ordered` and `ordered` status from linked downstream order coverage rather than making those states purely manual toggles.
- [x] Task 3: Add revision, loss, and competitor handling. (AC: 4-5)
  - [x] Support amendment or revision lineage through an explicit backlink such as `amended_from` or equivalent, with no silent in-place overwrite of prior commercial records.
  - [x] Add structured lost-reason and competitor capture on lost quotations.
  - [x] Preserve prior commercial context and notes across revisions.
- [x] Task 4: Build the quotation authoring and detail UI. (AC: 1-6)
  - [x] Add quotation list, create, detail, and revision flows inside the CRM workspace.
  - [x] Surface validity, item totals, status, source opportunity, and loss context clearly in list and detail views.
  - [x] Expose an order-conversion seam in the UI only as a handoff action for Story 23.4, not as implemented conversion behavior in this story.
- [x] Task 5: Add focused tests and validation. (AC: 1-7)
  - [x] Add backend tests for lifecycle transitions, expiry behavior, revision lineage, lost-reason capture, and auto-repeat metadata persistence.
  - [x] Add frontend tests for quotation create/edit flow, state visibility, revision UX, and loss handling.
  - [x] Validate that no order or invoice write logic lands in this story.

## Dev Notes

### Context

- The validated research confirms quotation as the formal offer document with dynamic-party targeting, valid-till, items, taxes, lost reasons, competitors, opportunity backlink, and auto-repeat.
- Story 23.3 should consume opportunity context from Story 23.2, but should not pull order conversion or invoice behavior forward.
- Base-currency quotation authoring is acceptable here because Epic 25 will handle wider cross-currency rollout.

### Architecture Compliance

- Keep quotation as a pre-order commercial document, not as an order variant.
- Preserve opportunity backlinking and loss reporting without embedding sales-order logic.
- Keep recurring support metadata-only here; actual recurring generation belongs in later commercial automation work.
- Reuse Epic 22 form, date, breadcrumb, toast, and shared table primitives.

### Implementation Guidance

- Likely backend files:
  - `backend/domains/crm/models.py` or a closely related selling-aligned domain module
  - `backend/domains/crm/schemas.py`
  - `backend/domains/crm/service.py`
  - `backend/domains/crm/routes.py`
  - migrations under `migrations/versions/`
- Likely frontend files:
  - `src/domain/crm/` quotation components, hooks, and types
  - `src/lib/api/crm.ts`
  - CRM route and navigation wiring
- Terms and payment-term fields should remain compatible with Epic 25 template work rather than hardcoding a second incompatible commercial model.
- Terms should support both a reusable template reference and inline override text rather than a single hardcoded blob field.
- Expiry can start with service-level evaluation and explicit user-visible status updates even if cron-based auto-expiry is deferred.
- Quotations should preserve full revision lineage through amendment records rather than relying on silent in-place edits.

### Testing Requirements

- Backend tests should cover tenant scoping, valid and invalid lifecycle transitions, expiry rules, revision lineage, and loss capture.
- Frontend tests should cover quote creation, edit or revise flow, status visibility, and loss or expiry messaging.
- If new translation keys are added, locale files should stay synchronized.

### References

- `../planning-artifacts/epic-23.md`
- `../planning-artifacts/epic-23-31-execution-plan.md`
- `ERPnext-Validated-Research-Report.md`
- `.omc/research/erpnext-crm-sales-detailed.md`
- `.omc/research/gap-analysis.md`
- `.omc/research/review-gap-claims.md`
- `.omc/research/review-roadmap.md`
- `CLAUDE.md`

## Dev Agent Record

### Agent Model Used

GPT-5.4

### Debug Log References

- `cd /Users/changtom/Downloads/UltrERP/backend && uv run pytest tests/domains/crm/test_quotation_service.py tests/domains/crm/test_quotation_routes.py -q`
- `cd /Users/changtom/Downloads/UltrERP/backend && uv run pytest tests/domains/crm/test_routes.py tests/domains/crm/test_lead_service.py tests/domains/crm/test_opportunity_service.py tests/domains/crm/test_opportunity_routes.py tests/domains/crm/test_quotation_service.py tests/domains/crm/test_quotation_routes.py -q`
- `cd /Users/changtom/Downloads/UltrERP && pnpm exec vitest run src/tests/crm/CreateQuotationPage.test.tsx src/tests/crm/QuotationListPage.test.tsx src/tests/crm/QuotationDetailPage.test.tsx src/tests/crm/OpportunityDetailPage.test.tsx`
- `cd /Users/changtom/Downloads/UltrERP && pnpm exec vitest run src/tests/crm/CreateLeadPage.test.tsx src/tests/crm/LeadDetailPage.test.tsx src/tests/crm/LeadListPage.test.tsx src/tests/crm/CreateOpportunityPage.test.tsx src/tests/crm/OpportunityDetailPage.test.tsx src/tests/crm/OpportunityListPage.test.tsx src/tests/crm/CreateQuotationPage.test.tsx src/tests/crm/QuotationDetailPage.test.tsx src/tests/crm/QuotationListPage.test.tsx`

### Completion Notes List

- 2026-04-21: Drafted Story 23.3 from Epic 23 and the validated quotation research, keeping quotation as a formal pre-order commercial record with lifecycle, revision, loss, and auto-repeat metadata while deferring conversion to Story 23.4.
- 2026-04-21: Implemented a tenant-scoped CRM quotation record with dynamic party targeting, transaction and validity dates, base-currency totals, taxes, contact and address context, opportunity backlinking, amendment lineage, competitor and lost-reason capture, and auto-repeat-ready metadata without embedding sales-order, invoice, or GL writes.
- 2026-04-21: Added CRM quotation create/list/detail/revision UI, opportunity-detail handoff into prefilled quotation authoring, localized route and navigation wiring, and focused backend/frontend CRM regression coverage for Stories 23.1 through 23.3.

### File List

- `_bmad-output/implementation-artifacts/23-3-quotation-authoring-and-lifecycle.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `backend/app/main.py`
- `backend/domains/crm/models.py`
- `backend/domains/crm/routes.py`
- `backend/domains/crm/schemas.py`
- `backend/domains/crm/service.py`
- `backend/tests/domains/crm/test_quotation_routes.py`
- `backend/tests/domains/crm/test_quotation_service.py`
- `migrations/versions/4d6e7f8a9b0c_add_crm_quotations.py`
- `public/locales/en/common.json`
- `public/locales/zh-Hant/common.json`
- `src/App.tsx`
- `src/components/crm/QuotationForm.tsx`
- `src/components/crm/QuotationResultsTable.tsx`
- `src/domain/crm/types.ts`
- `src/lib/api/crm.ts`
- `src/lib/navigation.tsx`
- `src/lib/routes.ts`
- `src/lib/schemas/quotation.schema.ts`
- `src/pages/crm/CreateQuotationPage.tsx`
- `src/pages/crm/OpportunityDetailPage.tsx`
- `src/pages/crm/QuotationDetailPage.tsx`
- `src/pages/crm/QuotationListPage.tsx`
- `src/tests/crm/CreateQuotationPage.test.tsx`
- `src/tests/crm/OpportunityDetailPage.test.tsx`
- `src/tests/crm/QuotationDetailPage.test.tsx`
- `src/tests/crm/QuotationListPage.test.tsx`