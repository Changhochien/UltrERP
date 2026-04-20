# Story 21.1: Preserve Existing Order Lifecycle and Expose Derived Execution Signals

Status: done

## Story

As an ERP operator,
I want order APIs and frontend types to expose commercial, fulfillment, and billing meaning without rewriting the working order lifecycle,
so that the orders workspace becomes clearer without regressing confirmation, invoicing, or stock reservation.

## Acceptance Criteria

1. Given an order stored as `pending`, when list or detail payloads are returned, then the API exposes a pre-commit commercial signal while keeping the persisted `status` unchanged.
2. Given an order has `invoice_id`, `confirmed_at`, and invoice payment data, when it is serialized, then billing meaning is derived consistently from existing data instead of a new write-side enum.
3. Given a confirmed, shipped, or fulfilled order is serialized, when the workspace renders it, then fulfillment meaning is derived consistently from the existing lifecycle and timestamps.
4. Given the existing confirmation workflow runs, when regression tests execute, then invoice creation and stock reservation still happen atomically on confirmation.
5. Given any touched backend or frontend consumer needs the new execution view, when it requests order data, then the derivation rules come from one centralized helper and remain deterministic across all touched surfaces.

## Tasks / Subtasks

- [x] Task 1: Centralize derived order execution mapping. (AC: 1-3, 5)
  - [x] Add a reusable helper in `backend/domains/orders/services.py` or a nearby serializer module that derives commercial, fulfillment, and billing meaning from `status`, `invoice_id`, `confirmed_at`, and invoice payment state.
  - [x] Avoid adding new persisted lifecycle columns in this story.
  - [x] Keep the derivation rules explicit so list, detail, and reporting consumers all use the same mapping.
- [x] Task 2: Extend order response contracts and frontend types. (AC: 1-3, 5)
  - [x] Update `backend/domains/orders/schemas.py` list/detail responses to expose the derived execution fields the workspace needs.
  - [x] Extend `src/domain/orders/types.ts` and `src/lib/api/orders.ts` to consume the enriched response shape.
  - [x] Preserve existing `status` as the persisted lifecycle field for compatibility.
- [x] Task 3: Preserve the superior confirmation path. (AC: 4)
  - [x] Keep `confirm_order()` as the atomic invoice-and-reservation workflow.
  - [x] Do not introduce a migration, new write-side stage, or alternative confirmation path in this story.
- [x] Task 4: Add focused regression coverage for the derived mapping and preserved lifecycle. (AC: 1-5)
  - [x] Add backend tests covering pending, confirmed, shipped, fulfilled, and cancelled orders.
  - [x] Add tests proving the enriched payload does not change confirmation behavior or reservation timing.

## Dev Notes

### Context

The live order domain already uses `pending -> confirmed -> shipped -> fulfilled/cancelled`, and `confirm_order()` currently creates the invoice and reserves stock in one transaction. The best practice here is to preserve those proven mechanics and add a clearer read model for the workspace instead of doing a migration-first rewrite.

### Architecture Compliance

- Keep the persisted `status` lifecycle as the write-side source of truth in v1.
- Treat derived execution fields as read-side clarity, not a second state machine.
- Do not add lifecycle columns or an Alembic migration in this story.
- Preserve `confirmed_at` semantics because analytics and invoice linkage already depend on it.

### Implementation Guidance

- Most likely touched files:
  - `backend/domains/orders/schemas.py`
  - `backend/domains/orders/services.py`
  - `backend/domains/orders/routes.py`
  - `src/domain/orders/types.ts`
  - `src/lib/api/orders.ts`
- Billing meaning should come from existing order and invoice data, not from a speculative new billing enum.
- If invoice payment status is not already present on the order response, expose only the minimum read-side information needed by the workspace.

### Testing Requirements

- Backend-focused validation is the priority.
- Run the touched order tests plus confirmation regression coverage with `cd backend && uv run pytest tests/<path>`.
- If frontend types or API callers are touched, run a focused frontend check for the touched slice.

### References

- `../planning-artifacts/epic-21.md`
- `ERPnext-Validated-Research-Report.md`
- `backend/domains/orders/services.py`
- `backend/domains/orders/schemas.py`
- `backend/tests/domains/orders/test_order_confirmation.py`
- `CLAUDE.md`

## Dev Agent Record

### Agent Model Used

GPT-5.4

### Debug Log References

- `cd backend && uv run pytest tests/domains/orders/test_orders_api.py tests/domains/orders/test_order_confirmation.py`
- Focused confirmation regression reruns on `backend/tests/domains/orders/test_order_confirmation.py` while debugging the fake execute queue mismatch in the confirm-order test helper.
- Static error checks over the touched backend order files and `src/domain/orders/types.ts` returned no issues.

### Completion Notes List

- Added additive backend execution enums and response models for commercial, fulfillment, billing, and reservation meaning, and mirrored the enriched contract in `src/domain/orders/types.ts` while keeping persisted `status` as the write-side lifecycle field.
- Centralized read-side derivation in `_derive_order_execution_signals()` and `build_order_execution_view_map()` in `backend/domains/orders/services.py`, and reused that mapping across order list, detail, and status-update serialization in `backend/domains/orders/routes.py`.
- Exposed `invoice_number`, `invoice_payment_status`, and nested `execution` signals without adding lifecycle columns or changing the existing confirmation flow.
- Updated `list_orders()` to preload `Order.lines` so readiness and backorder cues derive deterministically from the same line-level data used by the workspace.
- Preserved the atomic confirmation workflow. The only follow-up fix after validation was aligning the fake execute queue in `backend/tests/domains/orders/test_order_confirmation.py` with the real confirm-order readback sequence.
- Validation passed on 2026-04-20 with focused backend coverage (`38 passed`) plus clean static diagnostics on the touched files.

### File List

- `backend/domains/orders/schemas.py`
- `backend/domains/orders/services.py`
- `backend/domains/orders/routes.py`
- `backend/tests/domains/orders/_helpers.py`
- `backend/tests/domains/orders/test_orders_api.py`
- `backend/tests/domains/orders/test_order_confirmation.py`
- `src/domain/orders/types.ts`
