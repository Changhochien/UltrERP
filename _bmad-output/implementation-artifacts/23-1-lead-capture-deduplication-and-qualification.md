# Story 23.1: Lead Capture, Deduplication, and Qualification

Status: drafted

## Story

As a sales or business-development user,
I want to capture leads with qualification and attribution data while preventing avoidable duplicates,
so that UltrERP can manage prospects before customer creation without losing conversion context.

## Problem Statement

UltrERP currently jumps from customer master data straight into order workflows. The validated ERPnext research confirmed that this leaves a structural pre-sale gap: there is no dedicated Lead record, no qualification lifecycle, no UTM attribution on CRM records, and no dedupe path across prospects and existing customers. Epic 23 should start by establishing Lead as the first commercial intake record rather than pushing prospect handling into customer creation or order notes.

## Solution

Add a lead-management slice under the new CRM domain with:

- a Lead record that captures identity, organization, owner, qualification, source, and UTM context
- explicit lead statuses aligned to the validated ERPnext lifecycle
- dedupe checks against existing customers and previously captured leads before save or conversion
- a conversion path that promotes a lead into either an opportunity or customer without forcing quotation or order creation in the same story

The goal is to establish a reliable pre-customer commercial record and a clean handoff point for Story 23.2, not to implement the entire CRM stack in one slice.

## Acceptance Criteria

1. Given a sales user creates a lead, when the record is saved, then it stores core identity, communication, owner, territory, source, qualification, and UTM attribution fields in a dedicated CRM lead model.
2. Given a lead is viewed or edited, when its lifecycle changes, then the available statuses support the validated lead progression `lead -> open -> replied -> opportunity -> quotation -> converted` plus the alternate terminal states needed by the research (`lost quotation`, `interested`, `do not contact`).
3. Given a lead is being created or updated, when the business identity, email, or phone collides with an existing lead or customer, then the UI surfaces actionable reuse, review, or merge guidance instead of silently creating a duplicate.
4. Given CRM settings allow automatic contact creation later, when this story is implemented, then the lead model and service boundaries remain compatible with later shared-contact work but do not require Epic 28 to ship first.
5. Given a qualified lead should advance, when a user converts it, then the system can create an opportunity or customer while preserving attribution, owner, territory, qualification context, and status lineage.
6. Given this story is implemented, when the backend and frontend are reviewed, then no order-domain or quotation-domain write logic is introduced here beyond the lead-to-next-step handoff.

## Tasks / Subtasks

- [ ] Task 1: Add the lead domain model, schemas, and persistence contract. (AC: 1, 2, 4)
  - [ ] Create a CRM lead model under `backend/domains/crm/` with tenant-scoped identity, organization, owner, lifecycle, qualification, communication, and attribution fields.
  - [ ] Include the validated UTM fields (`utm_source`, `utm_medium`, `utm_campaign`, `utm_content`) and the qualification fields called out in research.
  - [ ] Keep the write model compatible with later shared contact records instead of embedding one-off conversion-only fields.
- [ ] Task 2: Implement lead CRUD services and lifecycle handling. (AC: 1, 2, 5)
  - [ ] Add create, list, detail, update, and lifecycle-transition service logic for leads.
  - [ ] Enforce the validated status set and the allowed progression rules.
  - [ ] Add conversion endpoints or commands for lead-to-opportunity and lead-to-customer handoff without pulling Story 23.2 or Story 23.3 logic forward.
  - [ ] Preserve conversion-safe status and qualification lineage so later CRM reporting can reconstruct how the lead advanced.
- [ ] Task 3: Add deduplication and review guidance. (AC: 3)
  - [ ] Check new and updated leads against existing leads and customers using business identity and primary contact channels where available.
  - [ ] Return structured duplicate candidates so the UI can guide reuse or review.
  - [ ] Keep the first slice on actionable review guidance rather than automatic merge automation.
- [ ] Task 4: Build the lead UI workspace and capture form. (AC: 1-3, 5)
  - [ ] Add lead list and detail surfaces under the new CRM area using Epic 22 breadcrumb, toast, date, and shared form primitives.
  - [ ] Add a lead form that captures the validated core fields, attribution, and qualification state.
  - [ ] Surface duplicate warnings and conversion actions clearly in the detail flow.
- [ ] Task 5: Add focused tests and validation. (AC: 1-6)
  - [ ] Add backend tests for lifecycle enforcement, dedupe detection, and conversion handoff.
  - [ ] Add frontend tests for lead creation, duplicate guidance, and conversion actions.
  - [ ] Validate that the touched code does not introduce quotation or order write behavior.

## Dev Notes

### Context

- The validated report identifies Lead as the first missing CRM record and confirms that ERPnext carries owner, territory, qualification, and UTM fields directly on the lead.
- The review corrected an earlier field-count overstatement: the implementation should focus on the real data-carrying fields, not ERPnext layout-break noise.
- This story should establish the first CRM write surface while staying pre-financial and independent from GL.

### Architecture Compliance

- Keep Lead as a dedicated CRM domain record; do not overload `customers` for prospect intake.
- Stay pre-financial. No GL posting, quotation pricing engine, or order creation belongs here.
- Keep the lead record compatible with future shared contact management, but do not block on Epic 28.
- Reuse Epic 22 UI primitives and shared form architecture rather than creating CRM-local patterns.

### Implementation Guidance

- Likely backend files:
  - `backend/domains/crm/models.py`
  - `backend/domains/crm/schemas.py`
  - `backend/domains/crm/service.py`
  - `backend/domains/crm/routes.py`
  - `backend/domains/crm/mcp.py` only if CRM read tooling is in scope for this slice
  - migrations under `migrations/versions/`
- Likely frontend files:
  - `src/domain/crm/` for page sections, hooks, and typed contracts
  - `src/lib/api/crm.ts`
  - route registration inside the existing app shell
- Dedupe should compare against both lead records and existing customer records before create or update.
- Conversion should preserve source attribution and status history even if the next record type is created in a later story.

### Testing Requirements

- Backend tests should cover tenant scoping, dedupe collisions, valid and invalid lifecycle transitions, and lead-to-next-step conversion handoff.
- Backend tests should explicitly cover status and qualification lineage preservation during lead conversion.
- Frontend tests should cover create flow, duplicate-warning UX, and status-transition visibility.
- If new translation keys are added, locale files should stay synchronized.

### References

- `../planning-artifacts/epic-23.md`
- `../planning-artifacts/epic-23-31-execution-plan.md`
- `ERPnext-Validated-Research-Report.md`
- `.omc/research/erpnext-crm-sales-detailed.md`
- `.omc/research/gap-analysis.md`
- `.omc/research/review-gap-claims.md`
- `CLAUDE.md`

## Dev Agent Record

### Agent Model Used

GPT-5.4

### Debug Log References

- Story draft only; implementation and validation commands not run yet.

### Completion Notes List

- 2026-04-21: Drafted Story 23.1 from Epic 23 and the validated CRM research, keeping Lead pre-financial, UTM-aware, dedupe-aware, and compatible with later shared-contact work.

### File List

- `_bmad-output/implementation-artifacts/23-1-lead-capture-deduplication-and-qualification.md`