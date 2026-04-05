# Story 15.4: Canonical Historical Transaction Import

Status: done

## Story

As a migration operator,
I want staged legacy headers and lines imported into UltrERP's canonical tables,
So that historical sales, purchase, inventory, and party data are available in the new system.

## Acceptance Criteria

**AC1:** Canonical import respects the live model boundaries  
**Given** normalized master data and product mappings are available  
**When** the CLI canonical-import phase runs  
**Then** implemented UltrERP domains receive historical data through a documented import layer  
**And** unsupported domains are routed to an explicit history/prep holding area instead of being dropped or forced into ad hoc live tables

**AC2:** Import order remains FK-safe  
**Given** parties, products, warehouses, and inventory are dependencies for transactions  
**When** historical data is imported  
**Then** canonical writes happen in dependency order  
**And** unresolved variant rows use the approved fallback path rather than violating foreign keys

**AC3:** Canonical records retain legacy lineage  
**Given** a historical row is imported into UltrERP  
**When** an operator or auditor inspects the imported record  
**Then** they can trace it back to the originating legacy table, source identifier, and import batch  
**And** later discrepancy reports can join back to the original legacy row deterministically

**AC4:** Import reruns remain safe  
**Given** the same tenant and cutoff window are imported again  
**When** the canonical import step reruns  
**Then** duplicate live records are not created  
**And** the batch outcome remains explainable from stored lineage and run metadata

## Tasks / Subtasks

- [x] **Task 1: Define the canonical target matrix** (AC1, AC2)
  - [x] Map normalized legacy entities to existing live-domain tables where those domains already exist
  - [x] Explicitly document where purchase-history data lands because the repo does not yet have a first-class purchase domain
  - [x] Keep tenant scoping and lineage requirements visible for every target table

- [x] **Task 2: Implement dependency-ordered import services** (AC2, AC3, AC4)
  - [x] Expose canonical import as a stable CLI subcommand instead of a route-only or notebook-only workflow
  - [x] Import parties, products, warehouses, and inventory before transactional history
  - [x] Import historical sales/order/invoice/payment-adjacent data through a dedicated import layer
  - [x] Reuse the mapping workflow from Story 15.3 for product resolution

- [x] **Task 3: Preserve lineage and replay safety** (AC3, AC4)
  - [x] Add lineage columns or sidecar mapping tables needed for deterministic source-to-canonical traceability
  - [x] Make reruns idempotent for the same batch scope
  - [x] Ensure partial failures are observable and recoverable

- [x] **Task 4: Add focused import tests** (AC1, AC2, AC3, AC4)
  - [x] Add batch-scoped tests covering dependency order, fallback-product behavior, and replay safety
  - [x] Add at least one test for a currently unsupported target domain so it lands in the documented holding area rather than disappearing

### Review Findings

- [x] [Review][Patch] Make canonical live IDs tenant-scoped [backend/domains/legacy_import/canonical.py:97]
- [x] [Review][Patch] Preserve full payment-history payloads in unsupported holding [backend/domains/legacy_import/canonical.py:1371]
- [x] [Review][Patch] Persist failed run and failed step telemetry outside the rolled-back import transaction [backend/domains/legacy_import/canonical.py:1678]
- [x] [Review][Patch] Add deterministic lineage assertions and failure-observability regressions to the canonical import tests [backend/tests/domains/legacy_import/test_canonical.py:307]

## Dev Notes

### Repo Reality

- UltrERP currently has implemented anchors for customers, inventory, orders, invoices, and payments.
- The repo does **not** currently expose a first-class purchase domain, so purchase-history migration must be handled deliberately rather than assumed into existence.

### Critical Warnings

- Do **not** invent half-integrated live purchase tables just to satisfy the migration story title.
- Do **not** bypass lineage tracking when writing live-domain rows.
- Do **not** import transactions before master entities and mappings are ready.

### Implementation Direction

- Keep historical import logic in the dedicated import domain, not spread across existing live-domain routes.
- Treat the canonical import phase as part of the same reviewed CLI surface that the skill will orchestrate.
- Use live-domain models where appropriate, but isolate batch/replay concerns inside the import layer.
- Document clearly which datasets land in live tables now and which remain in a migration-owned holding area pending future productization.

### Validation Follow-up

- Add replay tests for identical batch reruns and cutoff-window reruns.
- Add at least one lineage lookup assertion from a live canonical row back to a staged legacy row.

### References

- `_bmad-output/planning-artifacts/epics.md` - Epic 15 / Story 15.4 / FR59 / FR61
- `docs/legacy/migration-plan.md` - target import order and lineage expectations
- `backend/domains/customers/models.py` - current party/customer anchor
- `backend/common/models/product.py` - current product anchor
- `backend/common/models/warehouse.py` - current warehouse anchor
- `backend/common/models/inventory_stock.py` - current inventory anchor
- `backend/common/models/order.py` and `backend/common/models/order_line.py` - current order anchors
- `backend/domains/invoices/models.py` - current invoice anchor
- `backend/domains/payments/models.py` - current payment anchor

## Dev Agent Record

### Agent Model Used

GitHub Copilot (GPT-5.4)

### Completion Notes List

- Story is explicit that purchase history needs a documented landing zone because the repo does not yet have a purchase domain.
- Story keeps lineage and replay safety as first-class constraints rather than afterthoughts.
- Added `legacy-import canonical-import` plus a dedicated canonical import layer that writes deterministic historical rows into `customers`, `product`, `warehouse`, `inventory_stock`, `orders`, `order_lines`, `invoices`, and `invoice_lines` in dependency order.
- Preserved unsupported purchase and payment-adjacent history in `raw_legacy.unsupported_history_holding` and added deterministic traceability through `raw_legacy.canonical_record_lineage`, `canonical_import_runs`, and `canonical_import_step_runs`.
- Post-review hardening made canonical live IDs deterministic per tenant, preserved full payment-history holding payloads, and committed failed run/step telemetry even when the import transaction aborts.
- Documented the canonical landing matrix in `docs/legacy/canonical-import-target-matrix.md` and added Alembic revision `ww444yy44z65` for the canonical import support tables.
- Validation completed with `uv run pytest tests/domains/legacy_import/test_canonical.py` (7 passed), `uv run pytest tests/domains/legacy_import` (48 passed), and `uv run ruff check` on the touched canonical-import slice.

### File List

- backend/domains/legacy_import/canonical.py
- backend/domains/legacy_import/cli.py
- backend/domains/legacy_import/__init__.py
- backend/tests/domains/legacy_import/test_canonical.py
- docs/legacy/canonical-import-target-matrix.md
- docs/legacy/migration-plan.md
- migrations/versions/ww444yy44z65_create_canonical_import_support_tables.py

### Change Log

- 2026-04-05: Implemented canonical historical transaction import, documented the canonical target matrix, added canonical lineage and holding support tables, and validated the legacy import slice.
- 2026-04-05: Completed post-review hardening for tenant-scoped canonical IDs, payment-history holding payload preservation, failed-step observability, and stronger canonical import regressions.
