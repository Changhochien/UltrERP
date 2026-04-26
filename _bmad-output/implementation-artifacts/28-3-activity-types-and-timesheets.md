# Story 28.3: Activity Types and Timesheets

**Status:** ready-for-dev

**Story ID:** 28.3

**Epic:** Epic 28 - Workforce, Contacts, and Service Desk Foundations

---

## Story

As a manager or staff member,
I want standardized activity types and reusable timesheets linked to employees and business work,
so that UltrERP can track labor consistently for service, project, and future costing workflows.

---

## Problem Statement

UltrERP has no shared labor-capture model today. Work time can be discussed inside tickets or handled outside the system, but there is no reusable activity-type master, no line-item time entry, and no review surface that future service costing or project reporting can trust. Epic 28 needs a timesheet model that works before finance or project parity arrives, otherwise later billing and staffing work will inherit inconsistent labor data.

## Solution

Add a timesheet foundation that:

- creates tenant-scoped `ActivityType`, `Timesheet`, and `TimesheetEntry` records under a dedicated timesheets domain
- links time entries to employees and optionally to supported business objects such as issues or future project or work references
- captures duration, billable intent, and optional costing or billing hooks without pulling invoicing or payroll into the first slice

Keep the first slice practical. Land manual entry, submission, review, and filtering while deferring timer-heavy UX, salary-slip generation, invoice creation, and full project-task parity.

## Acceptance Criteria

1. Given a staff member logs work, when a timesheet entry is saved, then employee, activity type, start or end time, duration, and optional linked business object are captured consistently on a dedicated timesheet model.
2. Given a manager reviews labor, when they filter by employee, activity type, status, or linked record, then the review view returns matching timesheet entries and totals.
3. Given later costing or billing work lands, when it reuses timesheets, then the model already exposes billable intent plus nullable costing or billing fields without requiring a schema rewrite.
4. Given a timesheet moves through `draft -> submitted -> approved/rejected`, when historical entries are reviewed, then the labor record remains traceable even if the employee later becomes inactive.

## Tasks / Subtasks

- [ ] Task 1: Add activity-type and timesheet persistence. (AC: 1-4)
  - [ ] Add `ActivityType`, `Timesheet`, and `TimesheetEntry` ORM models under `backend/domains/timesheets/models.py`.
  - [ ] Store activity defaults for optional costing and billing rates plus an active flag.
  - [ ] Store timesheet header status as `draft`, `submitted`, `approved`, or `rejected` and per-entry fields for activity type, from and to time, duration minutes, note, billable flag, and a validated `reference_type` plus `reference_id` pair that initially allows `issue` and can extend later without schema churn.
  - [ ] Add the required Alembic migration under `migrations/versions/`.
- [ ] Task 2: Implement timesheet entry, submit, and review services. (AC: 1-4)
  - [ ] Add service methods to create, edit, submit, approve, reject, and list timesheets.
  - [ ] Recalculate totals from line items instead of trusting client-supplied aggregates.
  - [ ] Keep approval manager-driven; submission must not auto-approve the timesheet.
  - [ ] Validate supported reference targets explicitly so the model stays reusable without becoming a freeform polymorphic sink.
- [ ] Task 3: Expose APIs and review filters. (AC: 1-4)
  - [ ] Add `backend/domains/timesheets/routes.py` endpoints for list, detail, create, update, submit, and review actions.
  - [ ] Return employee, activity, and linked-record summaries needed for manager review pages.
- [ ] Task 4: Build timesheet capture and review surfaces in the frontend. (AC: 1-3)
  - [ ] Add `src/pages/timesheets/` pages for entry list, detail, and manager review.
  - [ ] Add `src/domain/timesheets/` hooks, types, and form components plus `src/lib/api/timesheets.ts`.
  - [ ] Reuse existing table, date-input, and detail-shell patterns rather than inventing a bespoke time-tracking workspace.
- [ ] Task 5: Add focused tests and validation. (AC: 1-4)
  - [ ] Add backend tests for total recalculation, invalid reference targets, submit or approve transitions, and employee-inactive history handling.
  - [ ] Add frontend tests for entry creation, manager filtering, and review-state transitions.

## Dev Notes

### Context

- Epic 28 requires activity types, timesheets, and future costing compatibility without pulling finance or payroll depth forward.
- Vendored ERPNext references show a header-level timesheet with line items, optional billing/costing amounts, and a dedicated activity-type master.
- Employee records from Story 28.1 are a prerequisite for reliable labor ownership and filtering.

### Architecture Compliance

- Create a new `backend/domains/timesheets/` domain and register it in `backend/app/main.py`.
- Reuse `Employee` from Story 28.1; do not attach timesheets directly to bare auth users.
- Keep timesheet target linkage explicit through a validated allowlist that starts with `issue` and can later add project or service record types without domain-specific nullable columns for every future use case.
- Keep costing and billing fields nullable and informational in this slice; do not wire them to invoices or payroll yet.

### Implementation Guidance

- Likely backend files:
  - `backend/domains/timesheets/models.py`
  - `backend/domains/timesheets/schemas.py`
  - `backend/domains/timesheets/service.py`
  - `backend/domains/timesheets/routes.py`
  - `backend/app/main.py`
  - `migrations/versions/*_timesheets_foundation.py`
- Likely frontend files:
  - `src/lib/api/timesheets.ts`
  - `src/domain/timesheets/types.ts`
  - `src/domain/timesheets/hooks/useTimesheets.ts`
  - `src/domain/timesheets/components/TimesheetForm.tsx`
  - `src/pages/timesheets/TimesheetListPage.tsx`
  - `src/pages/timesheets/TimesheetDetailPage.tsx`
  - `src/pages/timesheets/TimesheetReviewPage.tsx`
- If timer UX is desired later, treat it as a frontend enhancement on top of the same entry contract rather than as a different persistence model.

### What NOT to implement

- Do **not** implement payroll payout, sales-invoice generation, or salary-slip linkage in this story.
- Do **not** implement a desktop timer daemon or deep project-task integration if the supporting domains are not already present.
- Do **not** let the client persist arbitrary totals without backend recomputation.

### Testing Standards

- Include a regression proving totals are recomputed from entries and not trusted from the request payload.
- Include a regression proving unsupported linked record types are rejected cleanly.
- Keep frontend locale files synchronized if new timesheet labels are added.

## Dependencies & Related Stories

- **Depends on:** Story 28.1
- **Related to:** Story 28.4 for issue linkage, Story 31.2 for future service-maintenance costing

## References

- `../planning-artifacts/epic-28.md`
- `reference/erpnext-develop/erpnext/projects/doctype/timesheet/timesheet.json`
- `reference/erpnext-develop/erpnext/projects/doctype/activity_type/activity_type.json`
- `https://docs.frappe.io/erpnext/timesheets`
- `backend/app/main.py`
- `src/App.tsx`
- `CLAUDE.md`

---

## Dev Agent Record

**Status:** ready-for-dev
**Last Updated:** 2026-04-26

### Completion Notes List

- 2026-04-26: Story drafted from Epic 28 timesheet scope, ERPNext time-tracking references, and the current UltrERP list/detail and service-ready data patterns.

### File List

- `_bmad-output/implementation-artifacts/28-3-activity-types-and-timesheets.md`