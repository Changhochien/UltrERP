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
- Routing and workstation definitions with operation sequences.
- Production planning from demand signals and capacity constraints.
- Downtime tracking and OEE (Overall Equipment Effectiveness) calculation.

**Frontend:**
- BOM and work-order workspaces using shared list/detail patterns.
- Routing and workstation management interfaces.
- Production planning and scheduling views.
- Downtime and OEE dashboard.

**Data Model:**
- BOM headers, BOM items, and operation definitions.
- Work-order status, quantity, operation steps, and reservation/consumption fields.
- Workstation capacity and operation time definitions.
- Downtime records categorized by reason.
- OEE calculation components: Availability, Performance, Quality.

## Non-Goals

- Full Job Card and operation-routing parity in the first slice.
- Detailed capacity planning and workstation scheduling.
- Full subcontracting parity.
- Full manufacturing cost accounting.

## Technical Approach

- Treat BOM as a submittable master record, not an informal recipe note.
- Start with direct material transfer against the work order, matching the validated recommendation.
- Implement routing as operation sequences linked to workstations with time and cost estimates.
- Use existing stock movement and product models wherever possible.
- Calculate OEE from downtime data to provide equipment effectiveness visibility.

## Key Constraints

- The validated report is explicit: full BOM and Work Order parity is high effort, but a minimally viable slice is medium.
- BOM approval must exist before work orders can consume it.
- Quality hooks should be designed to connect cleanly to Epic 29 rather than embedded prematurely.
- Routing and workstation work extends Epic 27 beyond direct-transfer mode.

## 2026-04-27 Quality Review Summary

1. Story 27.1 review fixed the BOM active-version metadata mismatch so the ORM now matches the migration's partial unique index and preserves historical revisions.
2. Stories 27.2 and 27.3 review mounted the manufacturing work-order surface in the app shell and added a detail workspace for lifecycle, reservation, transfer, and completion actions.
3. Story 27.4 review fixed proposal generation to use the real confirmed-order demand model, stale superseded proposals, and return typed shortage payloads.
4. Story 27.5 review fixed routing labor-cost calculation to use workstation hourly rates and exposed a routing detail calculator in the frontend.
5. Story 27.6 review populated production-plan demand, stock, open-work-order, shortage, and capacity fields instead of relying on empty defaults.
6. Story 27.7 review mounted the OEE dashboard and manufacturing navigation so the dashboard is reachable in the protected app shell.
7. Residual-gap review for Story 27.7 added downtime/OEE payload validation so impossible intervals, counts, and negative runtime telemetry are rejected before persistence.
8. Focused validation now covers reviewed backend slices with manufacturing unit tests, frontend build, and locale parity checks.

## Dependency and Phase Order

1. BOM lands before Work Orders and Routing.
2. Direct-transfer work orders land before operation-level tracking.
3. Routing and workstations land after basic work orders are stable.
4. Production planning lands after routing with time estimates.
5. Downtime and OEE tracking can land independently for equipment visibility.

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

## Story 27.5: Routing and Workstation Management

- Add Workstation records with name, description, cost per hour, and capacity.
- Define Routing records with operation sequences linked to work orders.
- Add operation steps: operation name, workstation, time (setup, run, fixed, variable), and sequence order.
- Link routing to BOM for manufactured items with operation requirements.
- Calculate planned operation times and costs for work orders using routing.
- Support operation overlapping and sequencing for work order scheduling.

**Acceptance Criteria:**

- Given a workstation is configured with hourly cost, work orders using it calculate operation labor cost correctly.
- Given a routing is defined for a product, work orders inherit operation sequence and time estimates.
- Given a work order uses a routing with multiple operations, the planned production time reflects setup plus run times.
- Given operation costs are configured on routing, total production cost is estimable before work order execution.
- Given a work order is scheduled, the system can display operation timeline based on workstation availability.
- Given production requires specific workstations, the routing ensures operations are assigned correctly.

## Story 27.6: Production Plan and Demand Aggregation

- Add production plan records that aggregate demand from sales orders and forecasts.
- Generate proposed work orders from production plan based on BOM and material availability.
- Support make-to-order and make-to-stock production strategies.
- Provide visibility into production capacity vs. demand load.
- Allow plan approval and firming of proposed work orders.
- Track planned vs. actual production completion for plan accuracy reporting.

**Acceptance Criteria:**

- Given sales orders exist for manufactured items, the production plan aggregates total demand.
- Given material shortages exist, the production plan flags items that cannot be fully produced.
- Given a planner reviews the production plan, proposed work orders can be created, modified, or cancelled.
- Given a production plan is firmed, proposed work orders become firm work orders.
- Given production capacity is limited, the plan highlights overload situations and allows prioritization.
- Given the plan period ends, actual vs. planned production is reportable for planning accuracy analysis.

## Story 27.7: Downtime Tracking and OEE Calculation

- Add downtime recording linked to workstations or work orders.
- Categorize downtime by type: Planned Maintenance, Unplanned Breakdown, Changeover, Material Shortage, Quality Hold.
- Record downtime start time, end time, and duration.
- Calculate OEE components: Availability (actual run time / planned run time), Performance (ideal cycle time / actual cycle time), Quality (good units / total units).
- Compute OEE score as product of the three components.
- Provide OEE dashboard showing trends, downtime Pareto analysis, and improvement tracking.

**Acceptance Criteria:**

- Given a workstation experiences unplanned downtime, the operator can log the event with type and duration.
- Given downtime is logged, the system calculates impact on equipment availability.
- Given production data exists (good units, total units, cycle times), the system calculates OEE components.
- Given an OEE dashboard is viewed, current OEE score and trend over time are visible.
- Given a downtime Pareto report is generated, the system ranks downtime causes by frequency and duration.
- Given OEE improves or degrades, the trend visualization shows the change clearly for management review.
