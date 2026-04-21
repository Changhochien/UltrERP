# Story 23.2: Opportunity Pipeline and Dynamic Party Linking

Status: done

## Story

As a sales user managing active deals,
I want opportunity records that can follow a lead, customer, or prospect through a stage-based pipeline,
so that UltrERP can track deal confidence, expected close, and commercial context before a quotation is issued.

## Problem Statement

Story 23.1 introduces Lead as a pre-customer intake record, but UltrERP still lacks a deal-level record for active pipeline work. The validated ERPnext research confirms that Opportunity is where party context, sales stage, probability, expected close, amount, and lost-reason analysis converge. Without it, sales forecasting and commercial follow-up remain trapped in notes or spreadsheets, and Story 23.3 has no stable handoff record for quotation creation.

## Solution

Add an opportunity slice under the CRM domain with:

- a dynamic party-link model that can point at a lead, customer, or prospect-compatible record
- stage, probability, expected-closing, amount, contact, and attribution fields
- explicit open, replied, quoted, converted, closed, and lost outcomes
- conversion and status-update seams that support Story 23.3 quotation creation without embedding quotation logic here

This story should establish opportunity as the canonical active-deal record, not as a substitute for quotation, order, or invoice workflows.

## Acceptance Criteria

1. Given a user creates an opportunity, when the record is saved, then it links to a party through a validated dynamic-party pattern that supports lead, customer, and prospect-compatible contexts.
2. Given an opportunity is edited, when its commercial metadata is updated, then sales stage, probability, expected close date, currency, amount, item context, territory, customer-group-compatible context, contact fields, and UTM attribution remain explicit and reportable.
3. Given an opportunity changes lifecycle state, when it is marked as replied, quoted, converted, closed, or lost, then the transition respects a defined status model aligned to the validated research.
4. Given an opportunity is declared lost, when the user closes it, then lost reasons, competitor context, and explanatory notes are captured without overwriting prior deal history.
5. Given a user prepares the next commercial step, when they initiate quotation handoff, then the opportunity exposes party, contact, item, amount, territory, attribution, and currency context Story 23.3 needs without embedding quotation pricing or tax write logic here.
6. Given this story is implemented, when the touched code is reviewed, then no quotation lifecycle, sales-order creation, or GL behavior is implemented inside the opportunity slice beyond explicit handoff seams.

## Tasks / Subtasks

- [x] Task 1: Add the opportunity model, schemas, and dynamic-party contract. (AC: 1-3)
  - [x] Create an opportunity model under `backend/domains/crm/` with explicit `opportunity_from` and `party_name` fields compatible with lead, customer, and prospect contexts.
  - [x] Add validated fields for status, sales stage, probability, expected closing, currency, opportunity amount, a computed or stored read-only base-amount field suitable for later Epic 25 currency work, territory, customer-group-compatible context, contact fields (`contact_person`, `contact_email`, `contact_mobile`, `job_title`), and UTM attribution.
  - [x] Add an opportunity items table or equivalent structured line list so quotation handoff does not require rekeying deal lines later.
  - [x] Keep the party-link contract explicit and typed rather than relying on unstructured generic metadata.
- [x] Task 2: Implement opportunity lifecycle and forecasting services. (AC: 2-4)
  - [x] Add create, list, detail, update, and lifecycle-transition service logic for opportunities.
  - [x] Enforce the validated state model `open -> quotation -> converted` with alternate `replied`, `closed`, and `lost` paths.
  - [x] Preserve stage, amount, and probability changes for reporting-friendly history.
- [x] Task 3: Add loss handling and competitor capture. (AC: 4)
  - [x] Add structured lost-reason support and competitor capture on lost opportunities.
  - [x] Keep the first slice on structured fields and notes instead of a full competitive-intelligence subsystem.
  - [x] Prevent silent closure that would discard why the deal was lost.
- [x] Task 4: Build the opportunity UI workspace and detail flow. (AC: 1-5)
  - [x] Add opportunity list, detail, and pipeline-oriented views inside the CRM area.
  - [x] Surface stage, probability, expected close, owner, territory, and dynamic-party context clearly in list and detail views.
  - [x] Add a clear quotation-handoff action that stops at the opportunity boundary unless Story 23.3 is available.
  - [x] Define the handoff contract explicitly so Story 23.3 receives party, contact, item, attribution, and currency context with a backlink to the opportunity.
- [x] Task 5: Add focused tests and validation. (AC: 1-6)
  - [x] Add backend tests for dynamic-party validation, valid and invalid lifecycle transitions, lost-reason capture, and quotation handoff readiness.
  - [x] Add frontend tests for opportunity create or edit, status updates, lost-deal capture, and pipeline visibility.
  - [x] Validate that no quotation or order write logic is implemented inside this story.

## Dev Notes

### Context

- The validated research confirms Opportunity is the active-deal record with dynamic-party linking, sales stage, probability, expected close, amount, and lost reasons.
- Opportunity remains pre-financial and does not require GL.
- Story 23.3 should consume opportunity context; Story 23.2 should not pre-implement quotation pricing or ordering logic.

### Architecture Compliance

- Keep opportunity in the CRM domain and separate from quotation and order ownership.
- Use a typed dynamic-party pattern instead of multiple duplicated foreign-key columns spread across the UI.
- Keep quotation handoff explicit and additive. This story should prepare data for Story 23.3, not absorb it.
- Reuse Epic 22 primitives for forms, toasts, breadcrumbs, and date handling.

### Implementation Guidance

- Likely backend files:
  - `backend/domains/crm/models.py`
  - `backend/domains/crm/schemas.py`
  - `backend/domains/crm/service.py`
  - `backend/domains/crm/routes.py`
  - migrations under `migrations/versions/`
- Likely frontend files:
  - `src/domain/crm/` opportunity components, hooks, and types
  - `src/lib/api/crm.ts`
  - CRM route registration and navigation wiring
- Preserve both transaction currency and base-amount-ready fields at the model seam, but keep full cross-currency behavior deferred to Epic 25.
- The base-amount field in this story is only for read-model and handoff clarity; full cross-currency behavior and broader commercial currency rollout stay deferred to Epic 25.
- Contact linkage should be compatible with later shared-contact work in Epic 28, but this story may carry interim explicit contact fields if the shared contact record is not ready yet.
- If Prospect is not fully implemented in the first CRM slice, keep the party-link contract prospect-compatible without forcing the full Prospect UI to ship in this story.

### Testing Requirements

- Backend tests should cover tenant scoping, dynamic-party validation, lifecycle transitions, lost-deal capture, and quotation-handoff readiness.
- Frontend tests should cover create/edit flow, status updates, and pipeline visibility by stage.
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

- `cd /Users/changtom/Downloads/UltrERP/backend && uv run pytest tests/domains/crm/test_opportunity_service.py tests/domains/crm/test_opportunity_routes.py -q`
- `cd /Users/changtom/Downloads/UltrERP && pnpm test -- src/tests/crm/CreateOpportunityPage.test.tsx src/tests/crm/OpportunityDetailPage.test.tsx src/tests/crm/OpportunityListPage.test.tsx`
- `cd /Users/changtom/Downloads/UltrERP/backend && uv run pytest tests/domains/crm/test_lead_service.py tests/domains/crm/test_routes.py tests/domains/crm/test_opportunity_service.py tests/domains/crm/test_opportunity_routes.py -q`
- `cd /Users/changtom/Downloads/UltrERP && pnpm test -- src/tests/crm/CreateLeadPage.test.tsx src/tests/crm/LeadDetailPage.test.tsx src/tests/crm/LeadListPage.test.tsx src/tests/crm/CreateOpportunityPage.test.tsx src/tests/crm/OpportunityDetailPage.test.tsx src/tests/crm/OpportunityListPage.test.tsx`

### Completion Notes List

- 2026-04-21: Drafted Story 23.2 from Epic 23 and the validated CRM research, keeping Opportunity pre-financial, dynamic-party-aware, forecast-friendly, and cleanly separated from later quotation and order writes.
- 2026-04-21: Implemented the CRM opportunity backend slice with tenant-scoped opportunity persistence, typed lead/customer/prospect party validation, forecast fields, structured line items, lost-reason capture, and quotation-handoff context that stops before quotation writes.
- 2026-04-21: Added the opportunity frontend workspace with create/list/detail flows, a pipeline snapshot, quotation-handoff preview, and a lead-detail bridge into prefilled opportunity creation, then validated the combined lead and opportunity CRM regression suite.

### File List

- `migrations/versions/3b2d4f5e6a7b_add_crm_opportunities.py`
- `backend/app/main.py`
- `backend/domains/crm/models.py`
- `backend/domains/crm/schemas.py`
- `backend/domains/crm/service.py`
- `backend/domains/crm/routes.py`
- `backend/tests/domains/crm/test_opportunity_service.py`
- `backend/tests/domains/crm/test_opportunity_routes.py`
- `src/App.tsx`
- `src/components/crm/OpportunityForm.tsx`
- `src/components/crm/OpportunityPipelineSummary.tsx`
- `src/components/crm/OpportunityResultsTable.tsx`
- `src/domain/crm/types.ts`
- `src/lib/api/crm.ts`
- `src/lib/navigation.tsx`
- `src/lib/routes.ts`
- `src/lib/schemas/opportunity.schema.ts`
- `src/pages/crm/CreateOpportunityPage.tsx`
- `src/pages/crm/LeadDetailPage.tsx`
- `src/pages/crm/OpportunityDetailPage.tsx`
- `src/pages/crm/OpportunityListPage.tsx`
- `src/tests/crm/CreateOpportunityPage.test.tsx`
- `src/tests/crm/OpportunityDetailPage.test.tsx`
- `src/tests/crm/OpportunityListPage.test.tsx`
- `public/locales/en/common.json`
- `_bmad-output/implementation-artifacts/23-2-opportunity-pipeline-and-dynamic-party-linking.md`