# Story 18.5: Forward Invoice Unit Cost Ambiguity Guard

Status: review

## Story

As an owner,
I want new invoices to avoid guessing a `unit_cost` when the best historical purchase candidates disagree,
So that future gross-margin periods stay as trustworthy as the historical backfill path.

## Problem Statement

Story 18.3 introduced forward invoice-side cost stamping through `_resolve_latest_unit_cost()`, and Story 18.4 introduced historical backfill with explicit ambiguity detection. The current behavior is intentionally conservative for historical backfill, but the forward resolver still returns the first same-ranked row when two top-ranked purchase candidates share the same date and source priority but disagree on price.

That leaves a consistency gap:

- historical `invoice_lines.unit_cost IS NULL` rows are skipped when the top-ranked purchase tier is ambiguous
- newly created invoices can still stamp a guessed `unit_cost` from the same ambiguous purchase history

This follow-up aligns the forward path with the same trustworthiness standard already applied by the 18.4 historical backfill.

## Scope

This story only changes forward invoice-side `unit_cost` resolution for newly created invoices. It does not rerun the historical backfill, does not relax dashboard availability semantics, and does not change the product-only matching rule established in Story 18.4.

## Implemented Solution

- Updated `_resolve_latest_unit_cost()` in `backend/domains/invoices/service.py` so the forward invoice path now inspects the entire highest-ranked eligible purchase tier instead of returning the first row blindly.
- Preserved Story 18.3's cutoff and same-day source precedence rules: only sources on or before the invoice date are eligible, and same-day supplier invoices still outrank supplier orders when the winning tier is unique.
- Added the ambiguity guard from Story 18.4 to the forward resolver: if the latest eligible date and source-priority tier contains more than one distinct `unit_cost`, the resolver now returns `None` instead of guessing.
- Added focused backend coverage for both halves of the forward-path contract: ambiguous top-tier rows now return `None`, and unique same-day supplier invoices still win over same-day supplier orders.

## Acceptance Criteria

1. [x] Forward invoice creation uses the same cutoff and precedence rules as Stories 18.3 and 18.4, but returns no resolved `unit_cost` when the highest-ranked eligible purchase tier contains more than one distinct price.
2. [x] Same-day precedence still prefers supplier invoices over supplier orders when the winning top-ranked tier is unique.
3. [x] Focused backend tests cover the ambiguous same-tier case and the non-ambiguous same-day precedence case.
4. [x] Story 18.4's historical backfill command remains unchanged except for any necessary cross-reference or documentation note.

## Tasks / Subtasks

- [x] Task 1: Align forward resolver semantics
  - [x] Subtask 1.1: Extract or reuse the top-ranked purchase-source logic so `_resolve_latest_unit_cost()` can detect ambiguity instead of returning the first row blindly.
  - [x] Subtask 1.2: Preserve the existing invoice-date cutoff and same-day supplier-invoice precedence.
  - [x] Subtask 1.3: Return `None` for ambiguous forward matches so invoice creation stays conservative.

- [x] Task 2: Add focused regression coverage
  - [x] Subtask 2.1: Add a focused test for same-day conflicting supplier-invoice prices on the forward path.
  - [x] Subtask 2.2: Keep or strengthen the existing same-day precedence test for the unique-price case.

- [x] Task 3: Record the consistency rule
  - [x] Subtask 3.1: Update Story 18.3 or 18.4 completion notes if needed to state that forward and historical ambiguity handling are now aligned.

## Dev Notes

### Constraints

- Do not change the product-only matching rule. Sales invoices still have no supplier context.
- Do not weaken owner-dashboard `available` semantics.
- Do not backfill old invoices as part of this story.
- Do not silently choose among same-tier conflicting unit costs.

### Likely Implementation Surfaces

| File | Purpose |
|------|---------|
| `backend/domains/invoices/service.py` | Forward invoice cost resolution path (`_resolve_latest_unit_cost()`) |
| `backend/tests/domains/invoices/test_service.py` | Focused forward resolver regression tests |
| `_bmad-output/implementation-artifacts/18-4-historical-invoice-unit-cost-backfill.md` | Cross-reference to the historical ambiguity rule |

## Validation Targets

- focused pytest for `backend/tests/domains/invoices/test_service.py`
- targeted Ruff for `backend/domains/invoices/service.py` and the touched test file
- explicit assertion that ambiguous same-tier matches produce `None` on the forward invoice path

## Dev Agent Record

### Debug Log

- Reused the ranked purchase-source query already introduced for Stories 18.3 and 18.4, but changed the forward resolver to inspect the whole winning tier before choosing a cost.
- Kept the resolver product-only. The review finding was about ambiguity handling, not supplier-context enrichment, and the sales invoice data model still has no supplier reference.
- Added one integration-style ambiguity test and one integration-style unique-precedence test to the existing invoice cost regression harness so the forward path and the historical backfill path now enforce the same trust boundary.

### Completion Notes

- Forward invoice stamping no longer guesses among same-tier conflicting purchase prices. That keeps future invoice `unit_cost` persistence aligned with the same ambiguity rule already used by Story 18.4's historical backfill.
- The owner dashboard behavior did not change directly. Availability remains conservative because ambiguous forward matches now stay null instead of being guessed into a misleading cost.

## Validation

Validated on 2026-04-12 with:

- `cd backend && uv run python -m pytest tests/domains/invoices/test_unit_cost_backfill.py::test_forward_resolver_returns_none_for_ambiguous_top_ranked_prices tests/domains/invoices/test_unit_cost_backfill.py::test_forward_resolver_prefers_same_day_supplier_invoice_when_unique tests/domains/invoices/test_unit_cost_backfill.py::test_forward_resolver_ignores_future_purchase_costs tests/domains/invoices/test_service.py::TestCreateInvoice::test_resolve_latest_unit_cost_uses_invoice_date_cutoff_and_priority tests/domains/invoices/test_service.py::TestCreateInvoice::test_create_invoice_leaves_unit_cost_null_when_latest_purchase_tier_is_ambiguous -q` (`5 passed`)
- `cd backend && uv run ruff check domains/invoices/service.py tests/domains/invoices/test_service.py tests/domains/invoices/test_unit_cost_backfill.py`

## File List

- `backend/domains/invoices/service.py`
- `backend/tests/domains/invoices/test_service.py`
- `backend/tests/domains/invoices/test_unit_cost_backfill.py`
- `_bmad-output/implementation-artifacts/18-4-historical-invoice-unit-cost-backfill.md`

## Change Log

- 2026-04-12: Aligned forward invoice `unit_cost` resolution with the historical ambiguity rule so same-tier conflicting purchase prices now return `None` instead of a guessed value.

## References

- Story 18.3 implementation record: `_bmad-output/implementation-artifacts/18-3-purchase-price-mapping-and-margin-calculation.md`
- Story 18.4 implementation record: `_bmad-output/implementation-artifacts/18-4-historical-invoice-unit-cost-backfill.md`