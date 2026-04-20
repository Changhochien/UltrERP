# Epic 21 / Epic 22 Combined Implementation Sequence

Date: 2026-04-20
Project: UltrERP
Author: GitHub Copilot

## 1. Decision Summary

Epic 21 should not be completed end-to-end before Epic 22.

The correct delivery model is:

- land the order-domain behavior and workflow contract first
- land only the shared Epic 22 primitives that directly unblock the orders workspace
- finish the Epic 21 order-surface redesign and regression coverage on top of those shared primitives
- continue the broader Epic 22 foundation work after the order workflow is stable

This keeps ownership clean:

- Epic 21 owns order-domain behavior, workflow semantics, reporting semantics, and order-surface UX
- Epic 22 owns reusable UI primitives and shared frontend architecture

## 2. Ownership Rules

### Epic 21 owns

- preserving the current `pending -> confirmed -> shipped -> fulfilled/cancelled` lifecycle
- customer-linked order intake semantics
- confirmation semantics, including invoice creation and stock reservation timing
- fulfillment and billing presentation semantics
- order-specific filters, cues, badges, callouts, and reporting rules

### Epic 22 owns

- reusable toast infrastructure
- reusable breadcrumb infrastructure
- reusable date picker infrastructure
- shared Zod and react-hook-form architecture
- shared TanStackDataTable foundation
- shared spinner, quick-entry, and status-badge primitives

### Shared handoff rules

- Story 22.4 may migrate `OrderForm`, but it must preserve Story 21.2 behavior.
- Story 22.7 may use the orders list as its first pilot, but it must preserve Story 21.4 workflow cues and row interactions.
- Story 21.4 consumes shared toast and breadcrumb primitives from Epic 22 instead of creating local reusable versions.

## 3. Recommended Delivery Order

### Wave 1: Order behavior contract

1. Story 21.1 — Preserve Existing Order Lifecycle and Expose Derived Execution Signals
2. Story 21.2 — Customer-Linked Order Intake and Confirmation UX
3. Story 21.3 — Fulfillment and Billing Presentation Separation

Reason:

- These stories define the order-domain truth that later shared-UI and migration work must preserve.
- None of them require the reusable UI primitives from Epic 22 to establish the correct business behavior.

### Wave 2: Shared UI blockers for the orders workspace

4. Story 22.1 — Toast Notification System
5. Story 22.3 — Breadcrumb Navigation

Reason:

- These are the two reusable primitives that Story 21.4 directly consumes.
- Landing them here prevents duplicate local implementations on the orders surface.

### Wave 3: Finish the order-surface redesign

6. Story 21.4 — Orders Workspace UX Redesign and Shared Foundation Integration
7. Story 21.5 — Commission Tracking, Order Metadata, and Reporting Alignment
8. Story 21.6 — Audit, Permissions, and Regression Coverage

Reason:

- By this point the preserved order behavior is defined and the shared toast and breadcrumb primitives exist.
- Story 21.4 can now integrate those shared foundations cleanly.
- Story 21.6 closes after both the workspace redesign and the reporting alignment are stable.

### Wave 4: Shared table foundation follow-on

9. Story 22.7 — TanStackDataTable Foundation

Reason:

- The orders list can be used as the first migration target only after the order-specific UX contract is already clear.
- This avoids letting the table-foundation story take ownership of order-workflow behavior.

### Wave 5: Broader shared-form and UI foundation work

10. Story 22.2 — DatePicker and DateRangePicker Components
11. Story 22.4 — Zod Schema Centralization and Form Migration
12. Story 22.6 — Spinner, QuickEntryDialog, and StatusBadge

Parallel optional work:

13. Story 22.5 — CSS Cleanup - AlertFeed and CommandBar

Reason:

- These stories improve the broader frontend architecture and can continue after the orders workflow is no longer blocked.
- Story 22.4 should migrate `OrderForm` only after Story 21.2 behavior is already settled.
- Story 22.5 is independent and can run whenever bandwidth allows.

## 4. Explicit Do / Do Not Guidance

### Do

- do finish Stories 21.1 to 21.3 before the shared-form migration touches `OrderForm`
- do land Stories 22.1 and 22.3 before Story 21.4 completes
- do treat Story 22.7 as a foundation migration, not an order-workflow redesign
- do let Story 21.6 absorb regressions caused by the order-facing Epic 22 integrations that orders actually consume

### Do not

- do not block all of Epic 21 on all of Epic 22
- do not let Story 22.4 redefine the order intake or confirmation workflow
- do not let Story 22.7 redefine order-specific filters, readiness cues, billing cues, or row behavior
- do not ship duplicate local toast or breadcrumb implementations inside Epic 21

## 5. Minimum Cross-Epic Gate Set

The only hard cross-epic gates needed for Epic 21 are:

- Story 22.1 before Story 21.4 final integration
- Story 22.3 before Story 21.4 final integration

Everything else is either:

- independent of Epic 21 core behavior
- or a follow-on migration that must preserve behavior Epic 21 already established

## 6. Execution Note For Sprint Tracking

If sprint tracking needs a simple rule, use this:

`21.1 -> 21.2 -> 21.3 -> 22.1 + 22.3 -> 21.4 -> 21.5 -> 21.6 -> 22.7 -> 22.2 -> 22.4 -> 22.6`, with `22.5` schedulable independently.