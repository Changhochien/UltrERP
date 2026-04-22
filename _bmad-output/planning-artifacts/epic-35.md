# Epic 35: Workflow Automation Engine

## Epic Goal

Add a generic workflow engine that allows administrators to define custom approval chains, document state transitions, and automated notifications without code changes — enabling UltrERP to support diverse business processes beyond the pre-built order and approval flows.

## Business Value

- Administrators can create custom approval workflows for expense reports, purchase requests, leave applications, and other business processes.
- Document state transitions become configurable instead of hard-coded.
- Notifications trigger automatically when workflow states change.
- Business process automation stops requiring developer intervention for routine workflow changes.
- UltrERP gains ERPNext-equivalent workflow capabilities for process customization.

## Scope

**Backend:**
- Workflow definition model with states, transitions, and actions.
- Workflow engine that evaluates conditions and executes transitions.
- Notification triggers on state changes.
- Workflow history and audit trail.
- Document state field on applicable transaction types.

**Frontend:**
- Workflow definition builder UI for administrators.
- Workflow visualization (state diagram).
- Document workflow status display and action buttons.
- Workflow history view on documents.

**Data Model:**
- `Workflow` — name, document_type, states, transitions, is_active.
- `WorkflowState` — name, state_type (start, middle, end), style.
- `WorkflowTransition` — from_state, to_state, condition, action.
- `WorkflowHistory` — document, workflow, current_state, previous_state, actor, timestamp.

## Non-Goals

- Complex workflow branching with parallel approvals (v1 is sequential).
- Workflow version migration for in-flight documents.
- Sub-workflow nesting.
- Time-based workflow escalation (use Epic 28 SLA instead).

## Technical Approach

- Treat workflow as a state machine with explicit transitions.
- Evaluate transition conditions using a safe expression evaluator (no arbitrary Python execution).
- Execute workflow actions (notifications, field updates) after successful transitions.
- Store workflow state on the document as a single field.
- Keep workflow history immutable for audit.

## Key Constraints

- Workflow definitions must be versioned; active version applies to documents.
- Transition conditions must be simple field comparisons (no complex logic in v1).
- Epic 6 (Approval System) is a prerequisite — approval requests use workflow engine.
- Workflows should integrate with existing RBAC (Epic 11) for role-based actions.

## Dependency and Phase Order

1. Workflow engine core (Stories 35.1-35.3) lands before approval workflow integration.
2. Notification system (Story 35.4) depends on Epic 6 (Approval System) for notification channels.
3. Admin UI (Story 35.5) lands after core engine is tested.
4. Epic 35 can proceed in parallel with Epics 21-32 once Epic 6 (Approval) is stable.

---

## Story 35.1: Workflow Definition Model and State Machine

- Add `Workflow` records with name, document type, and active status.
- Define `WorkflowState` records: start, middle, end states with optional styling.
- Define `WorkflowTransition` records: source state, target state, condition expression, allowed roles.
- Validate workflow: each workflow must have exactly one start state and at least one end state.
- Validate transitions: no orphaned transitions, no circular paths without exit.
- Support workflow versioning: inactive workflows can be edited; active workflow is locked.

**Acceptance Criteria:**

- Given a workflow is created with start, middle, and end states
- When the workflow is saved
- Then validation confirms exactly one start and at least one end state exists

- Given a workflow with transitions is saved
- When it contains orphaned transitions or circular paths without exit
- Then the system returns a validation error

- Given a workflow version is active
- When an admin attempts to edit it
- Then the system prevents modification (new version required)

---

## Story 35.2: Workflow Engine Core and Transition Evaluation

- Add workflow engine service that evaluates document state against transitions.
- Implement safe condition expression evaluator: `field == value`, `field > value`, `field in [values]`.
- Execute transitions: update document state field, record history.
- Block transitions when conditions are not met or user lacks permission.
- Support conditional actions on transition: update fields, send notifications.
- Handle transition errors gracefully: log, notify admin, do not leave document in invalid state.

**Acceptance Criteria:**

- Given a document is in state A with a valid transition to state B
- When the transition is triggered
- Then the document state updates to B and history is recorded

- Given a transition has a condition that evaluates to false
- When the transition is triggered
- Then the transition is blocked and the user sees an error

- Given a transition has an allowed_roles constraint
- When a user without the required role triggers the transition
- Then the transition is blocked

---

## Story 35.3: Document Workflow State Integration

- Add `workflow_state` field to applicable transaction doctypes.
- Integrate workflow engine into document save and state change hooks.
- Display current workflow state on document forms and list views.
- Show available transitions based on current state and user role.
- Trigger transitions from UI buttons or API calls.
- Support manual state override by admin (with audit).

**Acceptance Criteria:**

- Given a transaction doctype has workflow integration enabled
- When the document loads
- Then the current workflow state is displayed

- Given a user is on a document with available transitions
- When they click a transition button
- Then the workflow engine evaluates and executes the transition

- Given a document transitions to a new state
- When the transition is successful
- Then the workflow history shows: previous_state, new_state, actor, timestamp

---

## Story 35.4: Workflow Notifications and Alerts

- Add notification action type to workflow transitions.
- Define notification templates per transition: recipient role, subject, body.
- Support variable substitution in templates: `{{document.number}}`, `{{actor.name}}`, `{{state.label}}`.
- Send notifications through Epic 6 notification channels (in-app, email, LINE).
- Track notification delivery status.
- Support escalation notifications (remind after X hours if state unchanged).

**Acceptance Criteria:**

- Given a transition has a notification action configured
- When the transition executes
- Then the notification is queued for delivery

- Given a notification template contains variables
- When the notification is sent
- Then all variables are substituted with actual values

- Given a transition action requires escalation
- When the state remains unchanged after the configured time
- Then a reminder notification is sent

---

## Story 35.5: Workflow Builder Admin UI

- Add workflow definition workspace for administrators.
- Visual workflow editor: state boxes connected by transition arrows.
- Drag-and-drop state and transition creation.
- Condition builder UI: field selector, operator, value input.
- Transition action configuration: notification, field update.
- Preview workflow on sample documents before activation.
- Workflow test mode: execute transitions without affecting production data.

**Acceptance Criteria:**

- Given an admin opens the workflow builder
- When they create states and connect them with transitions
- Then the workflow diagram updates in real-time

- Given an admin configures a transition condition
- When they use the condition builder UI
- Then the system generates the correct condition expression

- Given a workflow is in test mode
- When transitions are executed
- Then no production data is modified and test results are logged

---

## Story 35.6: Workflow Audit Trail and Reporting

- Record all workflow state changes with full context.
- Generate workflow analytics: average time per state, bottleneck identification.
- Audit log integration: workflow changes are logged with actor, timestamp, before/after.
- Export workflow history for compliance reporting.
- Support workflow performance comparison across document types.

**Acceptance Criteria:**

- Given a workflow history is requested for a document
- When the history is retrieved
- Then it includes: previous_state, new_state, actor, timestamp, transition_condition, action_results

- Given a manager requests workflow analytics
- When the report is generated
- Then it shows average time in each state and identifies bottlenecks

- Given an audit requires workflow change records
- When the audit log is exported
- Then it contains all workflow transitions with full context for the requested period
