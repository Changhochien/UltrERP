# Story 23.5: CRM Setup Masters and Pipeline Reporting

Status: completed

## Story

As a sales manager or administrator,
I want CRM setup masters and a pipeline reporting surface,
so that the new lead, opportunity, and quotation records use consistent business configuration and can be reviewed by stage, territory, customer group, and attribution source.

## Problem Statement

Stories 23.1 through 23.4 create CRM transaction records, but without shared setup masters and reporting controls the pipeline remains inconsistent and difficult to govern. The validated research confirms that ERPnext relies on CRM Settings, Sales Stage, Territory, Customer Group, and attribution-ready records to support structured pipeline management. UltrERP needs the same foundation if the new CRM records are going to stay coherent across teams and reports.

## Solution

Add the lightweight CRM master and reporting layer that:

- defines sales stages and the key setup masters used by lead, opportunity, quotation, and converted customer records
- adds CRM settings for duplication, contact-creation compatibility, default quotation validity, and opportunity auto-close policy
- exposes a pipeline reporting surface for leads, opportunities, quotations, lost reasons, territory, customer group, and UTM slices
- keeps the setup layer compatible with later shared contact, engagement, and analytics work

This story should standardize CRM configuration and visibility, not create new core transaction behavior beyond what earlier Epic 23 stories already introduced.

## Acceptance Criteria

1. Given CRM administrators configure the system, when they manage sales stages, territories, customer groups, and CRM settings, then new lead, opportunity, and quotation records consume those masters consistently.
2. Given duplication, default quotation validity, or opportunity auto-close behavior is configured, when CRM records are created or updated, then the corresponding settings are available to the relevant workflows without requiring ad hoc per-form logic.
3. Given a sales manager reviews the pipeline, when they open the reporting surface, then they can segment open and terminal CRM records by stage, status, territory, customer group, owner, lost reason, and UTM attribution.
4. Given customer-facing records are converted from CRM, when customer group or territory defaults apply, then the downstream records preserve that business context without silently inventing new master data.
5. Given this story is implemented, when the touched code is reviewed, then it does not re-implement lead, opportunity, quotation, or order-domain transaction logic that belongs to earlier stories.

## Tasks / Subtasks

- [x] Task 1: Add CRM setup masters and settings models. (AC: 1-2, 4)
  - [x] Add Sales Stage, Territory, Customer Group, and CRM Settings models or equivalent master records.
  - [x] Include CRM settings for lead duplication policy, contact-creation compatibility, default quotation validity, communication and comment carry-forward compatibility, and opportunity auto-close timing.
  - [x] Keep Customer Group and Territory tree-capable so later customer and reporting flows can reuse them.
- [x] Task 2: Wire setup masters into the CRM workflows. (AC: 1-2, 4)
  - [x] Apply Territory defaults across leads and apply Territory plus Customer Group defaults across opportunities, quotations, and converted customer handoff.
  - [x] Make default quotation validity available to quotation authoring without hardcoding a form-only fallback.
  - [x] Keep duplication rules centralized so lead intake does not drift from admin policy.
  - [x] Verify Stories 23.1 through 23.4 consume CRM settings and masters through stable integration points instead of forking settings logic per story.
- [x] Task 3: Build the CRM setup UI and admin surfaces. (AC: 1-2)
  - [x] Add admin-facing CRUD or single-record settings surfaces for the CRM masters and settings.
  - [x] Keep the UI consistent with Epic 22 shared form and navigation primitives.
  - [x] Surface the operational effect of key settings, especially duplicate behavior and quotation validity.
- [x] Task 4: Add pipeline reporting views and filters. (AC: 3-4)
  - [x] Add CRM reporting endpoints or projections for leads, opportunities, and quotations grouped and filtered by stage, status, territory, customer group, owner, lost reason, and UTM attribution.
  - [x] Surface open pipeline, terminal outcomes, and conversion drop-off views in the CRM workspace.
  - [x] Keep settings enforcement in workflow logic from Task 2 and use the reporting surface only to display configuration-aware outcomes and segment-level visibility.
  - [x] Keep the first slice on manager-facing reporting, not on a full custom report builder.
- [x] Task 5: Add focused tests and validation. (AC: 1-5)
  - [x] Add backend tests for settings enforcement, master-data reuse, and pipeline segmentation.
  - [x] Add frontend tests for CRM settings UI, master-data forms, and manager-facing filter/report views.
  - [x] Validate that no transaction write logic from Stories 23.1 through 23.4 is duplicated here.

## Dev Notes

### Context

- The validated research explicitly calls out Sales Stage, Territory, Customer Group, UTM tracking, and CRM Settings as part of the CRM foundation.
- Review-roadmap identifies Customer Group and Territory trees as low-effort setup doctypes that should not be lost between Epic 23 planning and implementation.
- This story should stabilize configuration and reporting for the CRM transaction stories already defined.

### Architecture Compliance

- Keep setup masters and settings separate from the transaction stories they inform.
- Keep reporting read-oriented; do not rebuild core lead, opportunity, quotation, or order writes in this story.
- Maintain compatibility with later Epic 28 shared contacts and Epic 30 engagement work.
- Reuse Epic 22 form, breadcrumb, toast, and shared-table foundations.

### Implementation Guidance

- Likely backend files:
  - `backend/domains/crm/models.py`
  - `backend/domains/crm/schemas.py`
  - `backend/domains/crm/service.py`
  - `backend/domains/crm/routes.py`
  - migrations under `migrations/versions/`
- Likely frontend files:
  - `src/domain/crm/` setup, reporting, and manager-view components
  - `src/lib/api/crm.ts`
  - CRM navigation and route wiring
- Territory and Customer Group should remain tree-capable even if the first UI slice is simple.
- Pipeline reporting should reuse stored CRM attribution fields rather than deriving attribution heuristically later.

### Testing Requirements

- Backend tests should cover settings defaults, duplicate-policy enforcement, territory and customer-group master reuse, and pipeline filtering.
- Frontend tests should cover setup screens, filter interactions, and manager-facing pipeline summaries.
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

- `cd /Users/changtom/Downloads/UltrERP/backend && uv run pytest tests/domains/crm/test_lead_service.py tests/domains/crm/test_opportunity_service.py tests/domains/crm/test_quotation_service.py -q`
- `cd /Users/changtom/Downloads/UltrERP/backend && uv run pytest tests/domains/crm/test_reporting_service.py -q`
- `cd /Users/changtom/Downloads/UltrERP && pnpm test src/tests/crm/CreateLeadPage.test.tsx src/tests/crm/CreateOpportunityPage.test.tsx src/tests/crm/CreateQuotationPage.test.tsx src/tests/crm/LeadDetailPage.test.tsx src/tests/crm/OpportunityDetailPage.test.tsx src/tests/crm/QuotationDetailPage.test.tsx src/tests/crm/CRMSetupPage.test.tsx src/tests/crm/CRMPipelineReportPage.test.tsx`
- `cd /Users/changtom/Downloads/UltrERP && pnpm build`

### Completion Notes List

- Added tenant-scoped CRM settings, sales stages, territories, and customer groups on the backend, together with migrations, setup/reporting routes, and read-oriented pipeline aggregation.
- Centralized duplicate-policy enforcement, territory/customer-group validation, and settings-driven quotation validity so Stories 23.1 through 23.4 now consume shared CRM configuration instead of form-local defaults.
- Added a shared CRM setup-bundle hook, migrated lead/opportunity/quotation forms onto setup masters, and introduced dedicated CRM setup and pipeline-reporting pages with route and navigation wiring.
- Added focused backend coverage for settings/master enforcement and pipeline reporting, plus focused frontend coverage for the new CRM setup and reporting pages and the updated CRM create/detail flows.
- Focused validation passed with `31 passed` across the backend Story 23.5 CRM service/report suite and `19 passed` across the frontend CRM Story 23.5 slice. A broader `pnpm build` rerun still reports unrelated pre-existing TypeScript failures outside the CRM slice in customer, inventory, order, and payment files.

### File List

- `_bmad-output/implementation-artifacts/23-5-crm-setup-masters-and-pipeline-reporting.md`
- `backend/app/main.py`
- `backend/domains/crm/models.py`
- `backend/domains/crm/routes.py`
- `backend/domains/crm/schemas.py`
- `backend/domains/crm/service.py`
- `backend/tests/domains/crm/test_lead_service.py`
- `backend/tests/domains/crm/test_opportunity_service.py`
- `backend/tests/domains/crm/test_quotation_service.py`
- `backend/tests/domains/crm/test_reporting_service.py`
- `migrations/versions/6f7a8b9c0d1e_add_crm_settings.py`
- `migrations/versions/70819a2b3c4d_add_crm_setup_masters.py`
- `public/locales/en/common.json`
- `src/App.tsx`
- `src/components/crm/LeadForm.tsx`
- `src/components/crm/OpportunityForm.tsx`
- `src/components/crm/QuotationForm.tsx`
- `src/domain/crm/hooks/useCRMSetupBundle.ts`
- `src/domain/crm/types.ts`
- `src/lib/api/crm.ts`
- `src/lib/navigation.tsx`
- `src/lib/routes.ts`
- `src/pages/crm/CRMSetupPage.tsx`
- `src/pages/crm/CRMPipelineReportPage.tsx`
- `src/pages/crm/LeadDetailPage.tsx`
- `src/pages/crm/OpportunityDetailPage.tsx`
- `src/pages/crm/QuotationDetailPage.tsx`
- `src/tests/crm/CRMSetupPage.test.tsx`
- `src/tests/crm/CRMPipelineReportPage.test.tsx`
- `src/tests/crm/CreateLeadPage.test.tsx`
- `src/tests/crm/CreateOpportunityPage.test.tsx`
- `src/tests/crm/CreateQuotationPage.test.tsx`
- `src/tests/crm/LeadDetailPage.test.tsx`
- `src/tests/crm/OpportunityDetailPage.test.tsx`
- `src/tests/crm/QuotationDetailPage.test.tsx`