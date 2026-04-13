# Story 18.4: Historical Invoice Unit Cost Backfill

Status: review

## Story

As an owner,
I want historical invoice lines without `unit_cost` backfilled from verified purchase history,
So that older gross-margin periods can become available without reissuing invoices.

## Problem Statement

Story 18.3 fixed the forward-looking cost chain for new supplier orders, new invoices, and the owner dashboard contract, but it intentionally left older `invoice_lines.unit_cost` values untouched. Because the dashboard now uses a conservative `available` rule, any current-period or historical period containing even one invoice line with `unit_cost = NULL` remains unavailable.

That is the correct behavior for trustworthiness, but it leaves a follow-up gap: historical periods can only become available if older invoice lines are backfilled from a deterministic purchase-cost source.

## Scope

This story is limited to historical backfill for existing `invoice_lines.unit_cost IS NULL` rows. It does not change Story 18.3's forward cost-resolution path, and it must not weaken the conservative `available` rule on the gross-margin KPI.

## Implemented Solution

- Added a batched historical backfill service in `backend/domains/invoices/service.py` that reuses Story 18.3's cutoff and same-day source precedence rules while computing results in set-based SQL batches instead of row-by-row loops.
- Kept the historical matching rule product-only, because sales invoices and invoice lines do not carry supplier context that would support a stricter product-plus-supplier match.
- Added explicit ambiguity detection for the top-ranked historical candidates: if the winning date/source-priority tier contains more than one distinct `unit_cost`, the row is skipped and reported instead of guessed.
- Added `backend/scripts/backfill_invoice_unit_cost.py` with dry-run by default, `--live` for updates, and `--batch-size` / `--limit` controls so the command remains practical on large legacy datasets.
- Preserved replay safety by only ever updating rows that still have `invoice_lines.unit_cost IS NULL`.

## Acceptance Criteria

1. [x] A dedicated backfill command identifies candidate `invoice_lines` where `unit_cost IS NULL` and `product_id IS NOT NULL`.
2. [x] The backfill resolves historical cost using the same business rules as Story 18.3: only purchase records on or before the invoice date are eligible, and same-day ties prefer supplier invoices over supplier orders.
3. [x] The backfill is idempotent: rerunning it does not change already-populated rows or create duplicate side effects.
4. [x] Rows with no deterministic historical cost match are skipped, counted, and reported rather than guessed.
5. [x] Focused tests cover successful backfill, skipped unmatched rows, and replay safety.

## Tasks / Subtasks

- [x] Task 1: Define the historical matching rule
  - [x] Subtask 1.1: Reuse the Story 18.3 resolver semantics (`effective_date <= invoice_date`, supplier invoice precedence on same-day ties).
  - [x] Subtask 1.2: Decide whether matching is product-only or product-plus-supplier when supplier context exists on the invoice.
  - [x] Subtask 1.3: Document why ambiguous matches are skipped instead of guessed.

- [x] Task 2: Implement a replay-safe backfill command
  - [x] Subtask 2.1: Add `backend/scripts/backfill_invoice_unit_cost.py`.
  - [x] Subtask 2.2: Support dry-run output plus a live mode that updates only null `unit_cost` rows.
  - [x] Subtask 2.3: Emit counts for updated rows, skipped rows, and ambiguous rows.

- [x] Task 3: Validate and report
  - [x] Subtask 3.1: Add focused backend tests for the historical matcher and command behavior.
  - [x] Subtask 3.2: Add a validation note showing command output on the local database in dry-run mode before any live execution.
  - [x] Subtask 3.3: Update Story 18.3 completion notes once the historical backfill is shipped.

## Dev Notes

### Constraints

- Do not overwrite non-null `invoice_lines.unit_cost` values.
- Do not use future purchase prices for historical invoices.
- Do not mark gross margin `available = true` by relaxing the dashboard rule; availability should improve only because the missing invoice-line costs were actually backfilled.
- Do not silently choose among ambiguous historical matches.

### Matching Decision

- Matching is product-only. The invoice model has no supplier reference on the sales-side invoice or invoice line, so product-plus-supplier matching is not supported by the persisted data.
- Ambiguous rows are defined as rows whose highest-ranked eligible source tier (latest eligible date, then highest same-day source priority) contains more than one distinct `unit_cost`.
- The command now batches candidate resolution because the local legacy tenant already contains hundreds of thousands of null-cost invoice lines; a one-shot full-table dry run is not operationally realistic under the repo's DB timeout settings.

### Likely Implementation Surfaces

| File | Purpose |
|------|---------|
| `backend/domains/invoices/service.py` | Source-of-truth resolver semantics from Story 18.3 |
| `backend/domains/dashboard/services.py` | Conservative availability logic that the backfill should satisfy, not bypass |
| `backend/common/models/supplier_order.py` | Historical supplier-order price source |
| `backend/common/models/supplier_invoice.py` | Historical supplier-invoice price source |
| `backend/scripts/backfill_invoice_unit_cost.py` | New follow-up command |

## Validation Targets

- `backend/tests/domains/invoices/...` focused matcher/backfill tests
- dry-run execution against the local database before any live update
- explicit counts for updated, skipped, and unmatched rows

## Dev Agent Record

### Debug Log

- Added a set-based historical decision engine in `backend/domains/invoices/service.py` instead of reusing the forward resolver row-by-row. The forward path keeps its existing behavior; the backfill path adds explicit ambiguity detection and batch processing.
- Added `--batch-size` and `--limit` to the CLI after measuring the default tenant's historical workload shape (`591943` null-cost candidate rows and `481444` distinct product/date slices). Without batching, the local dry run exceeded the repo's asyncpg command timeout.
- Used keyset-style progression by `invoice_line_id` so live runs can safely mutate `unit_cost` while still advancing through the remaining null rows without offset drift.
- BMAD code-review follow-up: live mode now commits per batch instead of holding one giant transaction open for the entire historical slice, and the CLI rejects non-positive `--batch-size` / `--limit` values instead of silently doing nothing.

### Completion Notes

- Historical cost resolution now improves owner-dashboard availability only by filling real missing `invoice_lines.unit_cost` values. The conservative gross-margin `available` rule was not loosened.
- The backfill command is intentionally dry-run first and supports bounded validation windows (`--limit`) so operators can inspect behavior before committing a large historical slice.
- The local dry-run evidence below was captured with a bounded run because the current default tenant holds a very large imported history.
- BMAD review follow-up shipped in Story 18.5: the forward invoice resolver now applies the same ambiguity rule already used by the historical backfill, so future invoices no longer guess among same-tier conflicting purchase prices.

## Validation

Validated on 2026-04-12 with:

- `cd backend && uv run python -m pytest tests/domains/invoices/test_unit_cost_backfill.py -q` (`5 passed` after the code-review follow-up test for per-batch commits)
- `cd backend && uv run ruff check domains/invoices/service.py scripts/backfill_invoice_unit_cost.py tests/domains/invoices/test_unit_cost_backfill.py`
- `cd backend && uv run python -m scripts.backfill_invoice_unit_cost --limit 0` → exits with `argument --limit: value must be a positive integer`
- `cd backend && uv run python -m scripts.backfill_invoice_unit_cost --batch-size 250 --limit 1000`
  - Output summary: `Candidates = 1000`, `Would update = 976`, `Skipped = 24`, `Unmatched = 23`, `Ambiguous = 1`

## File List

- `backend/domains/invoices/service.py`
- `backend/scripts/backfill_invoice_unit_cost.py`
- `backend/tests/domains/invoices/test_unit_cost_backfill.py`

## Change Log

- 2026-04-12: Added historical invoice `unit_cost` backfill service, batched dry-run/live CLI, ambiguity detection for top-ranked conflicting costs, and focused regression coverage.
- 2026-04-12: BMAD code-review follow-up tightened the operator path by committing live batches incrementally, rejecting non-positive batch controls, and adding regression coverage for the per-batch commit flow.

## References

- Story 18.3 forward cost chain: `backend/domains/invoices/service.py`
- Story 18.3 dashboard contract: `backend/domains/dashboard/services.py`
- Story 18.3 implementation record: `_bmad-output/implementation-artifacts/18-3-purchase-price-mapping-and-margin-calculation.md`