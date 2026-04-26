# Story 27.4: Production Planning From Demand Signals

**Status:** review

**Story ID:** 27.4

**Epic:** Epic 27 - Manufacturing Foundation

---

## Story

As a production planner,
I want lightweight manufacturing recommendations derived from real demand,
so that I can review and launch work orders without inventing a second demand model.

---

## Problem Statement

UltrERP already has customer orders, inventory positions, and the beginnings of manufacturing master data, but it still has no planning surface that translates confirmed demand into proposed production. Without that bridge, work-order creation is manual and reactive, planners cannot see which manufactured items actually need replenishment, and shortages stay invisible until a work order is already being drafted.

ERPNext's Production Plan goes much further, but Epic 27 specifically calls for a lighter first slice before the formal production-plan record in Story 27.6. This story should therefore convert confirmed demand and current inventory signals into reviewable proposals without yet introducing the broader period-based production-plan workflow.

## Solution

Add a lightweight planning layer that:

- derives proposed manufacturing demand from confirmed order signals for manufactured items
- subtracts current on-hand stock, open manufacturing supply, and reservation-aware availability signals so proposals reflect actual shortfall rather than raw demand
- lets planners accept or reject each proposed work order explicitly with an audit trail

Keep the first slice narrow. Land proposal generation, review, and work-order creation while deferring formal production-plan records, forecast aggregation, capacity balancing, and material-request generation.

## Acceptance Criteria

1. Given open demand exists for a manufactured item, when the planner runs planning, then the system proposes a work order quantity derived from confirmed demand and current supply signals.
2. Given a planner reviews a proposal, when they accept or reject it, then the action is explicit, persisted, and auditable instead of silently mutating demand state.
3. Given multiple BOM-driven items compete for limited materials, when proposals are generated, then the response exposes shortages or blocked components clearly for the planner.
4. Given a planner accepts a proposal, when the resulting work order is created, then it links back to the proposal and demand source used to justify it.

## Tasks / Subtasks

- [ ] Task 1: Implement demand-to-proposal planning queries. (AC: 1, 3)
  - [ ] Add planning queries that aggregate confirmed sales-order demand for manufactured products.
  - [ ] Subtract current on-hand inventory and open work-order supply so proposal quantity reflects net required production.
  - [ ] Use reservation-aware material availability from Story 27.3 when surfacing component shortages so planning does not treat already-allocated stock as free supply.
  - [ ] Resolve the active submitted BOM for each manufactured item before proposal generation.
  - [ ] Return shortage context for blocking raw materials where current BOM component availability is insufficient.
- [ ] Task 2: Add proposal persistence and review audit. (AC: 2, 4)
  - [ ] Add a `ManufacturingProposal` or equivalent review record under the manufacturing domain.
  - [ ] Track proposal status such as proposed, accepted, rejected, and stale.
  - [ ] Persist acceptance or rejection reason, demand source reference, and generated work-order linkage where applicable.
- [ ] Task 3: Expose planning APIs and proposal actions. (AC: 1-4)
  - [ ] Add endpoints to generate proposals, list proposals, fetch proposal detail, and accept or reject a proposal.
  - [ ] On acceptance, create the linked work order through the Story 27.2 service instead of duplicating work-order logic in the planning layer.
  - [ ] Return enough demand and shortage detail for the frontend to explain each recommendation.
- [ ] Task 4: Build the lightweight planning view. (AC: 1-4)
  - [ ] Add `src/pages/manufacturing/ProductionPlanningPage.tsx` for the lightweight planning workspace.
  - [ ] Show demand source, proposed quantity, current stock, open manufacturing supply, and blocking shortages in the proposal table.
  - [ ] Add explicit accept or reject actions with confirmation and reason capture.
  - [ ] Link accepted proposals to the created work-order detail page.
- [ ] Task 5: Add focused tests and validation. (AC: 1-4)
  - [ ] Add backend tests for proposal generation, shortage exposure, stale-proposal handling after new stock or work orders arrive, and accept or reject audit.
  - [ ] Add frontend tests for proposal rendering, shortage visibility, and accept or reject workflows.
  - [ ] Validate that the planning layer reuses existing order and work-order services rather than introducing a separate demand state machine.

## Dev Notes

### Context

- This story intentionally precedes the formal `ProductionPlan` record in Story 27.6.
- UltrERP already has sales-order demand and inventory availability signals; this story should reuse those rather than inventing a new demand ledger.
- Story 27.1 provides submitted BOM selection and Story 27.2 provides the work-order target document that accepted proposals should create.
- Story 27.3 provides the reservation-aware stock picture needed for reliable shortage output.
- Story 27.5 provides the routing and workstation baseline so this slice can follow the epic phase order while still staying lighter than the formal plan workflow in Story 27.6.

### Architecture Compliance

- Keep the proposal-generation logic inside the manufacturing domain, but read confirmed demand from the existing orders domain rather than copying sales-order data.
- Make proposal review explicit and auditable. A planner should accept or reject a recommendation, not trigger hidden automatic work-order creation.
- Keep proposal records lightweight and replaceable; the formal period-based planning model belongs to Story 27.6.
- Do not plan against raw unallocated stock if Story 27.3 reservation data exists; shortage math should use the same allocatable view of materials that execution uses.
- Story 27.6 should group, bulk-manage, or firm these proposals rather than inventing a second parallel proposal entity.

### Implementation Guidance

- Likely backend files:
  - `backend/domains/manufacturing/models.py`
  - `backend/domains/manufacturing/planning_service.py`
  - `backend/domains/manufacturing/routes.py`
  - `backend/domains/manufacturing/schemas.py`
  - `backend/domains/orders/services.py`
  - `backend/domains/orders/routes.py`
  - `backend/common/models/order.py`
  - `backend/common/models/order_line.py`
  - `migrations/versions/*_manufacturing_proposals.py`
- Likely frontend files:
  - `src/lib/api/manufacturing.ts`
  - `src/domain/manufacturing/hooks/useProductionPlanning.ts`
  - `src/domain/manufacturing/components/ProductionProposalTable.tsx`
  - `src/pages/manufacturing/ProductionPlanningPage.tsx`
- Reuse existing table and status-chip patterns from orders and procurement.
- If proposal recalculation invalidates earlier proposals, mark them stale explicitly rather than deleting them silently.

### What NOT to implement

- Do **not** implement formal production-plan headers, plan periods, or forecast lines here; Story 27.6 owns that scope.
- Do **not** implement capacity scheduling, optimizer logic, or workstation balancing in this story.
- Do **not** generate procurement documents or material requests automatically in this slice.
- Do **not** invent a second demand model outside confirmed orders and current supply signals.

### Testing Standards

- Include a regression proving proposal quantity is net of on-hand stock and open manufacturing supply.
- Include a regression proving shortage detail is returned for blocked components.
- Include a regression proving accepted proposals create linked work orders and rejected proposals remain auditable.

## Dependencies & Related Stories

- **Depends on:** Story 27.1, Story 27.2, Story 27.3, Story 27.5
- **Related to:** Story 27.6 for the formal production-plan record that should build on this proposal layer rather than duplicate it
- **Cross-epic:** Reuses confirmed-order demand from the orders domain and current stock visibility from Epic 4.

## References

- `../planning-artifacts/epic-27.md`
- `plans/2026-04-21-UltrERP-ERPNext-Comprehensive-Gap-Analysis-v1.md`
- `reference/erpnext-develop/erpnext/manufacturing/doctype/production_plan/production_plan.json`
- `backend/common/models/order.py`
- `backend/common/models/order_line.py`
- `backend/domains/orders/routes.py`
- `backend/common/models/inventory_stock.py`
- `https://docs.frappe.io/erpnext/user/manual/en/production-plan`
- `CLAUDE.md`

---

## Dev Agent Record

**Status:** ready-for-dev
**Last Updated:** 2026-04-26

### Completion Notes List

- 2026-04-26: Story drafted from Epic 27 planning goals, ERPNext production-plan research, and the existing UltrERP orders plus inventory demand signals.

### File List

- `_bmad-output/implementation-artifacts/27-4-production-planning-from-demand-signals.md`

**Implementation Notes:**
- ManufacturingProposal model and services implemented
- Proposal generation from sales order demand signals
- Net requirement calculation (demand - stock - open WO supply)
- Shortage exposure for BOM materials
- Accept/reject workflow with audit trail