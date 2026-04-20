# Story 21.5: Commission Tracking, Order Metadata, and Reporting Alignment

Status: ready-for-dev

## Story

As an operations and reporting user,
I want orders to support commission data and reporting-safe commitment semantics,
so that sales performance and order metrics can improve without destabilizing the existing order workflow.

## Acceptance Criteria

1. Given an order carries commission assignments, when it is viewed or reported on, then commission allocations and totals are available through the touched API and UI surfaces.
2. Given commission tracking is added, when orders are created, edited, confirmed, or fulfilled, then the existing invoice creation, reservation, and lifecycle behavior remains unchanged.
3. Given optional order metadata such as UTM fields is considered, when implementation scope is finalized, then it is only shipped if a real consumer in this epic uses it; otherwise the story closes on commission plus reporting alignment alone.
4. Given reporting counts commercially committed orders, when metrics are computed, then pending intake orders are excluded and confirmed orders remain counted by confirmation semantics rather than creation time alone.
5. Given this story changes reporting or intelligence logic, when the work is complete, then the touched legacy status-based reporting paths are documented in the implementation notes.

## Tasks / Subtasks

- [ ] Task 1: Add additive commission support to the order domain. (AC: 1, 2)
  - [ ] Extend the order model, schemas, and response contracts with the minimum additive commission structure needed for assignments and totals.
  - [ ] If no reusable commission or salesperson shape exists in the current source, choose the smallest structure that supports real order reporting needs.
  - [ ] Keep commission data orthogonal to confirmation, reservation, fulfillment, and invoice linkage.
- [ ] Task 2: Expose commission information through the touched API and UI surfaces. (AC: 1, 2)
  - [ ] Update the relevant backend order responses and frontend order types or views so commission information is visible where order operators or reporting users need it.
  - [ ] Avoid pulling CRM or quotation-specific abstractions into the orders domain.
- [ ] Task 3: Gate optional order metadata by real usage. (AC: 3)
  - [ ] Only add low-effort order metadata such as UTM fields if a real consumer inside Epic 21 uses it.
  - [ ] If no real consumer exists, document that metadata was deliberately deferred to keep scope tight.
- [ ] Task 4: Align reporting and intelligence semantics with confirmation. (AC: 4, 5)
  - [ ] Update reporting or intelligence paths that still rely on creation-time or stale status assumptions for committed-order counts.
  - [ ] Ensure committed-order analytics key off the preserved confirmation semantics, especially `confirmed_at` and the committed lifecycle states already in code.
  - [ ] Perform a targeted repository sweep for touched order-reporting paths and document the ones changed.
- [ ] Task 5: Add focused regression coverage. (AC: 1-5)
  - [ ] Add tests for commission serialization and any touched commission calculations.
  - [ ] Add tests proving committed-order reporting excludes pending intake orders and continues counting confirmed orders correctly.
  - [ ] Add compatibility coverage if optional metadata is introduced.

## Dev Notes

### Context

The validated research identified commission tracking as a low-effort order-domain gap and reporting alignment as a necessary guardrail. No reusable commission or UTM shape was found in the current backend source search under `backend/app`, `backend/domains`, or `backend/common`, so this story should stay additive and minimal.

### Architecture Compliance

- Keep this work inside the existing orders and reporting surfaces.
- Do not use commission tracking as a gateway to broader CRM or incentive-management scope.
- Preserve the current order confirmation and fulfillment semantics while extending reporting.

### Implementation Guidance

- Most likely touched files:
  - `backend/domains/orders/schemas.py`
  - `backend/domains/orders/services.py`
  - `backend/domains/orders/routes.py`
  - `backend/domains/intelligence/service.py`
  - any adjacent reporting modules that count orders
  - `src/lib/api/orders.ts`
  - `src/domain/orders/types.ts`
  - any order detail or reporting-adjacent UI surfaces that expose commission data
- Prefer additive commission fields or related child records over refactoring the whole order model.
- If optional metadata is added, keep it clearly optional and non-blocking for the rest of the order workflow.
- Start the reporting sweep with `backend/domains/intelligence/service.py`, where `_COUNTABLE_STATUSES` currently anchors committed-order counting behavior.

### Testing Requirements

- Backend validation is the priority for commission and reporting semantics.
- Add targeted tests for commission payloads and committed-order analytics.
- Protect against regressions that would start counting pending intake orders as committed demand.

### References

- `../planning-artifacts/epic-21.md`
- `ERPnext-Validated-Research-Report.md`
- `backend/domains/orders/routes.py`
- `backend/domains/orders/services.py`
- `backend/domains/orders/schemas.py`
- `backend/domains/intelligence/service.py`
- `src/lib/api/orders.ts`
- `src/domain/orders/types.ts`
- `CLAUDE.md`

## Dev Agent Record

### Agent Model Used

Record the model and version used during implementation.

### Debug Log References

Record focused validation commands and any review artifacts produced during implementation.

### Completion Notes List

Summarize commission support, metadata decisions, reporting changes, and validation results here once implementation is done.

### File List

List every file created or modified during implementation.
