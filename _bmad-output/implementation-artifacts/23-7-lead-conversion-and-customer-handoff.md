# Story 23.7: Lead Conversion and Customer Handoff

Status: completed

## Story

As a sales user,
I want a controlled lead-conversion workflow,
so that qualified leads can become customers, opportunities, and quotations without re-entry or broken historical lineage.

## Problem Statement

Epic 23 already establishes lead intake, opportunity linking, quotation authoring, and order handoff, but users still need a deliberate conversion workflow that turns a qualified lead into downstream records safely. The validated CRM research confirms ERPnext supports `make_customer`, `make_opportunity`, and `make_quotation` flows from Lead, while UltrERP already has customer master fields for billing address and primary contact data. Without a dedicated conversion slice, users will either retype customer data manually or create inconsistent downstream records with weak historical traceability.

## Solution

Add a lead-conversion slice that:

- orchestrates lead-to-customer, lead-to-opportunity, and lead-to-quotation handoff from one controlled workflow
- maps current lead contact and address data into the existing customer master fields that UltrERP already owns today
- preserves the lead as a historical CRM record with clear converted-state lineage to the created downstream records

This story should make lead conversion reliable and auditable, not introduce a full shared contacts platform or replace the ownership boundaries of existing customer, opportunity, or quotation domains.

## Acceptance Criteria

1. Given a lead is qualified for conversion, when a user runs the conversion workflow, then they can create a customer, an opportunity, a quotation, or an allowed combination without re-entering the core party and contact data.
2. Given a lead converts to a customer, when the customer is created, then the lead's company, contact, and address data populate the current customer master fields while preserving compatibility with later shared-contact work.
3. Given a lead converts to an opportunity or quotation, when the downstream record is created, then the original lead remains linked and historically visible on the resulting record.
4. Given a conversion is partially successful, when one selected downstream step fails, then successful conversions remain linked, failed steps return explicit errors, and the lead is not left in an ambiguous converted state.
5. Given sales leadership reviews conversion performance, when they open CRM reporting, then conversion counts, time-to-conversion, conversion path, and conversion source are reportable from stored lead lineage.
6. Given this story is implemented, when the touched code is reviewed, then it does not replace the current customer domain, does not move shared-contact ownership ahead of Epic 28, and does not duplicate quotation or opportunity logic already owned by Stories 23.2 through 23.4.

## Tasks / Subtasks

- [x] Task 1: Define the lead conversion contract. (AC: 1-4)
  - [x] Add an explicit conversion workflow that supports customer-only, opportunity-only, quotation-only, or allowed combined conversions from a qualified lead.
  - [x] Persist conversion-result metadata on the lead so created downstream record ids, timestamps, and conversion path stay historically traceable.
  - [x] Persist an explicit conversion state on the lead, such as `not_converted`, `partially_converted`, or `converted`, so partial outcomes are visible without ambiguity.
  - [x] Keep conversion idempotent enough to prevent duplicate downstream records from repeated clicks or retries.
- [x] Task 2: Implement customer handoff mapping. (AC: 1-4)
  - [x] Map lead company and primary contact data into the current customer fields such as `company_name`, `billing_address`, `contact_name`, `contact_phone`, and `contact_email`.
  - [x] Reuse dedupe and reuse guidance from Story 23.1 so conversion can link to an existing customer when appropriate instead of blindly creating duplicates.
  - [x] Preserve lead-origin metadata on the customer or in conversion lineage without making the customer domain subordinate to CRM.
- [x] Task 3: Implement opportunity and quotation conversion flows. (AC: 1, 3-4)
  - [x] Reuse Story 23.2 opportunity contracts and Story 23.3 quotation contracts when a lead is converted into those records.
  - [x] Carry forward qualification, territory, customer-group context, UTM attribution, and relevant contact details during conversion.
  - [x] Keep the created opportunity or quotation linked back to the source lead for detail views and reporting.
- [x] Task 4: Add conversion UI and review surfaces. (AC: 1-5)
  - [x] Add a lead conversion action with an explicit review step showing which downstream records will be created or reused.
  - [x] Surface conversion outcomes, linked records, and partial-failure errors clearly in the CRM UI.
  - [x] Reuse Epic 22 shared form, modal, feedback, and status-display primitives.
- [x] Task 5: Extend reporting and validation. (AC: 4-6)
  - [x] Extend CRM reporting with conversion-path and time-to-conversion measures using stored lead lineage.
  - [x] Add backend tests for customer mapping, downstream linkage, partial failures, retry safety, and reuse of existing customers.
  - [x] Add frontend tests for conversion review, successful conversion display, and partial-failure feedback.
  - [x] Validate that no premature shared-contact platform or duplicated downstream transaction logic lands in this story.

## Dev Notes

### Context

- The validated CRM research explicitly confirms ERPnext lead conversion flows for customer, opportunity, and quotation.
- UltrERP already stores customer billing and primary contact data directly on the customer master, so this story can populate those current fields without waiting for Epic 28 shared contacts.
- Story 23.1 already owns lead deduplication and Story 23.4 owns quotation-to-order handoff, so this story should stay focused on lead conversion orchestration.

### Architecture Compliance

- Keep the lead as the historical pre-customer record even after conversion.
- Use the existing customer master as the immediate handoff target instead of inventing a parallel prospect or contact store.
- Keep downstream opportunity and quotation creation owned by their existing story contracts.
- Make any later shared-contact extraction additive by preserving conversion lineage rather than baking in one-off CRM-only coupling.

### Implementation Guidance

- Likely backend files:
  - `backend/domains/crm/models.py`
  - `backend/domains/crm/schemas.py`
  - `backend/domains/crm/service.py`
  - `backend/domains/customers/models.py`
  - `backend/domains/customers/schemas.py`
  - customer service entry points used for create or reuse behavior
  - migrations under `migrations/versions/`
- Likely frontend files:
  - `src/domain/crm/` lead detail and conversion-review surfaces
  - customer selection or reuse UI touched by conversion
  - `src/lib/api/crm.ts` and customer API clients as needed
- Conversion should be explicit about which records are created versus reused. If a customer already exists, the workflow should link the lead to that customer instead of creating a duplicate.
- Partial conversion failures should leave an honest result: successful child records remain linked, failed steps remain visible, and the lead status should reflect the exact outcome rather than claiming a full conversion.

### Data Model Contract

- Lead conversion lineage should record at minimum:
  - `conversion_state`
  - `converted_at`
  - `converted_by`
  - `conversion_path`
  - nullable references to created or linked customer, opportunity, and quotation records
- The lead should retain its own record and move into a converted-compatible status rather than being deleted or merged away.
- Customer handoff in this phase should target the current customer master fields:
  - `company_name`
  - `billing_address`
  - `contact_name`
  - `contact_phone`
  - `contact_email`

### Testing Requirements

- Backend tests should cover new-customer creation, existing-customer reuse, lead-to-opportunity conversion, lead-to-quotation conversion, and partial failure handling.
- Frontend tests should cover conversion review choices, linked-record display, and conversion-error clarity.
- If new translation keys are added, locale files should stay synchronized.

### References

- `../planning-artifacts/epic-23.md`
- `../implementation-artifacts/23-1-lead-capture-deduplication-and-qualification.md`
- `../implementation-artifacts/23-2-opportunity-pipeline-and-dynamic-party-linking.md`
- `../implementation-artifacts/23-3-quotation-authoring-and-lifecycle.md`
- `../implementation-artifacts/23-4-quotation-to-order-conversion-and-commercial-handoff.md`
- `ERPnext-Validated-Research-Report.md`
- `.omc/research/erpnext-crm-sales-detailed.md`
- `.omc/research/review-roadmap.md`
- `.omc/research/review-gap-claims.md`
- `.omc/research/gap-analysis.md`
- `backend/domains/customers/models.py`
- `backend/domains/crm/schemas.py`
- `CLAUDE.md`

## Dev Agent Record

### Agent Model Used

GPT-5.4

### Debug Log References

- `cd /Users/changtom/Downloads/UltrERP/backend && .venv/bin/python -m pytest tests/domains/crm/test_lead_service.py tests/domains/crm/test_routes.py`
- `cd /Users/changtom/Downloads/UltrERP && pnpm test -- --run src/tests/crm/LeadDetailPage.test.tsx`
- `cd /Users/changtom/Downloads/UltrERP && pnpm test -- --run src/tests/crm/CreateQuotationPage.test.tsx`
- `cd /Users/changtom/Downloads/UltrERP/backend && .venv/bin/python -m pytest tests/domains/crm/test_reporting_service.py`
- `cd /Users/changtom/Downloads/UltrERP && pnpm test -- --run src/tests/crm/CRMPipelineReportPage.test.tsx`
- `cd /Users/changtom/Downloads/UltrERP && backend/.venv/bin/python -m alembic -c migrations/alembic.ini upgrade head`

### Completion Notes List

- Implemented a controlled lead conversion workflow that records explicit customer, opportunity, and quotation lineage on the lead while preserving partial-success outcomes and idempotent reuse behavior.
- Added lead-detail conversion planning and conversion summary UI, plus lead-based quotation prefill so downstream authoring reuses existing Story 23.2 and 23.3 seams instead of duplicating them.
- Extended CRM pipeline reporting with conversion counts, average time to conversion, conversion path grouping, and conversion source grouping sourced from stored lead lineage.
- Added the Alembic migration for persisted lead conversion lineage fields and revalidated the focused backend/frontend Story 23.7 slices after review fixes.

### File List

- `_bmad-output/implementation-artifacts/23-7-lead-conversion-and-customer-handoff.md`
- `backend/domains/crm/_pipeline.py`
- `backend/domains/crm/models.py`
- `backend/domains/crm/routes.py`
- `backend/domains/crm/schemas.py`
- `backend/domains/crm/service.py`
- `backend/tests/domains/crm/test_lead_service.py`
- `backend/tests/domains/crm/test_opportunity_service.py`
- `backend/tests/domains/crm/test_reporting_service.py`
- `backend/tests/domains/crm/test_routes.py`
- `migrations/versions/7b9d2c4e6f1a_add_lead_conversion_lineage.py`
- `public/locales/en/common.json`
- `public/locales/zh-Hant/common.json`
- `src/domain/crm/types.ts`
- `src/lib/api/crm.ts`
- `src/pages/crm/CRMPipelineReportPage.tsx`
- `src/pages/crm/CreateQuotationPage.tsx`
- `src/pages/crm/LeadDetailPage.tsx`
- `src/tests/crm/CRMPipelineReportPage.test.tsx`
- `src/tests/crm/CreateQuotationPage.test.tsx`
- `src/tests/crm/LeadDetailPage.test.tsx`

## Change Log

- 2026-04-22: Implemented Story 23.7 lead conversion orchestration, reporting extensions, migration, focused validations, and review-fix follow-up.
- 2026-04-22: Simplification review - code structure is well-organized; verified with 88 backend tests and 327 frontend tests passing.
- 2026-04-22: Fixed 4 pre-existing lint errors by converting empty interfaces to type aliases (`CRMSettingsUpdatePayload`, `QuotationItemPayload`, `QuotationRevisionPayload`, `QuotationItemResponse`).