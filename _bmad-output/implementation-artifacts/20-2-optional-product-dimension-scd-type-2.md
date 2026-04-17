# Story 20.2: Optional Product Dimension SCD Type 2

Status: deferred

## Story

As an analytics platform architect,
I want an optional SCD Type 2 product dimension,
so that UltrERP can track product-master changes independently of sale-time order-line snapshots when that extra history is genuinely needed.

## Problem Statement

`backend/common/models/product.py` stores mutable product name and category fields, but the current repo does not expose a clearly established product-master write owner in the Epic 20 anchor set. Story 20.1 already fixes the higher-value problem by freezing product context on each sale. A separate SCD Type 2 product dimension is only justified if Story 20.3 or later analytics need a conformed product dimension keyed independently from those transaction-time snapshots.

## Solution

Keep this story deferred by default for v1. Activate it only if Story 20.3 makes an explicit modeling decision that `sales_monthly` needs a conformed `product_snapshot_id` instead of inline snapshot text alone.

If activated:

- create `product_snapshots` in a new backend foundation package under `backend/domains/product_analytics/`
- add write logic that closes the old row and opens a new row whenever `Product.name` or `Product.category` changes
- hook that logic into the actual product write owner once that owner is confirmed
- keep Story 20.1 order-line snapshots as the canonical historical sales truth even if this dimension exists

## Best-Practice Update

This section supersedes conflicting details below.

- This story is optional and v1-deferred unless Story 20.3 explicitly requires a conformed dimension.
- Do not replace order-line snapshots with SCD joins for historical sales truth.
- Do not invent a category table, new product CRUD API, or separate admin flow just to support this dimension.
- Use non-overlapping effective windows with exactly one open row per tenant and product.
- If implementation cannot identify the real product write owner, stop and keep the story deferred rather than guessing.

## Acceptance Criteria

1. Given Story 20.3 ships with inline snapshot text on `sales_monthly`, when Epic 20 v1 scope is finalized, then Story 20.2 may remain deferred without blocking Story 20.3.
2. Given the team activates Story 20.2, when a product name or category changes through the real write owner, then the current `product_snapshots` row is closed and a new row opens with non-overlapping effective dates.
3. Given a product save where neither name nor category changed, when the save completes, then no new SCD row is created.
4. Given a lookup date and `product_id`, when the as-of read helper runs, then it returns the correct row for that point in time.
5. Given concurrent writes to the same product, when snapshot updates race, then only one current row remains open and no overlapping effective ranges are persisted.

## Technical Notes

### Existing extension points

- Mutable product master: `backend/common/models/product.py`
- Potential future owner hooks: whichever service actually owns product create/update once identified
- Downstream consumer if activated: Story 20.3 refresh logic and later portfolio analytics

### Activated design only

- Add `product_snapshots` with `tenant_id`, `product_id`, `name`, `category`, `effective_from`, `effective_to`, `created_at`, and `updated_at`.
- Add a uniqueness or exclusion strategy that guarantees one open row per tenant and product.
- Add write and as-of lookup helpers under `backend/domains/product_analytics/service.py`.
- Keep `product_snapshot_id` optional for Story 20.3. Inline snapshot text is still valid for v1.

## Tasks / Subtasks

- [ ] Task 1: Confirm whether Story 20.3 truly needs a conformed product dimension. If not, leave this story deferred.
- [ ] Task 2: If activated, add `product_snapshots` and its Alembic migration under `backend/domains/product_analytics/`.
- [ ] Task 3: Implement row-locking SCD close-and-open logic with no-overlap guarantees.
- [ ] Task 4: Hook the SCD writer into the actual product-mutation owner. Do not guess.
- [ ] Task 5: Add date-based lookup helpers and focused concurrency tests.

## Dev Notes

- Story 20.1 is the non-optional historical-sales foundation. Story 20.2 is additive only.
- The absence of a clearly established product update owner is the key repo-reality constraint in this story.
- If this story is deferred, keep the file as guidance and do not create placeholder code.

## Project Structure Notes

- Proposed new foundation surface: `backend/domains/product_analytics/models.py`, `backend/domains/product_analytics/service.py`
- Existing anchor surface: `backend/common/models/product.py`

## References

- `../planning-artifacts/epic-20.md`
- `../planning-artifacts/research/domain-epic-20-product-sales-analytics-research-2026-04-15.md`
- `backend/common/models/product.py`

## Dev Agent Record

### Agent Model Used

GPT-5.4

### Debug Log References

- Story drafted only. Populate during implementation.

### Completion Notes List

- Story intentionally marked optional and v1-deferred unless Story 20.3 requires a conformed dimension.

### File List

- `backend/common/models/product.py`
- `backend/domains/product_analytics/models.py`
- `backend/domains/product_analytics/service.py`
- `migrations/versions/<new_revision>.py`