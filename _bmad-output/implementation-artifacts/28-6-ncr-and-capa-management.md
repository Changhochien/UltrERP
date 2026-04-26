# Story 28.6: NCR and CAPA Management

**Status:** ready-for-dev

**Story ID:** 28.6

**Epic:** Epic 28 - Workforce, Contacts, and Service Desk Foundations

---

## Story

As a quality manager or cross-functional investigator,
I want non-conformance and CAPA records with ownership, root-cause tracking, and verification,
so that product, supplier, inspection, and complaint problems move through a governed corrective workflow instead of ad hoc follow-up.

---

## Problem Statement

UltrERP has inventory and procurement foundations, but it does not yet have a governed way to record non-conformances, assign corrective actions, or prove that corrective and preventive work was effective. If inspections fail or customer complaints surface defects, teams currently have no first-class NCR or CAPA workflow, no due-date tracking, and no quality-specific closure criteria. Epic 28 needs an audit-friendly NCR and CAPA layer before later supplier scorecards, recall analysis, or quality reviews depend on undocumented corrective work.

## Solution

Add a quality-action foundation that:

- creates `NonConformanceReport` and CAPA action records with explicit ownership, due dates, and closure criteria
- records root-cause analysis, corrective actions, preventive actions, and effectiveness verification on a dedicated quality workflow
- preserves supplier linkage and action outcomes so later supplier scorecard work can consume NCR/CAPA history without scraping notes
- keeps inspection, issue, return, and supplier linkage optional so the same NCR model can be used before every upstream source system exists

Keep the first slice operational. Land NCR lifecycle, action assignment, verification, and due-date reminders while deferring full 8D workflows, supplier scorecards, recall orchestration, and deep document-attachment automation.

## Acceptance Criteria

1. Given a quality inspection, return, supplier issue, or customer complaint reveals a problem, when an NCR is created, then source linkage, defect details, affected item or quantity context, and investigation status are explicit.
2. Given an NCR is open, when investigators document root cause and assign corrective or preventive actions, then responsible owners, due dates, and action states are persisted on dedicated records instead of buried in notes.
3. Given a corrective action is assigned, when owners review their work, then assignment and due-soon reminders are available through a narrow notification seam without blocking the core workflow on a new notification platform.
4. Given an NCR is closed, when auditors review the record, then closure only occurs after linked actions are implemented, verified, and documented for effectiveness.
5. Given a supplier-related NCR exists, when CAPA work is tracked, then supplier linkage and action outcomes remain queryable so Epic 29.8 supplier scorecards can consume the same quality history.

## Tasks / Subtasks

- [ ] Task 1: Add NCR and CAPA persistence. (AC: 1-4)
  - [ ] Add `NonConformanceReport` plus action and verification models under `backend/domains/quality/models.py`.
  - [ ] Store source linkage fields for optional inspection, issue, supplier, return, product, and process references.
  - [ ] Store root-cause fields for structured 5-Whys text, fishbone notes or JSON, an explicit CAPA `action_type` of `corrective` or `preventive`, responsible owner, due date, implementation notes, and verification result.
  - [ ] Add the required Alembic migration under `migrations/versions/`.
- [ ] Task 2: Implement NCR lifecycle, action assignment, and verification services. (AC: 1-4)
  - [ ] Add service methods to create NCRs, assign actions, transition states, verify effectiveness, and close only when gating rules are satisfied.
  - [ ] Reuse `ApprovalRequest` or an equivalent explicit sign-off seam for quality-manager verification rather than inventing a parallel ad hoc approval pattern.
  - [ ] Preserve supplier linkage and action outcomes in queryable fields so later supplier-quality scorecards can reuse them directly.
  - [ ] Keep inspection and issue linkage optional so the quality workflow remains usable before every upstream integration is complete.
- [ ] Task 3: Add assignment and reminder delivery seams. (AC: 2-4)
  - [ ] Emit due-date and assignment events through a thin quality-notification seam that can reuse existing fire-and-forget patterns.
  - [ ] Keep reminder delivery non-blocking and auditable; failures must not roll back NCR updates.
- [ ] Task 4: Expose APIs and build the NCR workspace. (AC: 1-4)
  - [ ] Add `backend/domains/quality/routes.py` endpoints for NCR list, detail, action updates, verification, and closure.
  - [ ] Add frontend pages under `src/pages/quality/` for NCR queue, detail, and action tracking.
  - [ ] Add `src/domain/quality/` hooks, types, and forms plus `src/lib/api/quality.ts`.
- [ ] Task 5: Add focused tests and validation. (AC: 1-4)
  - [ ] Add backend tests for optional source linkage, closure gating, action verification, and non-blocking reminder delivery.
  - [ ] Add frontend tests for NCR creation, action assignment, status transitions, and verification display.

## Dev Notes

### Context

- Epic 28 requires NCR and CAPA management linked to quality inspections, returns, or customer complaints.
- Vendored ERPNext non-conformance references are simpler than this epic scope, so UltrERP should treat them as a baseline rather than a full parity target.
- The current repo already has narrow notification seams in `backend/domains/line/notification.py` and `src/lib/desktop/notifications.ts`; reminder delivery should reuse thin adapters like these rather than inventing a general notification platform.

### Architecture Compliance

- Implement NCR and CAPA inside the shared `backend/domains/quality/` domain used by Epic 28 quality stories and register it in `backend/app/main.py`.
- Reuse `backend/common/models/audit_log.py` for append-only mutation visibility and `backend/common/models/approval_request.py` for explicit verification or sign-off gates.
- Keep inspection linkage optional because Epic 29 quality-inspection records may land separately.
- Store fishbone and 5-Whys content as structured text or JSON data, not as a bespoke diagram editor.

### Implementation Guidance

- Likely backend files:
  - `backend/domains/quality/models.py`
  - `backend/domains/quality/schemas.py`
  - `backend/domains/quality/service.py`
  - `backend/domains/quality/routes.py`
  - `backend/domains/quality/notifications.py`
  - `backend/app/main.py`
  - `migrations/versions/*_quality_ncr_capa.py`
- Likely frontend files:
  - `src/lib/api/quality.ts`
  - `src/domain/quality/types.ts`
  - `src/domain/quality/hooks/useNcrs.ts`
  - `src/domain/quality/components/NcrForm.tsx`
  - `src/domain/quality/components/CapaActionTable.tsx`
  - `src/pages/quality/NcrListPage.tsx`
  - `src/pages/quality/NcrDetailPage.tsx`
- If reminder delivery is added in the web app, prefer explicit in-app plus desktop notifications first and keep channel expansion optional.

### What NOT to implement

- Do **not** implement full 8D problem-solving workflows, supplier scorecards, recall management, or campaign-grade notification preferences in this story.
- Do **not** make inspection linkage mandatory before Epic 29 records exist.
- Do **not** block NCR edits on best-effort reminder-delivery failures.

### Testing Standards

- Include a regression proving NCR closure is rejected while linked actions remain unverified.
- Include a regression proving reminder-delivery failures are logged but do not roll back quality transactions.
- Keep frontend locale files synchronized if quality labels are added.

## Dependencies & Related Stories

- **Depends on:** Story 28.7
- **Blocks:** Story 28.8
- **Related to:** Story 29.1 for inspection linkage, Story 29.8 for supplier-quality analytics

## References

- `../planning-artifacts/epic-28.md`
- `../planning-artifacts/epic-29.md`
- `reference/erpnext-develop/erpnext/quality_management/doctype/non_conformance/non_conformance.json`
- `https://docs.frappe.io/erpnext/non-conformance`
- `backend/common/models/audit_log.py`
- `backend/common/models/approval_request.py`
- `backend/domains/line/notification.py`
- `src/lib/desktop/notifications.ts`
- `CLAUDE.md`

---

## Dev Agent Record

**Status:** ready-for-dev
**Last Updated:** 2026-04-26

### Completion Notes List

- 2026-04-26: Story drafted from Epic 28 quality scope, ERPNext non-conformance guidance, and the current UltrERP audit, approval, and notification seams.

### File List

- `_bmad-output/implementation-artifacts/28-6-ncr-and-capa-management.md`