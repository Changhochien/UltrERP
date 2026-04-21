# Epic 27: Manufacturing Foundation

## Epic Goal

Add the minimally viable manufacturing foundation needed to define product recipes, launch work orders, and consume or produce stock without waiting for full ERPnext routing and shop-floor parity.

## Business Value

- Businesses can model and execute basic in-house production.
- Inventory and procurement gain a real demand signal from BOM and work-order flows.
- Epic 29 quality and traceability work gets a manufacturing context to integrate with.
- The roadmap stays honest about direct-transfer-first scope before advanced Job Card complexity.

## Scope

**Backend:**
- BOM records with submit workflow, materials list, and production-item references.
- Work orders with direct material transfer mode and finished-goods completion.
- Basic production planning from demand signals.

**Frontend:**
- BOM and work-order workspaces using shared list/detail patterns.
- Material requirement and production-status visibility.
- Guardrails that keep draft, submitted, in-process, and completed states legible.

**Data Model:**
- BOM headers, BOM items, and optional operation-ready hooks.
- Work-order status, quantity, and reservation/consumption fields.
- Production-plan-ready references to sales and inventory demand.

## Non-Goals

- Full Job Card and operation-routing parity in the first slice.
- Detailed capacity planning and workstation scheduling.
- Full subcontracting parity.
- Full manufacturing cost accounting.

## Technical Approach

- Treat BOM as a submittable master record, not an informal recipe note.
- Start with direct material transfer against the work order, matching the validated recommendation.
- Keep operation and Job Card hooks present but deferred until the direct mode is stable.
- Use existing stock movement and product models wherever possible.

## Key Constraints

- The validated report is explicit: full BOM and Work Order parity is high effort, but a minimally viable slice is medium.
- BOM approval must exist before work orders can consume it.
- Quality hooks should be designed to connect cleanly to Epic 29 rather than embedded prematurely.

## Dependency and Phase Order

1. BOM lands before Work Orders.
2. Direct-transfer work orders land before any Job Card expansion.
3. Production planning lands only after the BOM and work-order write model is stable.

---

## Story 27.1: BOM Master and Submission Workflow

- Add BOM headers, materials, and submission controls.
- Track active versus draft BOMs per manufactured item.
- Preserve clean versioning or replacement semantics when recipes change.

**Acceptance Criteria:**

- Given a BOM is drafted, it cannot drive production until it is submitted.
- Given a product recipe changes, the active BOM is explicit and historical BOMs remain traceable.
- Given procurement or production inspects a BOM, required materials are visible without ambiguity.

## Story 27.2: Work Orders With Direct Material Transfer

- Add work orders for a production item, BOM, quantity, and due date.
- Support direct transfer and completion without Job Card routing.
- Track work-order states such as submitted, not started, in process, completed, stopped, and cancelled.

**Acceptance Criteria:**

- Given a planner creates a work order, it references a submitted BOM and required quantity.
- Given production starts, material-transfer and completion state remain explicit.
- Given a work order is stopped or cancelled, inventory and downstream planning remain consistent.

## Story 27.3: Material Reservation, Consumption, and Finished Goods Completion

- Reserve or earmark required materials from available inventory.
- Consume raw materials and record finished-goods output against the work order.
- Surface shortages clearly for planners and warehouse staff.

**Acceptance Criteria:**

- Given enough raw materials exist, the work order can reserve and consume them deterministically.
- Given shortages exist, the work order surfaces the blocking components instead of failing silently.
- Given completion occurs, finished-goods inventory is updated with clear lineage to the work order.

## Story 27.4: Production Planning From Demand Signals

- Add a lightweight production-planning view that turns demand into proposed work orders.
- Reuse confirmed-order and inventory signals instead of inventing a second demand model.
- Keep planning recommendations explicit and reviewable before execution.

**Acceptance Criteria:**

- Given open demand exists for a manufactured item, planners can generate a proposed work order.
- Given a planner accepts or rejects a proposal, the action is explicit and auditable.
- Given multiple BOM-driven items compete for materials, planning still exposes shortages clearly.

## Story 27.5: Advanced Routing Extension Point

- Add the minimum model hooks needed for later operation routing and Job Card work.
- Keep those hooks inactive until the direct-transfer flow is stable.
- Document the migration path from direct work-order execution to operation-level tracking.

**Acceptance Criteria:**

- Given the current release uses direct mode only, the schema still leaves room for future operation records.
- Given a future Job Card slice is planned, it does not require destructive rework of the v1 manufacturing write model.
- Given current users interact with work orders, no inactive advanced-routing surface creates confusion.