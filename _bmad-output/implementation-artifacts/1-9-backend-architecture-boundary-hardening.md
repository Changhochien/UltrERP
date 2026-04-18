# Story 1.9: Backend Architecture Boundary Hardening

Status: completed

**Story ID:** 1.9

---

## Story

As a developer,
I want explicit backend boundary wiring for shared model registration and order confirmation orchestration,
So that foundation-level refactors stop leaking across domains and core business flows stay safe to evolve.

---

## Problem Statement

The current backend foundation is stable enough to ship features, but three structural seams are now slowing safe change:

- `backend/common/models/__init__.py` imports domain-owned ORM models upward into `common`, which inverts the dependency direction of the shared kernel.
- Alembic and helper scripts currently rely on `import common.models` side effects for metadata registration, so the coupling is hidden in foundational tooling.
- `backend/domains/orders/services.py::confirm_order()` is doing too much orchestration inline: order locking, customer/product resolution, invoice persistence, stock reservation, snapshot stamping, and audit writes are mixed into one transaction script with direct imports of private cross-domain internals.

This story should fix the highest-leverage architectural seams first. It should not try to complete the full `inventory/services.py` and `invoices/service.py` decomposition in the same slice; instead, it should establish the public collaborator seams that make those follow-on splits safer.

## Solution

Harden the backend foundation in two focused steps:

1. Replace package-init side effects with an explicit ORM model registry so migrations and bootstrap helpers can load all mapped tables without requiring `common.models` to import domain-owned models.
2. Refactor order confirmation into a thin order-owned use case with public collaborator functions for invoice persistence and stock reservation, while preserving the current single-transaction behavior and response contract.

## Acceptance Criteria

**AC1:** Explicit ORM registration replaces upward package coupling

1. Given Alembic and helper scripts need ORM side-effect imports, when backend model metadata is loaded, then all mapped tables are registered through an explicit registry module rather than `import common.models`.
2. Given `backend/common/models/__init__.py` is imported, when package init runs, then it exports only common-owned ORM models and enums and does not import domain-owned ORM modules from `domains.*`.
3. Given migrations or bootstrap helpers run after the refactor, when metadata is inspected, then customer, invoice, payment, analytics, and settings tables are still registered successfully.

**AC2:** Order confirmation uses explicit public collaborators

1. Given a pending order is confirmed, when `confirm_order()` executes, then the order domain owns row locking, state validation, snapshot stamping, status mutation, and final audit behavior.
2. Given invoice creation and stock reservation are required parts of confirmation, when the workflow runs, then those steps are invoked through explicit public collaborator functions rather than private cross-domain internals such as `_create_invoice_core`.
3. Given the modular-monolith architecture allows direct service-to-service calls, when this story ships, then required confirmation steps remain explicit and deterministic instead of being hidden behind implicit handler ordering.

**AC3:** Confirmation remains one atomic workflow

1. Given a downstream failure occurs during confirmation after the order row is locked, when the transaction exits, then order status, invoice linkage, stock adjustments, and audit rows roll back together.
2. Given confirmation succeeds, when the order is reloaded, then the API-visible result still includes the linked invoice ID and the existing snapshot/audit behavior remains intact.
3. Given current order-line snapshot stamping exists, when the refactor lands, then the tenant-scoped product snapshot behavior from Story 20.1 remains unchanged.

**AC4:** Focused regression coverage proves the boundary hardening

1. Given the model-registry refactor lands, when focused backend validation runs, then there is an automated proof that the explicit registry still registers all ORM tables used by migrations/startup.
2. Given the confirmation refactor lands, when focused order-confirmation tests run, then success, rollback, snapshot stamping, and audit-log paths remain covered and green.
3. Given the story is implemented, when Ruff and the focused pytest slice run on touched backend files, then they pass without changing the public order-confirmation API contract.

## Tasks / Subtasks

- [x] **Task 1: Introduce an explicit ORM model registry** (AC1)
  - [x] Add a dedicated registry module such as `backend/common/model_registry.py` whose only responsibility is importing all ORM model modules needed for SQLAlchemy metadata registration.
  - [x] Update `migrations/env.py` to import the explicit model registry instead of `common.models`.
  - [x] Update helper/bootstrap scripts that currently rely on `import common.models` side effects, including `seed_user.py`.
  - [x] Keep the registry side-effect-only and separate from developer-facing model export surfaces.

- [x] **Task 2: Remove upward domain imports from the shared model package** (AC1)
  - [x] Trim `backend/common/models/__init__.py` so it exports only common-owned models/enums that actually live under `backend/common/models/`.
  - [x] Remove imports of domain-owned ORM classes such as `Customer`, `Invoice`, `Payment`, `SalesMonthly`, and `AppSetting` from that package init.
  - [x] Fix any touched call sites so domain-owned ORM classes are imported from their owning domain modules instead of the shared kernel.
  - [x] Preserve existing exports for genuinely common-owned models such as orders, order lines, products, warehouses, stock adjustments, supplier entities, users, approval requests, and audit logs.

- [x] **Task 3: Create explicit public collaborator seams for order confirmation** (AC2, AC3)
  - [x] Introduce a public invoice-persistence collaborator for in-transaction order confirmation use, either by promoting the current invoice core helper to a public supported function or by adding a narrow collaborator module under `backend/domains/invoices/`.
  - [x] Introduce a focused stock-reservation collaborator for order confirmation use, either in `backend/domains/inventory/` or a small helper module, without attempting the full inventory-service split in this story.
  - [x] Keep collaborator APIs explicit about transaction expectations: the caller owns the open session/transaction boundary.
  - [x] Do not expand the generic event-bus surface in this story unless a truly decoupled optional side effect is being added.

- [x] **Task 4: Slim `confirm_order()` into an order-owned use case** (AC2, AC3)
  - [x] Refactor `backend/domains/orders/services.py::confirm_order()` so it focuses on order locking, validation, product snapshot stamping, customer/buyer resolution, invoking public collaborators, status mutation, and order/invoice audit logging.
  - [x] Remove direct imports of private cross-domain internals from the order confirmation path.
  - [x] Preserve one atomic transaction for the full workflow.
  - [x] Preserve current API-visible behavior and current error semantics where practical.
  - [x] Keep the existing `_get_default_warehouse_id` race note visible if it is not fully solved in this story; do not silently broaden scope without tests.

- [x] **Task 5: Add focused backend regression coverage and verification commands** (AC4)
  - [x] Add a focused backend test proving the explicit model registry loads all mapped tables required by migrations/startup.
  - [x] Extend `backend/tests/domains/orders/test_order_confirmation.py` with confirmation-seam regressions that prove success, rollback, snapshot stamping, and audit behavior still hold after the refactor.
  - [x] Run focused validation commands and record them in the story file once implementation is complete.

### Review Findings

- [x] [Review][Patch] Add an explicit active-transaction guard to `create_invoice_in_transaction` [backend/domains/invoices/service.py:620]
- [x] [Review][Patch] Strengthen registry validation so it proves the live model-wiring surface, not just direct helper calls [backend/tests/common/test_model_registry.py:6]
- [x] [Review][Patch] Add a downstream confirmation failure regression that proves post-invoice failure leaves the order workflow uncommitted [backend/tests/domains/orders/test_order_confirmation.py:239]
- [x] [Review][Defer] Stock-adjustment exceptions still surface through the pre-existing confirmation path without explicit 409 mapping [backend/domains/inventory/services.py:645] — deferred, pre-existing
- [x] [Review][Defer] Fractional order-line quantities are still truncated during reservation because confirmation continues to coerce `Decimal` quantities to `int` [backend/domains/inventory/order_confirmation.py:67] — deferred, pre-existing

## Dev Notes

### Why This Belongs in Epic 1

- This is cross-cutting foundation work, not a new business feature.
- The affected seams sit below multiple domains: shared ORM registration, migration/bootstrap startup, and the main order-confirmation workflow.
- The story establishes maintainable architecture boundaries for later work, including any future inventory/invoice module decomposition.

### Architecture Alignment

- The approved architecture uses a FastAPI modular monolith where services may call each other directly inside one process. That supports explicit collaborator calls for mandatory confirmation steps.
- The same architecture also defines a domain-event/outbox direction for decoupled side effects. In this repo today, the event bus is only concretely wired for `StockChangedEvent`, so do not hide mandatory invoice creation or stock reservation behind implicit handler ordering in this story.
- Keep transaction ownership explicit. The order-confirmation workflow should remain atomic and easy to reason about.

### Repo Reality And Guardrails

- `backend/common/models/__init__.py` currently imports domain-owned ORM classes and is used as an implicit metadata-registration surface by `migrations/env.py` and `seed_user.py`.
- `backend/domains/orders/services.py::confirm_order()` currently imports `create_stock_adjustment`, `_create_invoice_core`, and `normalize_buyer_identifier` inline and mixes orchestration with order-owned state changes.
- `backend/common/events.py` currently defines only `DomainEvent` and `StockChangedEvent`; `backend/app/main.py` only imports `domains.inventory.handlers` at startup for handler registration.
- `backend/domains/inventory/services.py` and `backend/domains/invoices/service.py` are both large. Full concern-by-concern module decomposition is follow-on work, not required to finish this story.

### Implementation Direction

- Prefer a side-effect-only explicit model registry module over further expanding `common.models`.
- Prefer a thin order-owned use case plus public collaborator functions over private cross-domain reach-ins.
- Preserve the current confirmation workflow shape: resolve tenant-scoped customer/product data, stamp missing order-line snapshots, persist invoice, reserve stock, update status, write audit logs, return the reloaded order.
- Keep the order-confirmation response contract stable for existing routes/tests.

### Suggested File Targets

- `backend/common/model_registry.py` (new)
- `backend/common/models/__init__.py`
- `migrations/env.py`
- `seed_user.py`
- `backend/domains/orders/services.py`
- A focused collaborator module or promoted public function under `backend/domains/invoices/`
- A focused collaborator module or promoted public function under `backend/domains/inventory/`
- `backend/tests/domains/orders/test_order_confirmation.py`
- A new focused backend registry test file if needed

### Out Of Scope

- Full decomposition of `backend/domains/inventory/services.py` into multiple concern-specific modules
- Full decomposition of `backend/domains/invoices/service.py` into multiple concern-specific modules
- A generalized order-event pipeline or background workflow redesign
- Public API contract changes for order confirmation

## Project Structure Notes

- Follow repo reality instead of forcing a naming cleanup as part of this story. The codebase currently uses both `service.py` and `services.py`; do not expand scope into a package-wide rename.
- `common` should remain the shared kernel. Domain-owned ORM classes belong in their owning domain packages even if the SQLAlchemy metadata registry imports them for side effects.
- Keep helper extraction narrow and local to the confirmation seam. This story should reduce coupling, not create a second monolith under a new filename.

## References

- `_bmad-output/planning-artifacts/epic-1.md` - Epic 1 foundation scope and new Story 1.9 entry
- `docs/superpowers/specs/2026-03-30-erp-architecture-design-v2.md` - Sections 4.2 and 4.4 on modular-monolith service composition and domain-event/outbox direction
- `backend/common/models/__init__.py` - current shared model export surface
- `migrations/env.py` - current metadata-registration import path
- `seed_user.py` - current helper-script import path
- `backend/domains/orders/services.py` - current `confirm_order()` transaction script and `update_order_status()` delegation
- `backend/common/events.py` - current event bus surface
- `backend/app/main.py` - current startup handler registration
- `_bmad-output/implementation-artifacts/5-4-auto-generate-invoice-from-order.md` - original confirmation architecture intent
- `_bmad-output/implementation-artifacts/20-1-product-snapshot-on-order-line.md` - current snapshot-stamping contract during confirmation
- `backend/tests/domains/orders/test_order_confirmation.py` - current order-confirmation regression suite

---

## Dev Agent Record

### Agent Model Used

GPT-5.4

### Debug Log References

- `cd /Volumes/2T_SSD_App/Projects/UltrERP/backend && uv run pytest tests/common/test_model_registry.py tests/domains/orders/test_order_confirmation.py -q`
- `cd /Volumes/2T_SSD_App/Projects/UltrERP/backend && uv run ruff check common/model_registry.py common/models/__init__.py ../migrations/env.py ../seed_user.py domains/orders/services.py domains/invoices/service.py domains/inventory/order_confirmation.py tests/common/test_model_registry.py tests/domains/orders/test_order_confirmation.py tests/domains/orders/_helpers.py`

### Completion Notes List

- Added `backend/common/model_registry.py` and repointed Alembic plus `seed_user.py` to explicit ORM registration instead of `import common.models` side effects.
- Trimmed `backend/common/models/__init__.py` to common-owned exports only, removing re-exported domain-owned ORM classes from the shared kernel surface.
- Promoted a supported in-transaction invoice collaborator in `backend/domains/invoices/service.py` and added `backend/domains/inventory/order_confirmation.py` for stock reservation during order confirmation.
- Slimmed `backend/domains/orders/services.py::confirm_order()` to an order-owned coordinator while preserving tenant-scoped snapshot stamping, one atomic transaction, audit behavior, and the API-visible confirmation contract.
- Review follow-up added an explicit active-transaction guard for the public invoice collaborator, strengthened registry coverage to the full mapped table surface, and added a post-invoice reservation-failure regression using the fake-session rollback harness.
- Focused validation passed with `19` backend tests green and Ruff clean on the touched Story 1.9 slice.

### File List

- `backend/common/model_registry.py`
- `backend/common/models/__init__.py`
- `migrations/env.py`
- `seed_user.py`
- `backend/domains/invoices/service.py`
- `backend/domains/inventory/order_confirmation.py`
- `backend/domains/orders/services.py`
- `backend/tests/common/test_model_registry.py`
- `backend/tests/domains/orders/test_order_confirmation.py`
