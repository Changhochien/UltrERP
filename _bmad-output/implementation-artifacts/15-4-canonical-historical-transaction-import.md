# Story 15.4: Canonical Historical Transaction Import

Status: ready-for-dev

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

- [ ] **Task 1: Define the canonical target matrix** (AC1, AC2)
  - [ ] Map normalized legacy entities to existing live-domain tables where those domains already exist
  - [ ] Explicitly document where purchase-history data lands because the repo does not yet have a first-class purchase domain
  - [ ] Keep tenant scoping and lineage requirements visible for every target table

- [ ] **Task 2: Implement dependency-ordered import services** (AC2, AC3, AC4)
  - [ ] Expose canonical import as a stable CLI subcommand instead of a route-only or notebook-only workflow
  - [ ] Import parties, products, warehouses, and inventory before transactional history
  - [ ] Import historical sales/order/invoice/payment-adjacent data through a dedicated import layer
  - [ ] Reuse the mapping workflow from Story 15.3 for product resolution

- [ ] **Task 3: Preserve lineage and replay safety** (AC3, AC4)
  - [ ] Add lineage columns or sidecar mapping tables needed for deterministic source-to-canonical traceability
  - [ ] Make reruns idempotent for the same batch scope
  - [ ] Ensure partial failures are observable and recoverable

- [ ] **Task 4: Add focused import tests** (AC1, AC2, AC3, AC4)
  - [ ] Add batch-scoped tests covering dependency order, fallback-product behavior, and replay safety
  - [ ] Add at least one test for a currently unsupported target domain so it lands in the documented holding area rather than disappearing

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
