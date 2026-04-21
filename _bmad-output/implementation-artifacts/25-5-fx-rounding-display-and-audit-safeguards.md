# Story 25.5: FX Rounding, Display, and Audit Safeguards

Status: drafted

## Story

As a finance or commercial user,
I want foreign-currency calculations, display, and audit details to be deterministic,
so that transaction amounts, base amounts, and displayed totals do not silently drift apart.

## Problem Statement

Stories 25.1 through 25.4 establish currency masters, document FX fields, payment-term templates, and party defaults, but the system still needs one consistent rule for formatting, rounding, and validating converted amounts. Without that safeguard layer, different services or UI screens can round at different times, report queries can disagree with saved document values, and auditors cannot see how a base amount was derived from the transaction amount.

## Solution

Add an FX-safeguard slice that:

- centralizes money formatting, currency precision, conversion, and rounding rules
- makes transaction-to-base conversion details visible in document and audit views
- validates that line totals, header totals, and converted values follow one deterministic policy

This story should harden FX math and display behavior, not introduce GL revaluation or booking logic.

## Acceptance Criteria

1. Given a document total is converted between transaction and base currency, when the document is saved or displayed, then the system uses one shared rounding and precision policy derived from Epic 25 currency masters.
2. Given line items and header totals are converted, when totals are validated, then the system either matches the documented rounding policy or fails deterministically instead of silently adjusting values.
3. Given a finance or audit user reviews a foreign-currency document, when they open the detail or audit view, then the applied rate, effective date, transaction amounts, base amounts, and rounding rule are visible.
4. Given a document is rendered in the UI, when both transaction and base amounts are shown, then formatting and labels stay consistent across quotation, order, procurement, invoice, and payment surfaces.
5. Given this story is implemented, when the touched code is reviewed, then no unrealized gain or loss posting, no exchange-rate revaluation, and no finance-book parity work is introduced here.

## Tasks / Subtasks

- [ ] Task 1: Centralize FX precision and rounding rules. (AC: 1-3)
  - [ ] Define one shared utility for currency precision, transaction-to-base conversion, and rounding.
  - [ ] Use the currency master precision from Story 25.1 rather than hard-coded decimal assumptions.
  - [ ] Document the canonical calculation order for line amounts, header totals, and base totals.
- [ ] Task 2: Add deterministic validation guards. (AC: 1-2)
  - [ ] Validate that converted line amounts and header totals follow the shared calculation order.
  - [ ] Reject documents whose provided or recomputed totals drift outside the documented rounding policy.
  - [ ] Keep validation messages explicit about which amount and rule caused the mismatch.
- [ ] Task 3: Expose FX audit details and UI formatting. (AC: 3-4)
  - [ ] Add reusable UI formatting helpers for transaction and base amounts with consistent labels and symbols.
  - [ ] Expose applied rate, conversion effective date, base totals, and rounding policy on document detail and audit views.
  - [ ] Reuse Epic 22 shared UI primitives while keeping FX details readable rather than hidden in tooltips only.
- [ ] Task 4: Make document services consume the shared FX rules. (AC: 1-4)
  - [ ] Apply the shared utility across quotation, order, PO, invoice, supplier invoice, payment, and supplier payment services touched by Epic 25.
  - [ ] Ensure stored base amounts from Story 25.2 are validated against the shared rule, not recomputed ad hoc in each service.
  - [ ] Keep historical document snapshots immutable and audit-readable.
- [ ] Task 5: Add focused tests and validation. (AC: 1-5)
  - [ ] Add backend tests for currency-precision differences, line-versus-header rounding, deterministic validation failures, and immutable audit display of rate details.
  - [ ] Add frontend tests for consistent money formatting across document surfaces.
  - [ ] Validate that no revaluation, gain or loss booking, or finance-book automation lands in this story.

## Dev Notes

### Context

- Story 25.1 defines currency precision and exchange-rate lookup.
- Story 25.2 defines stored transaction and base amounts on commercial documents.
- This story is the safeguard layer that keeps those amounts mathematically and visually consistent.

### Architecture Compliance

- One shared FX utility should own conversion and rounding behavior.
- Document services should validate against stored base amounts, not drift into per-domain custom math.
- Audit views should explain the rate and rule used.
- Do not add GL or revaluation features here.

### Implementation Guidance

- Likely backend files:
  - shared commercial or money utility module used by orders, invoices, procurement, and payments
  - service layers touched by Story 25.2
  - migrations only if explicit rounding-policy metadata must be stored
- Likely frontend files:
  - shared money-formatting utilities
  - detail views for quotations, orders, POs, invoices, purchases, and payments
- Canonical FX math should be explicit: convert using the stored `conversion_rate`, round using the target currency precision, sum rounded line values into header totals, and fail validation when persisted values do not match the documented policy.
- If a rounding policy label is stored, keep it stable and human-readable for audit views.

### Testing Requirements

- Backend tests should cover at least one case where line rounding and header rounding could diverge, proving that the service rejects ambiguous totals deterministically.
- Frontend tests should cover currency symbol, precision, and transaction-versus-base labeling consistency.
- If new translation keys are added, locale files should stay synchronized.

### References

- `../planning-artifacts/epic-25.md`
- `../implementation-artifacts/25-1-currency-and-exchange-rate-masters.md`
- `../implementation-artifacts/25-2-currency-aware-commercial-documents.md`
- `ERPnext-Validated-Research-Report.md`
- `.omc/research/review-roadmap.md`
- `.omc/research/review-gap-claims.md`
- `.omc/research/gap-analysis.md`
- `CLAUDE.md`

## Dev Agent Record

### Agent Model Used

GPT-5.4

### Debug Log References

- Story draft only; implementation and validation commands not run yet.

### Completion Notes List

- 2026-04-21: Drafted Story 25.5 from Epic 25 and the validated multi-currency research so FX formatting, rounding, and audit visibility are deterministic across the commercial document set without expanding into GL work.

### File List

- `_bmad-output/implementation-artifacts/25-5-fx-rounding-display-and-audit-safeguards.md`