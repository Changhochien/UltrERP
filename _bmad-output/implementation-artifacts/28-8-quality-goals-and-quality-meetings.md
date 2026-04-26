# Story 28.8: Quality Goals and Quality Meetings

**Status:** ready-for-dev

**Story ID:** 28.8

**Epic:** Epic 28 - Workforce, Contacts, and Service Desk Foundations

---

## Story

As a quality leader,
I want measurable quality goals and traceable quality meetings,
so that improvement work has explicit targets, review cadence, and accountable follow-up instead of manual spreadsheets and disconnected meeting notes.

---

## Problem Statement

UltrERP has no first-class way to define quality objectives, record periodic measurements, or capture meeting agenda and action outcomes against those objectives. Without a goal and meeting system, quality decisions stay outside the ERP and NCR or CAPA work loses the management-review layer needed for sustained improvement. Epic 28 needs lightweight but governed goals and meetings before later SPC and supplier-quality analytics try to explain trends without a management baseline.

## Solution

Add a quality-governance foundation that:

- creates `QualityGoal`, `QualityGoalObjective`, and `QualityGoalMeasurement` records for target-setting and periodic performance capture
- creates `QualityMeeting`, agenda, minute, and action-item records linked to goals, NCRs, and CAPAs under discussion
- keeps review cadence, trend visibility, and action ownership explicit without requiring a full scheduler or BI platform

Keep the first slice focused. Land goal setup, measurement capture, meeting records, and action tracking while deferring automatic recurring review-document generation, calendar sync, advanced BI suites, and external notification preference management.

## Acceptance Criteria

1. Given a quality manager defines a goal, when it is saved, then objective, metric, target, frequency, and responsible party are stored on a dedicated quality-goal model.
2. Given periodic measurements are recorded, when the goal detail is viewed, then the system shows progress and trend against the target using historical measurements instead of only the latest value.
3. Given a quality meeting is held, when agenda items, minutes, and action items are captured, then goals, NCRs, CAPAs, owners, and due dates remain linked and traceable from the meeting record.
4. Given action items or missed goals require follow-up, when owners review the quality workspace, then assignments and due-soon reminders are available through existing narrow delivery seams without requiring a new scheduling platform.

## Tasks / Subtasks

- [ ] Task 1: Add quality-goal, measurement, and meeting persistence. (AC: 1-4)
  - [ ] Add `QualityGoal`, `QualityGoalObjective`, `QualityGoalMeasurement`, `QualityMeeting`, agenda, minute, and action-item models under `backend/domains/quality/models.py`.
  - [ ] Store goal fields for owner, department or process scope, target, unit, frequency, status, and related procedure.
  - [ ] Store measurement history with measured value, measurement date, recorder, and optional comment.
  - [ ] Store meeting status, attendees, agenda items, minutes, and action owners plus explicit optional references to `quality_goal_id`, `ncr_id`, and `capa_action_id` instead of a generic polymorphic link table in the first slice.
  - [ ] Add the required Alembic migration under `migrations/versions/`.
- [ ] Task 2: Implement goal progress, review, and meeting services. (AC: 1-4)
  - [ ] Add service methods to create and update goals, record measurements, evaluate missed-target status, create meetings, and close action items.
  - [ ] Compute trend and summary status from measurement history rather than persisting redundant derived fields only.
  - [ ] Allow meeting items to reference goals, NCRs, and CAPAs explicitly.
- [ ] Task 3: Add action-item reminder and report seams. (AC: 2-4)
  - [ ] Expose due-soon and overdue action queries plus a thin reminder-delivery seam that can reuse the existing patterns in `backend/domains/line/notification.py` and `src/lib/desktop/notifications.ts` where configured.
  - [ ] Add summary payloads for goal achievement rate and meeting action-closure reporting.
- [ ] Task 4: Expose APIs and build the goals or meetings workspace. (AC: 1-4)
  - [ ] Add `backend/domains/quality/routes.py` endpoints for goal CRUD, measurement capture, meeting CRUD, and action updates.
  - [ ] Add frontend pages under `src/pages/quality/` for goals, meetings, and performance summary views.
  - [ ] Add `src/domain/quality/` hooks, chart-ready selectors, and forms plus `src/lib/api/quality.ts`.
- [ ] Task 5: Add focused tests and validation. (AC: 1-4)
  - [ ] Add backend tests for goal trend calculations, missed-target status, meeting linkage, and action reminder queries.
  - [ ] Add frontend tests for measurement entry, goal trend rendering, meeting minutes capture, and action-item status display.

## Dev Notes

### Context

- Epic 28 requires quality goals and meetings after procedures and alongside or after NCR/CAPA work.
- Vendored ERPNext quality-goal references show the useful upstream patterns for this slice: named goals, objective lines, monitoring frequency, and procedure linkage.
- Vendored ERPNext quality-meeting references show agenda and minutes as the baseline meeting structures, while Epic 28 extends them with attendees, owners, action items, and linked quality records.
- The current repo already has narrow notification seams in `backend/domains/line/notification.py` and `src/lib/desktop/notifications.ts`; reminder delivery should reuse those patterns instead of inventing a second notification system here.

### Architecture Compliance

- Keep quality goals and meetings inside the shared `backend/domains/quality/` domain rather than creating a second governance subsystem.
- Treat historical measurements as the source of truth for progress and trend; avoid collapsing them into a single mutable summary field.
- Reuse existing narrow notification seams for reminder delivery, and keep those deliveries non-blocking.
- Do not require a scheduler-generated `Quality Review` clone before the first goal or meeting slice is useful.

### Implementation Guidance

- Likely backend files:
  - `backend/domains/quality/models.py`
  - `backend/domains/quality/schemas.py`
  - `backend/domains/quality/service.py`
  - `backend/domains/quality/routes.py`
  - `backend/domains/quality/notifications.py`
  - `migrations/versions/*_quality_goals_and_meetings.py`
- Likely frontend files:
  - `src/lib/api/quality.ts`
  - `src/domain/quality/types.ts`
  - `src/domain/quality/hooks/useQualityGoals.ts`
  - `src/domain/quality/hooks/useQualityMeetings.ts`
  - `src/domain/quality/components/QualityGoalForm.tsx`
  - `src/domain/quality/components/QualityMeetingForm.tsx`
  - `src/pages/quality/QualityGoalsPage.tsx`
  - `src/pages/quality/QualityMeetingsPage.tsx`
  - `src/pages/quality/QualityPerformancePage.tsx`
- Reuse the existing frontend table and chart stack for trend and action-closure views rather than introducing a separate analytics toolkit.

### What NOT to implement

- Do **not** implement a full BI suite, calendar sync, or auto-generated periodic review documents in this story.
- Do **not** block goal or meeting updates on best-effort reminder delivery failures.
- Do **not** flatten all meeting history into one rich-text field when separate agenda, minutes, and action items are required for traceability.

### Testing Standards

- Include a regression proving trend and goal status are derived from measurement history rather than only the latest value.
- Include a regression proving meeting action items remain linked to owners and due dates after meeting closure.
- Keep frontend locale files synchronized if quality-governance labels are added.

## Dependencies & Related Stories

- **Depends on:** Story 28.7, Story 28.6
- **Related to:** Story 29.7 for SPC trend reuse, Story 29.8 for supplier-quality reporting

## References

- `../planning-artifacts/epic-28.md`
- `../planning-artifacts/epic-29.md`
- `reference/erpnext-develop/erpnext/quality_management/doctype/quality_goal/quality_goal.json`
- `reference/erpnext-develop/erpnext/quality_management/doctype/quality_meeting/quality_meeting.json`
- `https://docs.frappe.io/erpnext/quality_goal`
- `https://docs.frappe.io/erpnext/quality_meeting`
- `backend/domains/line/notification.py`
- `src/lib/desktop/notifications.ts`
- `CLAUDE.md`

---

## Dev Agent Record

**Status:** ready-for-dev
**Last Updated:** 2026-04-26

### Completion Notes List

- 2026-04-26: Story drafted from Epic 28 quality-governance scope, ERPNext quality goal and meeting references, and the current UltrERP notification and reporting seams.

### File List

- `_bmad-output/implementation-artifacts/28-8-quality-goals-and-quality-meetings.md`