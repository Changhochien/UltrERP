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

**Frontend:**
- People and contact workspaces.
- Timesheet capture and review surfaces.
- Issue queue, SLA state, and escalation views.

**Data Model:**
- Organization structure and employee profile fields.
- Contact records linked to customers, suppliers, CRM parties, and support issues.
- Timesheet entries with project or service references.
- Issue state, priority, SLA timers, and assignment fields.

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

## Key Constraints

- ERPnext v14 moved payroll and leave out of the ERPnext module set; this epic should stay within the validated scope of employee and service foundations.
- CRM may ship earlier with limited local contact capture, but Epic 28 becomes the shared system of record.
- Service flows should integrate with Epic 30 portal work rather than compete with it.

## Dependency and Phase Order

1. Shared contacts should land before portal self-service and broad omnichannel engagement.
2. Employee records should land before deeper timesheet and service assignment flows.
3. Issue and SLA routing should be ready before portal tickets are opened to external users.

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