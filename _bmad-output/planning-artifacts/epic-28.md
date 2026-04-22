# Epic 28: Workforce, Contacts, and Service Desk Foundations

## Epic Goal

Add the shared people, contact, timesheet, and issue-management foundations that later CRM, service, portal, and project workflows depend on.

## Business Value

- Shared contacts stop living as embedded freeform fields across customers and suppliers.
- Employee records unlock staffing, service assignment, and time-based costing.
- Service teams gain issue and SLA tracking instead of unmanaged inbox work.
- Later portal and engagement flows can rely on stable human records.

## Scope

**Backend:**
- Employee, Department, Designation, Branch, and Holiday List foundations.
- Shared contact-person CRUD and dynamic-link relationships across business records.
- Timesheet and activity-type models.
- Issue and SLA models with response and resolution tracking.
- Quality procedures, NCR/CAPA, and quality goals/meetings for manufacturing context.

**Frontend:**
- People and contact workspaces.
- Timesheet capture and review surfaces.
- Issue queue, SLA state, and escalation views.
- Quality procedure and NCR management interfaces.
- Quality goals and meeting management screens.

**Data Model:**
- Organization structure and employee profile fields.
- Contact records linked to customers, suppliers, CRM records, and support issues.
- Timesheet entries with project or service references.
- Issue state, priority, SLA timers, and assignment fields.
- Quality Procedure tree and revision history.
- NCR records with root cause, corrective action, and CAPA tracking.
- Quality Goals with measurement metrics and periodic reviews.

## Non-Goals

- Full payroll, leave, or expense management.
- Deep project-management parity.
- Full field-service asset scheduling.
- Marketing automation or outbound campaign logic.

## Technical Approach

- Normalize people and contacts into shared records rather than duplicating domain-local copies.
- Keep issue/SLA flows operational first; more advanced service analytics can land later.
- Make timesheets reusable by service, project, and future costing flows.
- Reuse existing auth and role structures for assignment and visibility controls.
- Implement NCR/CAPA as an independent quality domain that can link to issues, inspections, and returns.

## Key Constraints

- ERPnext v14 moved payroll and leave out of the ERPnext module set; this epic should stay within the validated scope of employee and service foundations.
- CRM may ship earlier with limited local contact capture, but Epic 28 becomes the shared system of record.
- Service flows should integrate with Epic 30 portal work rather than compete with it.
- Quality procedures and NCR/CAPA should connect to Epic 29 quality inspection and Epic 27 manufacturing work.

## Dependency and Phase Order

1. Shared contacts should land before portal self-service and broad omnichannel engagement.
2. Employee records should land before deeper timesheet and service assignment flows.
3. Issue and SLA routing should be ready before portal tickets are opened to external users.
4. Quality procedure and NCR/CAPA land after Epic 29 (Quality Control) for inspection linkage.
5. Quality goals and meetings can land alongside or after NCR/CAPA for complete quality management.

---

## Story 28.1: Employee and Organization Structure

- Add employee, department, designation, branch, and holiday-list records.
- Link employees to user accounts, managers, and operational teams where applicable.
- Support join, confirmation, and exit lifecycle dates without building payroll.

**Acceptance Criteria:**

- Given an employee is created, reporting line and organization placement are explicit.
- Given a team lead views assignments, active employees can be filtered by branch or department.
- Given an employee becomes inactive, future assignment and approval flows respect that state.

## Story 28.2: Shared Contact-Person CRUD and Dynamic Links

- Add standalone contact records with phone, email, role, and organization metadata.
- Link contacts to customers, suppliers, CRM records, and service issues through dynamic relationships.
- Replace embedded one-off contact fields over time with shared references.

**Acceptance Criteria:**

- Given a customer or supplier has multiple contacts, each person is represented cleanly.
- Given CRM or procurement needs a contact, the same record can be reused without duplication.
- Given a contact changes role or leaves, linked business records remain historically understandable.

## Story 28.3: Activity Types and Timesheets

- Add activity types, costing-ready metadata, and timesheet entry workflows.
- Link timesheets to issues, projects, or service work where needed.
- Keep approval and billing hooks clean for later finance use.

**Acceptance Criteria:**

- Given a staff member logs work, activity type and duration are captured consistently.
- Given a manager reviews time, entries can be filtered by employee, activity, and linked business object.
- Given later costing or billing work lands, the timesheet model already exposes the right linkage fields.

## Story 28.4: Issue Tracking and SLA Management

- Add issue records with status, priority, assignment, and response or resolution timing.
- Support SLA policies by priority and working calendar.
- Keep escalation and overdue visibility explicit in the service queue.

**Acceptance Criteria:**

- Given a support issue is logged, the queue shows status, owner, and SLA countdown clearly.
- Given an issue changes state, SLA pause or escalation behavior follows configured policy.
- Given managers review service performance, response and resolution compliance are reportable.

## Story 28.5: Warranty and Service Handoff Hooks

- Add warranty-claim-ready linkage from issues to customers, products, and serialized inventory where applicable.
- Preserve enough service context for future field and asset operations.
- Keep the model compatible with Epic 31 asset lifecycle work.

**Acceptance Criteria:**

- Given a warranty-related issue is logged, the relevant customer, product, and serial context can be attached.
- Given service later extends into asset repair or maintenance, existing issue data remains reusable.
- Given current users work only with issues, the extra warranty hooks do not complicate the core queue.

## Story 28.6: NCR and CAPA Management

- Add Non-Conformance Report (NCR) records linked to quality inspections, returns, or customer complaints.
- Track NCR status: Open, Under Investigation, Corrective Action, Closed.
- Record non-conformance details: affected items, quantities, defect description, and discovery source.
- Implement root cause analysis fields: 5-Whys, Fishbone diagram support.
- Add Corrective Action (CA) records linked to NCRs with action description, responsible party, and due date.
- Track Preventive Action (PA) as separate records for proactive improvements.
- Link CAPA to affected processes, products, or suppliers.
- Verify CAPA effectiveness and close NCR upon successful resolution.

**Acceptance Criteria:**

- Given a quality inspection fails, an NCR can be created directly from the inspection record.
- Given an NCR is open, the investigation team can document root cause analysis and corrective actions.
- Given a corrective action is assigned, the responsible party receives notification and due date reminders.
- Given a corrective action is implemented, the system tracks verification and effectiveness review.
- Given a supplier-related NCR exists, the CAPA can link to supplier quality scorecard for tracking.
- Given an NCR is closed, all related corrective actions are verified and documented for audit.

## Story 28.7: Quality Procedure Management

- Add Quality Procedure records with title, description, department, and effective dates.
- Support procedure versioning with revision history.
- Build procedure tree hierarchy for manual sections and sub-procedures.
- Attach documents, forms, or flowcharts to procedures.
- Track procedure review schedule and approval workflow.
- Link procedures to related NCRs, CAPAs, and quality inspections.
- Support procedure training records to track employee acknowledgment.

**Acceptance Criteria:**

- Given a quality manager creates a procedure, the system stores title, content, and effective date range.
- Given a procedure is revised, the system maintains version history and marks previous versions as superseded.
- Given a procedure has sub-procedures, the hierarchy is navigable in the procedure tree view.
- Given a related NCR is created, the system can link to relevant procedures for root cause context.
- Given an employee completes procedure training, the system records the acknowledgment with timestamp.
- Given a procedure review is due, the system sends notification to the responsible manager.

## Story 28.8: Quality Goals and Quality Meetings

- Add Quality Goals with objective description, measurement metric, target value, and review frequency.
- Track goal status: Active, Achieved, Missed, Under Review.
- Link goals to responsible department, process, or individual.
- Record periodic goal measurements against targets.
- Add Quality Meeting records with meeting date, attendees, and agenda.
- Track meeting minutes with action items, owners, and due dates.
- Link quality meetings to specific goals, NCRs, or CAPAs under discussion.
- Generate quality performance reports summarizing goal achievement and meeting outcomes.

**Acceptance Criteria:**

- Given a quality manager defines a goal, the system stores objective, metric, target, and responsible party.
- Given periodic measurements are recorded, the goal progress visualization shows trend against target.
- Given a goal misses target, the system flags it for review and potential corrective action.
- Given a quality meeting is scheduled, attendees and agenda items are recorded.
- Given action items are created in a meeting, owners receive assignments and due date reminders.
- Given a series of quality meetings are held, the meeting history provides traceability for quality decisions.
- Given leadership reviews quality performance, the report shows goal achievement rate and meeting action closure.
