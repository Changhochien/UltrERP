# Story 23.6: UTM Tracking and Marketing Attribution

Status: completed

## Story

As a sales manager or revenue operations user,
I want UTM attribution captured and preserved across the CRM-to-order flow,
so that lead sources and campaign influence remain traceable without relying on offline spreadsheets.

## Problem Statement

Epic 23 already introduces attribution-ready fields on lead, opportunity, quotation, and reporting surfaces, but the new stories need a single implementation slice that standardizes how UTM data is captured, inherited, and reported. The validated CRM research confirms ERPnext supports UTM tracking on Lead, Opportunity, Quotation, and Sales Order, with enablement controlled by settings and with attribution intended for pipeline analysis rather than a full marketing-automation engine. Without a dedicated story for that propagation contract, UTM data will remain inconsistent across conversion steps and revenue attribution will break at the order handoff.

## Solution

Add a UTM-attribution slice that:

- standardizes the supported UTM field set across lead, opportunity, quotation, and order flows
- preserves first-touch attribution through lead, opportunity, quotation, and order conversion boundaries
- extends the CRM reporting layer with attribution-specific segmentation for source, medium, campaign, and content performance

This story should make attribution data durable and reportable, not implement campaign automation, spend-led ROI accounting, or a full multi-touch attribution engine.

## Acceptance Criteria

1. Given UTM tracking is enabled, when a lead, opportunity, quotation, or order is created or converted, then the supported UTM fields are captured and exposed consistently across those records.
2. Given an opportunity is created from a lead or a quotation is created from a lead or opportunity, when the new document is generated, then the inherited UTM attribution is copied from the source record unless the user explicitly overrides it.
3. Given a quotation converts to an order, when the order is created, then the effective UTM attribution remains snapshotted on the order for downstream revenue attribution and audit.
4. Given a sales manager reviews CRM reporting, when they use attribution filters for source, medium, campaign, content, owner, territory, or stage, then lead volume, conversion counts, quotation counts, and ordered revenue are visible from stored attribution values without creating a separate analytics domain.
5. Given this story is implemented, when the touched code is reviewed, then no email-campaign automation, no spend-led campaign ROI accounting, and no full multi-touch attribution model is introduced in this slice.

## Tasks / Subtasks

- [x] Task 1: Standardize the UTM field contract. (AC: 1-3)
  - [x] Support one explicit UTM field set across lead, opportunity, quotation, and order: `utm_source`, `utm_medium`, `utm_campaign`, and `utm_content`.
  - [x] Reuse the setup and enablement controls from Story 23.5 rather than inventing a second UTM configuration path.
  - [x] Keep any future `utm_term` or custom attribution extensions out of scope for this first CRM slice unless later analytics work explicitly claims them.
- [x] Task 2: Implement attribution inheritance and override behavior. (AC: 1-3)
  - [x] Copy UTM values from lead to opportunity, lead to quotation, opportunity to quotation, quotation to order, and other supported Epic 23 handoff flows.
  - [x] Persist whether the effective UTM values came from a source document or a manual override when that distinction is needed for audit visibility.
  - [x] Keep inherited UTM values stable on downstream records after creation unless a user intentionally edits them before finalization.
- [x] Task 3: Extend CRM reporting with attribution segmentation. (AC: 3-4)
  - [x] Extend the Story 23.5 CRM reporting surface with attribution segments for lead volume, opportunity conversion, quotation conversion, and ordered revenue by UTM source, medium, campaign, and content.
  - [x] Support filtering by owner, territory, stage, and date range using stored CRM fields rather than heuristic joins.
  - [x] Keep this first slice on first-touch attribution and conversion visibility, not on standalone campaign dashboards, campaign-cost ROI, or marketing automation workflows.
- [x] Task 4: Build UI capture and visibility patterns. (AC: 1-4)
  - [x] Add UTM capture fields to the relevant CRM and order forms when tracking is enabled.
  - [x] Show inherited attribution clearly on detail views and conversion review screens.
  - [x] Reuse Epic 22 shared form, filter, table, and feedback primitives.
- [x] Task 5: Add focused tests and validation. (AC: 1-5)
  - [x] Add backend tests for UTM inheritance across supported conversions, order snapshot persistence, and attribution reporting filters.
  - [x] Add frontend tests for conditional UTM field visibility, inherited-value display, and manager-facing attribution views.
  - [x] Validate that no campaign-automation, cost-tracking, or multi-touch modeling work lands in this story.

## Dev Notes

### Context

- Epic 23 already established attribution-ready CRM records and reporting hooks.
- Story 23.5 owns setup masters and the baseline CRM reporting surface, so this story should extend that layer with attribution-specific filters and measures rather than recreate it.
- The validated research explicitly confirms UTM fields on Lead, Opportunity, Quotation, and Sales Order, enabled through settings.

### Architecture Compliance

- Keep UTM data as a lightweight attribution layer attached to CRM and order records.
- Preserve attribution across conversion boundaries without turning this into a generalized marketing platform.
- Keep order ownership in Epic 21 and use the order handoff only to preserve attribution values.
- Keep advanced attribution analytics additive for later epics.

### Implementation Guidance

- Likely backend files:
  - `backend/domains/crm/models.py`
  - `backend/domains/crm/schemas.py`
  - `backend/domains/crm/service.py`
  - quotation conversion and order handoff services from Stories 23.3 and 23.4
  - order-domain schemas or models only where Epic 23 hands off attribution snapshots
  - migrations under `migrations/versions/`
- Likely frontend files:
  - `src/domain/crm/` lead, opportunity, quotation, and reporting surfaces
  - order conversion review surfaces touched by Story 23.4
  - `src/lib/api/crm.ts` and order API clients as needed
- First-touch attribution should come from the originating CRM document and be copied forward into downstream records. If manual overrides are allowed, they should be explicit and visible rather than silently replacing source attribution.
- This slice should use stored attribution fields for reporting. Campaign spend, ROI, and multi-touch journey weighting require later dedicated analytics work and are out of scope here.

### Data Model Contract

- Lead, Opportunity, Quotation, and Order should converge on these nullable attribution fields:
  - `utm_source`
  - `utm_medium`
  - `utm_campaign`
  - `utm_content`
- Downstream records created from an upstream CRM source should retain the copied attribution snapshot even if the upstream record changes later.
- If audit metadata is stored for attribution inheritance, allowed origins should be explicit and lightweight, such as:
  - `source_document`
  - `manual_override`

### Testing Requirements

- Backend tests should cover lead-to-opportunity, lead-to-quotation, opportunity-to-quotation, and quotation-to-order attribution propagation.
- Frontend tests should cover enablement-gated field visibility and attribution display on detail and reporting screens.
- If new translation keys are added, locale files should stay synchronized.

### References

- `../planning-artifacts/epic-23.md`
- `../implementation-artifacts/23-4-quotation-to-order-conversion-and-commercial-handoff.md`
- `../implementation-artifacts/23-5-crm-setup-masters-and-pipeline-reporting.md`
- `ERPnext-Validated-Research-Report.md`
- `.omc/research/erpnext-crm-sales-detailed.md`
- `.omc/research/review-roadmap.md`
- `.omc/research/review-gap-claims.md`
- `.omc/research/gap-analysis.md`
- `CLAUDE.md`

## Dev Agent Record

### Agent Model Used

GPT-5.4

### Debug Log References

- `cd /Users/changtom/Downloads/UltrERP/backend && .venv/bin/python -m pytest tests/domains/crm/test_reporting_service.py tests/domains/orders/test_orders_api.py`
- `cd /Users/changtom/Downloads/UltrERP && pnpm test -- --run src/tests/crm/CRMPipelineReportPage.test.tsx src/tests/orders/OrderFormCustomerContext.test.tsx src/tests/orders/OrderDetailConfirmationUX.test.tsx`
- Review follow-up regression reruns reused the same backend target and the focused frontend pair `src/tests/crm/CRMPipelineReportPage.test.tsx` and `src/tests/orders/OrderFormCustomerContext.test.tsx` after code-review fixes.

### Completion Notes List

- Implemented typed order-side UTM exposure and snapshot normalization so quotation attribution remains auditable on orders without adding new order-table columns.
- Extended CRM reporting contracts, filters, and UI segmentation for UTM medium, campaign, and content, including ordered-revenue attribution sourced from downstream order lineage.
- Completed focused frontend visibility work for inherited order attribution and synchronized the new CRM reporting and order attribution strings across English and zh-Hant locales.
- Code-review follow-up fixes preserved ordered revenue inside opportunity and quotation report slices, allowed users to explicitly clear inherited order UTM values, and removed hard-coded English labels from the reporting page.
- Focused validation passed with `33 passed` on the backend Story 23.6 regression slice and targeted frontend Story 23.6 regression coverage passing for CRM reporting and order attribution flows.

### File List

- `_bmad-output/implementation-artifacts/23-6-utm-tracking-and-marketing-attribution.md`
- `backend/domains/crm/schemas.py`
- `backend/domains/crm/service.py`
- `backend/domains/orders/schemas.py`
- `backend/domains/orders/services.py`
- `backend/domains/orders/routes.py`
- `backend/tests/domains/crm/test_reporting_service.py`
- `backend/tests/domains/orders/test_orders_api.py`
- `public/locales/en/common.json`
- `public/locales/zh-Hant/common.json`
- `src/domain/crm/types.ts`
- `src/domain/orders/components/OrderDetail.tsx`
- `src/domain/orders/components/OrderForm.tsx`
- `src/domain/orders/types.ts`
- `src/lib/api/crm.ts`
- `src/lib/schemas/order.schema.ts`
- `src/pages/crm/CRMPipelineReportPage.tsx`
- `src/tests/crm/CRMPipelineReportPage.test.tsx`
- `src/tests/orders/OrderDetailConfirmationUX.test.tsx`
- `src/tests/orders/OrderFormCustomerContext.test.tsx`

## Change Log

- 2026-04-22: Implemented Story 23.6 UTM attribution propagation, reporting extensions, focused validations, and review-fix follow-up.
- 2026-04-22: Code-review follow-up fixed ordered revenue attribution inside opportunity and quotation slices, allowed explicit clearing of inherited order UTM values, and removed hard-coded English labels from the reporting page.
- 2026-04-22: Simplification review - new CRM domain modules (_lead.py, _pipeline.py, _setup.py) are well-structured with clear separation of concerns; verified with 88 backend tests and 327 frontend tests passing.
- 2026-04-22: Fixed 4 pre-existing lint errors by converting empty interfaces to type aliases (`CRMSettingsUpdatePayload`, `QuotationItemPayload`, `QuotationRevisionPayload`, `QuotationItemResponse`).