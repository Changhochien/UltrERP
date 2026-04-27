# Story 28.4: Issue Tracking and SLA Management

**Status:** ready-for-dev

**Story ID:** 28.4

**Epic:** Epic 28 - Workforce, Contacts, and Service Desk Foundations

---

## Story

As a service lead or support agent,
I want issues with assignment, priority, and SLA timing,
so that the service queue shows clear ownership, urgency, and overdue risk instead of unmanaged inbox work.

---

## Problem Statement

UltrERP has order, invoice, CRM, and messaging foundations, but it does not yet have a first-class service issue queue. Customer problems can be mentioned in freeform channels, yet there is no dedicated issue record, no owner and status workflow, and no policy-driven response or resolution timers. Epic 28 needs an operational issue and SLA foundation before portal tickets, warranty handoff, or service analytics reuse ad hoc conversations and spreadsheets.

## Solution

Add a service foundation that:

- creates `Issue` and `ServiceLevelAgreement` records with priority-based response and resolution rules
- supports assignment, status changes, first-response tracking, hold or pause behavior, and overdue visibility in the service queue
- reuses `HolidayList` plus support-hour windows so SLA timing is calendar-aware without requiring full workforce scheduling

Keep the first slice operational. Land manual issue creation, queue review, assignment, and SLA calculation while deferring inbound email ingestion, automated assignment rules, customer-thread portals, and omnichannel delivery orchestration.

## Acceptance Criteria

1. Given a support issue is logged, when the queue is viewed, then subject, customer or contact, owner, status, priority, and SLA countdown are visible on a dedicated issue record.
2. Given an issue changes state, when it moves into or out of a hold status, then SLA pause or resume behavior follows configured policy and total hold time remains traceable.
3. Given a response or resolution occurs, when managers review service performance, then a dedicated query/report surface can return first-response and resolution compliance from persisted timestamps rather than UI-only calculations.
4. Given later portal or warranty flows reuse issues, when those features arrive, then party linkage and SLA policy do not require a second service queue model.

## Tasks / Subtasks

- [ ] Task 1: Add issue and SLA persistence. (AC: 1-4)
  - [ ] Add `Issue`, `ServiceLevelAgreement`, and child-rule models under `backend/domains/issues/models.py`.
  - [ ] Store issue fields for subject, description, customer, contact, status, priority, assignee, first-response timestamps, resolution timestamps, hold start, and accumulated hold duration.
  - [ ] Store SLA fields for entity scope, a foreign key to the shared people-domain holiday list, and normalized `ServiceLevelWorkingWindow` rows keyed by weekday with start and end times, plus default priority, pause-on statuses, and per-priority response and resolution rules.
  - [ ] Add the required Alembic migration under `migrations/versions/`.
- [ ] Task 2: Implement issue workflow and SLA calculation services. (AC: 1-4)
  - [ ] Add service methods to create, update, assign, transition, respond, resolve, close, and reopen issues.
  - [ ] Calculate `response_by` and `resolution_by` using working hours plus holiday-list exclusions instead of flat wall-clock math.
  - [ ] Recalculate deadlines when a paused issue resumes and preserve total hold duration for reporting.
- [ ] Task 3: Expose APIs and reporting surfaces. (AC: 1-4)
  - [ ] Add `backend/domains/issues/routes.py` endpoints for list, detail, create, update, assignment, transition, and SLA policy CRUD.
  - [ ] Return queue-friendly summary fields and explicit SLA state such as on track, paused, due soon, or overdue.
  - [ ] Add a lightweight compliance-summary query surface for first-response and resolution SLA reporting.
- [ ] Task 4: Build the issue queue and detail UI in the frontend. (AC: 1-3)
  - [ ] Add `src/pages/issues/` pages for queue, detail, and SLA policy management.
  - [ ] Add `src/domain/issues/` hooks, types, and components plus `src/lib/api/issues.ts`.
  - [ ] Reuse shared table, badge, breadcrumb, and detail-shell patterns rather than inventing a service-specific layout system.
- [ ] Task 5: Add focused tests and validation. (AC: 1-4)
  - [ ] Add backend tests for deadline calculation across support windows and holidays, hold or resume behavior, first-response capture, and overdue state reporting.
  - [ ] Add frontend tests for queue filters, assignee changes, and SLA badge rendering.

## Dev Notes

### Context

- Epic 28 explicitly requires issue tracking plus SLA routing before Epic 30 portal tickets are opened to external users.
- Vendored ERPNext issue and SLA references show the operational fields that matter in this slice: issue status, priority, raised-by context, first response, resolution timestamps, pause-on statuses, holiday lists, and per-priority response or resolve rules.
- Story 28.1 holiday lists and Story 28.2 contacts are important upstream foundations for accurate SLA calculation and party linkage.

### Architecture Compliance

- Create a new `backend/domains/issues/` domain and register it in `backend/app/main.py`.
- Reuse customer and shared-contact identities instead of embedding contact text again inside the issue write model.
- Keep SLA calculation in deterministic service-layer functions so the frontend receives explicit countdown and state fields.
- Use holiday list plus support-hour windows for working-calendar logic; do not build full employee-shift scheduling in this story.
- Foreign-key the shared `HolidayList` model from the people domain rather than duplicating a second calendar master inside the issues domain.
- Model support hours as SLA-owned weekday window rows; date-specific exclusions belong in the shared holiday list rather than in another override table for this first slice.

### Implementation Guidance

- Likely backend files:
  - `backend/domains/issues/models.py`
  - `backend/domains/issues/schemas.py`
  - `backend/domains/issues/service.py`
  - `backend/domains/issues/routes.py`
  - `backend/app/main.py`
  - `migrations/versions/*_issues_and_sla_foundation.py`
- Likely frontend files:
  - `src/lib/api/issues.ts`
  - `src/domain/issues/types.ts`
  - `src/domain/issues/hooks/useIssues.ts`
  - `src/domain/issues/components/IssueForm.tsx`
  - `src/domain/issues/components/SlaBadge.tsx`
  - `src/pages/issues/IssueQueuePage.tsx`
  - `src/pages/issues/IssueDetailPage.tsx`
  - `src/pages/issues/SlaPoliciesPage.tsx`
- If due-soon highlighting is needed, derive it from persisted SLA timestamps and the current clock rather than storing a second unstable countdown field.

### What NOT to implement

- Do **not** implement inbound email-to-ticket ingestion, threaded mailbox sync, or customer-portal auth in this story.
- Do **not** build a generic assignment-rule engine or omnichannel campaign tooling here.
- Do **not** reduce SLA logic to flat duration math that ignores configured support windows and holidays.

### Testing Standards

- Include a regression proving hold statuses pause SLA timers and resume them with accumulated hold time preserved.
- Include a regression proving deadline calculation skips configured holidays.
- Keep frontend locale files synchronized if issue and SLA labels are added.

## Dependencies & Related Stories

- **Depends on:** Story 28.1, Story 28.2
- **Blocks:** Story 28.5, Story 30.1
- **Related to:** Story 29.5 for compliance reporting, Story 31.2 for later asset-service repair linkage

## References

- `../planning-artifacts/epic-28.md`
- `../planning-artifacts/epic-30.md`
- `reference/erpnext-develop/erpnext/support/doctype/issue/issue.json`
- `reference/erpnext-develop/erpnext/support/doctype/service_level_agreement/service_level_agreement.json`
- `https://docs.frappe.io/erpnext/issue`
- `https://docs.frappe.io/erpnext/service-level-agreement`
- `backend/app/main.py`
- `CLAUDE.md`

---

## Dev Agent Record

**Status:** ready-for-dev
**Last Updated:** 2026-04-26

### Completion Notes List

- 2026-04-26: Story drafted from Epic 28 service-desk scope, ERPNext issue and SLA references, and the current UltrERP auth, contact, and reporting seams.

### File List

- `_bmad-output/implementation-artifacts/28-4-issue-tracking-and-sla-management.md`