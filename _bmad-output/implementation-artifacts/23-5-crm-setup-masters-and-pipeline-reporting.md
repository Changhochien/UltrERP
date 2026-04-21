# Story 23.5: CRM Setup Masters and Pipeline Reporting

Status: drafted

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

- [ ] Task 1: Add CRM setup masters and settings models. (AC: 1-2, 4)
  - [ ] Add Sales Stage, Territory, Customer Group, and CRM Settings models or equivalent master records.
  - [ ] Include CRM settings for lead duplication policy, contact-creation compatibility, default quotation validity, communication and comment carry-forward compatibility, and opportunity auto-close timing.
  - [ ] Keep Customer Group and Territory tree-capable so later customer and reporting flows can reuse them.
- [ ] Task 2: Wire setup masters into the CRM workflows. (AC: 1-2, 4)
  - [ ] Apply Territory defaults across leads and apply Territory plus Customer Group defaults across opportunities, quotations, and converted customer handoff.
  - [ ] Make default quotation validity available to quotation authoring without hardcoding a form-only fallback.
  - [ ] Keep duplication rules centralized so lead intake does not drift from admin policy.
  - [ ] Verify Stories 23.1 through 23.4 consume CRM settings and masters through stable integration points instead of forking settings logic per story.
- [ ] Task 3: Build the CRM setup UI and admin surfaces. (AC: 1-2)
  - [ ] Add admin-facing CRUD or single-record settings surfaces for the CRM masters and settings.
  - [ ] Keep the UI consistent with Epic 22 shared form and navigation primitives.
  - [ ] Surface the operational effect of key settings, especially duplicate behavior and quotation validity.
- [ ] Task 4: Add pipeline reporting views and filters. (AC: 3-4)
  - [ ] Add CRM reporting endpoints or projections for leads, opportunities, and quotations grouped and filtered by stage, status, territory, customer group, owner, lost reason, and UTM attribution.
  - [ ] Surface open pipeline, terminal outcomes, and conversion drop-off views in the CRM workspace.
  - [ ] Keep settings enforcement in workflow logic from Task 2 and use the reporting surface only to display configuration-aware outcomes and segment-level visibility.
  - [ ] Keep the first slice on manager-facing reporting, not on a full custom report builder.
- [ ] Task 5: Add focused tests and validation. (AC: 1-5)
  - [ ] Add backend tests for settings enforcement, master-data reuse, and pipeline segmentation.
  - [ ] Add frontend tests for CRM settings UI, master-data forms, and manager-facing filter/report views.
  - [ ] Validate that no transaction write logic from Stories 23.1 through 23.4 is duplicated here.

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

- Story draft only; implementation and validation commands not run yet.

### Completion Notes List

- 2026-04-21: Drafted Story 23.5 from Epic 23 and the validated CRM research, keeping setup masters and reporting read-oriented while standardizing sales stages, territory, customer group, CRM settings, and attribution-aware pipeline views.

### File List

- `_bmad-output/implementation-artifacts/23-5-crm-setup-masters-and-pipeline-reporting.md`