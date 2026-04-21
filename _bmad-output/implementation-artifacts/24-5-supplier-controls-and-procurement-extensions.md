# Story 24.5: Supplier Controls and Procurement Extensions

Status: drafted

## Story

As a procurement lead,
I want supplier hold controls, score-based procurement warnings, and stable extension hooks on procurement records,
so that buyers can respect supplier policy and later procurement capabilities can build on the same document chain without retrofit work.

## Problem Statement

Stories 24.1 through 24.4 introduce procurement transactions and lineage, but procurement policy still needs supplier-level controls. The validated ERPnext research confirms that supplier hold state and supplier scorecard standing can warn or block RFQ and PO workflows, while later procurement work such as blanket orders or landed-cost allocation depends on stable reference hooks already being present on the core purchase documents. UltrERP's current supplier model is intentionally light and does not yet include these controls or extension points.

## Solution

Add a supplier-control and procurement-extension slice that:

- extends supplier records with procurement hold state and scorecard-compatible policy fields
- surfaces warning or blocking behavior in RFQ and PO authoring based on supplier control outcomes
- adds contract-ready and extension-ready references on procurement records for later blanket-order and landed-cost work
- exposes procurement performance reporting such as quote turnaround and award outcomes

This story should add policy controls and extension seams, not implement blanket orders, landed-cost allocation, or a full supplier-portal program.

## Acceptance Criteria

1. Given a supplier is blocked, on hold, or released on a future date, when a buyer authors an RFQ or PO, then the relevant warning or blocking behavior is enforced explicitly.
2. Given supplier score or standing falls into a warning or blocking range, when a buyer uses procurement flows, then RFQ and PO authoring surface that status before submission.
3. Given procurement records are created, when later blanket-order or landed-cost work needs a stable hook, then contract-ready or extension-ready reference fields already exist on the relevant sourcing or PO records.
4. Given procurement leadership reviews performance, when reporting is opened, then quote turnaround, award outcomes, and scorecard-relevant sourcing signals are visible.
5. Given this story is implemented, when the touched code is reviewed, then no blanket-order execution logic, landed-cost allocation engine, or supplier-portal automation is implemented inside this control slice.

## Tasks / Subtasks

- [ ] Task 1: Extend the supplier model for procurement controls. (AC: 1-2)
  - [ ] Add procurement hold fields such as `on_hold`, `hold_type`, and `release_date` or compatible equivalents to the supplier model.
  - [ ] Add supplier scorecard summary fields or scorecard-compatible status fields such as `scorecard_standing`, `scorecard_last_evaluated_at`, `warn_rfqs`, `prevent_rfqs`, `warn_pos`, and `prevent_pos` needed to warn or block RFQ and PO workflows.
  - [ ] Keep these procurement controls separate from Epic 25 commercial defaults such as currency and payment terms.
- [ ] Task 2: Enforce supplier controls in sourcing and PO flows. (AC: 1-2)
  - [ ] Apply supplier hold and scorecard checks during RFQ draft or submit actions in Story 24.1 and during PO create or submit actions in Story 24.2.
  - [ ] Distinguish warning outcomes from blocking outcomes so operator intent and policy are visible, with blocking as validation failure and warning as explicit banner or status messaging.
  - [ ] Enforce release-date behavior through deterministic validation logic, with optional scheduler cleanup as a later optimization rather than the only control path.
  - [ ] Keep enforcement deterministic and tenant-scoped.
- [ ] Task 3: Add extension hooks for later procurement capabilities. (AC: 3)
  - [ ] Add additive nullable fields on procurement records for contract references, blanket-order-compatible references, and landed-cost-compatible references such as `contract_reference` on RFQ and Supplier Quotation records plus `blanket_order_reference_id` and `landed_cost_reference_id` on Purchase Order records.
  - [ ] Keep these hooks explicit but non-executing so later stories can attach behavior without schema churn.
  - [ ] Ensure these extension references remain tenant-scoped and compatible with procurement lineage plus supplier-invoice readiness rather than replacing those links.
- [ ] Task 4: Build procurement control reporting and UI feedback. (AC: 1-4)
  - [ ] Surface supplier hold or scorecard warnings in RFQ and PO create flows.
  - [ ] Add reporting views for quote turnaround, award outcomes, and supplier performance signals derived from Stories 24.1 through 24.4.
  - [ ] Reuse Epic 22 shared feedback, tables, filters, and status-display patterns.
- [ ] Task 5: Add focused tests and validation. (AC: 1-5)
  - [ ] Add backend tests for hold-state enforcement, scorecard warning versus blocking behavior, extension-field rollout, and procurement reporting summaries.
  - [ ] Add frontend tests for warning banners, blocked-submit messaging, and procurement performance views.
  - [ ] Validate that no blanket-order execution or landed-cost automation lands in this story.

## Dev Notes

### Context

- ERPnext Supplier supports hold controls and scorecard-driven warning or blocking behavior for RFQs and POs.
- Supplier Scorecard standing in ERPnext can warn or prevent RFQ and PO authoring based on evaluated score thresholds.
- UltrERP's current supplier model is intentionally minimal, so this story should extend it conservatively and only for procurement controls.

### Architecture Compliance

- Keep supplier procurement controls on the supplier master and enforcement in procurement workflows.
- Keep extension hooks additive and nullable so later blanket-order or landed-cost work can attach cleanly.
- Do not merge Epic 25 commercial default fields into this story.
- Keep reporting read-oriented; do not add automation beyond deterministic warning or blocking checks.

### Implementation Guidance

- Likely backend files:
  - `backend/common/models/supplier.py`
  - `backend/domains/inventory/schemas.py`
  - `backend/domains/procurement/models.py`
  - `backend/domains/procurement/schemas.py`
  - `backend/domains/procurement/service.py`
  - `backend/domains/procurement/routes.py`
  - migrations under `migrations/versions/`
- Likely frontend files:
  - `src/domain/procurement/` for RFQ and PO warnings plus reporting views
  - supplier-maintenance surfaces that already expose supplier master data
  - `src/lib/api/procurement.ts`
  - supplier API surfaces as needed
- Supplier scorecard evaluation can begin as a procurement-oriented summary and rollout seam even if a full periodic scorecard engine evolves later.
- The first slice can stop at supplier scorecard summary and enforcement fields; a full periodic scorecard calculation engine can land later without breaking the supplier contract established here.
- Warning and blocking semantics should mirror the named supplier control fields: `warn_rfqs` and `warn_pos` surface non-blocking UI feedback, while `prevent_rfqs` and `prevent_pos` fail validation for the affected workflow.
- Quote turnaround reporting should use timestamps and award outcomes from Story 24.1 rather than introducing manual reporting-only fields.

### Testing Requirements

- Backend tests should cover release-date behavior, warn-versus-block transitions, tenant isolation, and null-safe extension-field rollout.
- Frontend tests should cover warning and blocking messaging plus procurement performance filtering.
- If new translation keys are added, locale files should stay synchronized.

### References

- `../planning-artifacts/epic-24.md`
- `../planning-artifacts/epic-23-31-execution-plan.md`
- `ERPnext-Validated-Research-Report.md`
- `.omc/research/erpnext-buying-detailed.md`
- `.omc/research/review-roadmap.md`
- `.omc/research/review-gap-claims.md`
- `backend/common/models/supplier.py`
- `backend/domains/inventory/schemas.py`
- `CLAUDE.md`

## Dev Agent Record

### Agent Model Used

GPT-5.4

### Debug Log References

- Story draft only; implementation and validation commands not run yet.

### Completion Notes List

- 2026-04-21: Drafted Story 24.5 from Epic 24, the buying research, and the current supplier model so procurement controls, reporting, and future procurement extensions can land without stealing Epic 25 commercial-default scope.

### File List

- `_bmad-output/implementation-artifacts/24-5-supplier-controls-and-procurement-extensions.md`