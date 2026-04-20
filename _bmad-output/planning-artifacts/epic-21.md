# Epic 21: Orders Workflow Clarification and Gap Closure

## Epic Goal

Keep the current superior order workflow intact while closing the validated order-domain gaps from the ERPnext research. Epic 21 should make the existing pre-commit, confirmation, fulfillment, and billing flow clearer and more complete without turning this into a replacement for the higher-priority CRM, purchasing, or full-sector backlog.

## Business Value

- Preserve the proven confirmation flow that already creates invoices and reserves stock atomically.
- Make sales, warehouse, and finance users read the same order correctly without decoding one overloaded status badge.
- Close the real order gaps confirmed by research: customer-linked order intake UX, order-to-invoice continuity, commission tracking, backorder visibility, and reporting alignment.
- Leave a clean extension point for future Quotation-to-Order work without pulling CRM implementation into this epic.

## Scope

**Backend:**
- Keep the existing persisted order `status` lifecycle and confirmation transaction as the write-side source of truth in v1.
- Expose derived commercial, fulfillment, and billing signals for API and UI consumers from the existing order status, invoice linkage, payment state, and timestamps.
- Add low-effort order-domain extensions validated by the research, especially commission tracking, reporting-safe semantics, and any lightweight additive metadata that directly supports the orders workflow.
- Preserve committed-order analytics semantics by keying on confirmation rather than creation time.

**Frontend:**
- Add or complete the flow to create an order from an existing customer context.
- Redesign the orders workspace so the pre-commit stage, fulfillment progress, billing context, invoice linkage, reservation state, and backorder cues are legible.
- Add timeline, grouped actions, and order-specific workflow cues, while consuming shared breadcrumb and toast primitives from Epic 22 instead of creating local reusable versions.

**Data Model:**
- Prefer additive fields for genuine missing capabilities only, such as commission tracking and optional order metadata.
- Avoid a mandatory three-column lifecycle migration unless later implementation proves the current persisted model cannot support the required UX and reporting behavior.

## Non-Goals

- Lead, Opportunity, and Quotation implementation
- Purchase Order, GRN, RFQ, and Supplier Quotation implementation
- Full multi-currency rollout across all transaction domains
- Broad UI cleanup unrelated to the orders surface
- Creation of reusable UI primitives already owned by Epic 22
- Full ERPnext Sales Order parity in one epic

## Technical Approach

- Treat `pending` as the existing query-compatible state. It is already the editable, pre-commit stage in the live code and should be preserved as such.
- Keep confirmation atomic with invoice creation and stock reservation. This behavior is superior to the stale research claim that UltrERP has no stock reservation and must not be regressed.
- Separate fulfillment from billing first in the API/view model and workspace UX. Only add deeper persistence changes if a concrete write-side limitation remains after the UX and reporting gaps are closed.
- Fix the validated order gaps at the root:
  - customer-linked order intake UX
  - order-to-invoice continuity in list/detail flows
  - commission tracking
  - backorder and readiness cues
  - reporting semantics keyed to `confirmed_at`
- Keep future Quotation-to-Order flow as an integration point for a later CRM epic rather than implementing CRM scope inside Epic 21.

## Key Constraints

- Invoice creation stays on confirmation.
- Stock reservation stays on confirmation.
- No regression to the existing `pending -> confirmed -> shipped -> fulfilled/cancelled` order lifecycle.
- No breaking API change without compatibility for current consumers.
- Reusable toast, breadcrumb, form-architecture, and table-foundation work is owned by Epic 22; Epic 21 only consumes those primitives where the orders workflow needs them.
- Broader research findings remain inputs to follow-on epics, not hidden scope creep inside Epic 21.

## Dependency and Phase Order

1. Land Stories 21.1 to 21.3 first. They preserve the current order lifecycle and define the order-specific behavior contract without waiting on Epic 22.
2. Land shared breadcrumb and toast primitives from Epic 22 before the final shared-foundation integration work in Story 21.4, so the orders workspace consumes reusable components instead of creating duplicates.
3. Story 21.4 owns the order-specific workflow redesign, while Story 22.7 owns the TanStackDataTable foundation. If the orders list is used as the first TanStack pilot, 22.7 must preserve the order-specific behavior contract from Epic 21 rather than redefine it.
4. Story 21.5 can proceed after Stories 21.1 to 21.3 because commission and reporting alignment are primarily domain concerns, not shared-UI concerns.
5. Story 21.6 closes after the workflow redesign and reporting alignment are stable, absorbing any audit or regression coverage needed for shared Epic 22 primitives that orders actually consume.
6. Leave CRM quotation conversion and wider sector gaps for follow-on epics.

## Cross-Epic Resolution With Epic 22

- Epic 21 owns order-domain behavior and order-specific UX semantics.
- Epic 22 owns reusable UI primitives and architecture: Toast, Breadcrumb, DatePicker, Zod form architecture, StatusBadge, QuickEntryDialog, and TanStackDataTable.
- Story 21.2 may change `OrderForm` behavior on the current form stack. Story 22.4 may later migrate that same form to the shared Zod and react-hook-form architecture, but it must preserve the customer-linked intake and confirmation semantics defined by Epic 21.
- Story 21.4 may integrate shared toast and breadcrumb support, but it does not own those primitives.
- Story 22.7 may use the orders list as its first migration target, but it owns only the table foundation and migration mechanics. The order-specific filters, cues, badges, and workflow guidance remain owned by Epic 21.

---

## Story 21.1: Preserve Existing Order Lifecycle and Expose Derived Execution Signals

**Context:** The live code already uses `pending` as an editable pre-commit state and confirms orders atomically with invoice creation and stock reservation. The first story should preserve that superior behavior, document it clearly, and expose the execution dimensions the UI and reporting layers need without forcing a migration-first rewrite.

**R1 - Preserve write-side truth**
- Keep the persisted `status` lifecycle as the source of truth in v1.
- Preserve `confirmed_at`, `invoice_id`, and the existing confirmation transaction.

**R2 - Expose derived execution signals**
- Add derived commercial, fulfillment, and billing read signals in order schemas and services so list/detail surfaces can present ERPnext-like clarity.
- Make the derivation rule explicit and reusable across list, detail, and reporting consumers.

**R3 - Avoid destructive migration**
- Do not introduce a mandatory lifecycle refactor in this story.
- Allow additive fields only where they represent genuinely missing capability rather than a relabeling of the current flow.

**Acceptance Criteria:**

**Given** a pending order exists
**When** list or detail responses are serialized
**Then** the API exposes a pre-commit commercial view without changing the stored status model

**Given** a confirmed order with an invoice exists
**When** it is serialized
**Then** fulfillment and billing cues are derivable without mutating the current confirmation semantics

**Given** the existing confirm path is exercised
**When** tests run
**Then** invoice creation and stock reservation still happen atomically on confirmation

---

## Story 21.2: Customer-Linked Order Intake and Confirmation UX

**Context:** The research shows the real intake gap is not the absence of a pre-commit state, but the absence of a polished workflow for creating orders from an existing customer and confirming them with clear invoice and reservation language.

**R1 - Intake flow from existing customer**
- Make it straightforward to create an order from an existing customer context.
- Preserve pricing, payment terms, notes, and stock visibility during intake.

**R2 - Clear confirmation workflow**
- Present confirmation explicitly as the moment that creates the invoice and reserves stock.
- Surface retryable failure states if invoice creation or reservation fails.

**R3 - Order and invoice continuity**
- Keep invoice linkage obvious after confirmation.
- Do not invent a separate CRM quotation workflow in this story.

**Acceptance Criteria:**

**Given** a user creates an order from an existing customer
**When** the save succeeds
**Then** the order enters the existing pending state and is visible in the orders workspace

**Given** a pending order is confirmed
**When** the operation succeeds
**Then** the UI makes clear that invoice creation and stock reservation occurred

**Given** confirmation fails
**When** the user remains in the order flow
**Then** the order stays editable and the error is actionable

---

## Story 21.3: Fulfillment and Billing Presentation Separation

**Context:** The confirmed order lifecycle already distinguishes commitment from later execution in practice, but the current workspace still overloads one status label. This story separates fulfillment actions from billing navigation in presentation and workflow language.

**R1 - Warehouse-focused fulfillment actions**
- Present shipped and fulfilled transitions as fulfillment actions, not generic status changes.
- Keep billing navigation read-only from the warehouse action rail.

**R2 - Billing clarity**
- Make invoice linkage, payment state, and reservation state visible without suggesting shipment creates invoices.
- Keep `confirmed_at` as the commercial commitment milestone.

**R3 - Backorder and readiness cues**
- Show ready-to-ship and backorder cues directly on the detail page.
- Keep edge states explicit for pending, confirmed, shipped, fulfilled, and cancelled orders.

**Acceptance Criteria:**

**Given** a confirmed order is opened
**When** the detail page renders
**Then** warehouse actions are visually separated from billing and invoice navigation

**Given** a shipped or backordered order is viewed
**When** the user inspects the workflow cues
**Then** fulfillment progress and backorder context are clear without changing billing meaning

**Given** fulfillment transitions occur
**When** regression tests run
**Then** billing semantics remain tied to confirmation and payment state, not shipment

---

## Story 21.4: Orders Workspace UX Redesign and Shared Foundation Integration

**Context:** The validated research confirms that the orders surface needs stronger filters, clearer cues, breadcrumbs, and reliable user feedback. This story is the centerpiece of Epic 21.

**R1 - Workspace clarity**
- Show primary commercial meaning plus supporting fulfillment and billing cues.
- Add fast filters for operational slices such as pending intake, ready to ship, shipped not completed, and invoiced not paid.

**R2 - Detail-page guidance**
- Add breadcrumb navigation, milestone timeline, grouped actions, invoice links, and contextual callouts.
- Surface reservation and backorder cues where users make decisions.

**R3 - Shared primitives used by orders**
- Introduce toast feedback and any minimal shared UI support the orders workflow directly needs.
- Do not use this story as a vehicle for unrelated app-wide UI cleanup.

**Acceptance Criteria:**

**Given** the orders list is loaded
**When** a user scans rows and filters
**Then** they can distinguish commercial, fulfillment, and billing meaning at a glance

**Given** a user completes or fails a key order action
**When** the UI responds
**Then** feedback is explicit and immediate

**Given** a user navigates between the orders list and detail pages
**When** they orient themselves in the workflow
**Then** breadcrumb, timeline, and grouped actions make the path legible

---

## Story 21.5: Commission Tracking, Order Metadata, and Reporting Alignment

**Context:** The research identified low-effort order-domain gaps that belong inside Epic 21 because they extend the existing Order surface directly, unlike CRM or purchasing.

**R1 - Commission tracking**
- Add `sales_team`-style commission tracking to orders.
- Compute and expose total commission plus the data needed for salesperson reporting.

**R2 - Order metadata**
- Add low-effort order metadata, such as UTM fields, only if it is wired into a real consumer in this epic.
- Keep optional metadata additive and non-disruptive.

**R3 - Reporting semantics**
- Align analytics and reporting so commercially committed orders key off confirmation, not order creation alone.
- Sweep order reporting consumers for stale assumptions about status meaning.

**Acceptance Criteria:**

**Given** an order carries commission assignments
**When** it is viewed or reported on
**Then** commission allocations and totals are available

**Given** reporting counts committed orders
**When** metrics are computed
**Then** pending intake orders are excluded and confirmed orders remain counted correctly

**Given** optional order metadata is added
**When** APIs and tests are updated
**Then** existing order workflows continue to behave compatibly

---

## Story 21.6: Audit, Permissions, and Regression Coverage

**Context:** Epic 21 preserves a working financial commitment flow while expanding the workspace and order-domain capabilities. The safety net must focus on keeping the superior current behavior intact.

**R1 - Audit continuity**
- Keep confirmation and invoice creation correlated as one business action chain.
- Audit fulfillment changes, commission mutations, and any new order metadata writes where they affect workflow meaning.

**R2 - Permissions**
- Preserve the existing confirmation permissions.
- Ensure warehouse actions, finance visibility, and sales editing stay consistent with the clarified workflow.

**R3 - Regression coverage**
- Add tests around confirmation, reservation, fulfillment labeling, reporting semantics, and commission tracking.
- Protect against drift toward invoice-on-shipment or creation-time analytics counting.

**Acceptance Criteria:**

**Given** a pending order is confirmed
**When** the transition succeeds
**Then** the audit trail still links order confirmation and invoice creation under the same business action chain

**Given** workflow and reporting tests run
**When** Epic 21 changes are exercised
**Then** the preserved confirmation semantics and the newly closed order gaps both remain covered