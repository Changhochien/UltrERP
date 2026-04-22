# Epic 33: HR Foundation

## Epic Goal

Establish the foundational human resources infrastructure for UltrERP, enabling employee management with organizational structure, Taiwan-specific holiday calendars, basic leave tracking, and attendance recording — completing the HR foundation needed for timesheet, service, and quality epics.

## Business Value

- Employee records become a system of record rather than informal user metadata.
- Taiwan-specific holiday handling ensures accurate leave and attendance calculations.
- Leave management provides staff with clear entitlement visibility and request workflows.
- Attendance tracking supports payroll-adjacent time recording without full payroll scope.
- Epic 28 workforce foundations gain a stable HR record system underneath employee and holiday records.

## Scope

**Backend:**
- Employee, Department, Designation, and Branch masters with org hierarchy.
- Holiday List with Taiwan statutory holidays and custom company holidays.
- Leave Type, Leave Policy, and Leave Application records.
- Attendance Record with check-in/check-out and attendance summary.

**Frontend:**
- Employee management workspace with list, detail, and org chart views.
- Holiday configuration UI with Taiwan calendar integration.
- Leave request, approval, and balance visibility surfaces.
- Attendance capture and review screens.

**Data Model:**
- Employee profile with employment dates, status, and organizational linkage.
- Holiday List with per-year date entries and holiday type classification.
- Leave Policy with accrual rules and eligibility criteria.
- Leave Application with status workflow and balance impact.
- Attendance Record with clock times, work hours, and overtime flags.

## Non-Goals

- Full payroll, salary structure, or salary slip processing.
- Expense management or reimbursement workflows.
- Recruitment and onboarding workflows.
- Performance evaluation or training tracking.
- Multi-company or consolidated HR reporting.

## Technical Approach

- Treat employee records as lightweight HR profiles linked to user accounts from Epic 11.
- Keep holiday calendar per-year configurable with pre-seeded Taiwan statutory holidays.
- Implement leave as a request-approval model with balance tracking; accrual automation can follow in a later iteration.
- Attendance recording can start with manual check-in/check-out; automated time clocks or badge integrations are out of scope.
- Reuse existing date, currency, and approval primitives rather than inventing parallel systems.

## Key Constraints

- Employee records in Epic 28 are lightweight; Epic 33 extends them with leave and attendance depth.
- Taiwan holiday calendar must be accurate and maintainable by non-technical HR staff.
- Leave workflow should integrate with existing approval infrastructure rather than creating a separate approval system.
- Attendance records should remain simple enough to extend into timesheet integration later.
- Epic 33 should not attempt payroll processing; that remains a future phase consideration.

## Dependency and Phase Order

1. Employee and organization structure (Department, Designation) lands before Holiday List and Leave Management.
2. Holiday List lands before Leave Management since leave accrual and approval depend on working-day calculations.
3. Leave Management lands before Attendance Tracking since leave impacts attendance calculations.
4. Epic 33 can proceed in parallel with Epic 28 once basic employee foundations are established.

---

## Story 33.1: Employee CRUD with Department, Designation

- Add employee records with employee number, name, date of joining, employment status, and organizational placement.
- Support department hierarchy with parent-child relationships for org structure.
- Add designation records for job titles and seniority levels.
- Link employees to user accounts for system access where applicable.
- Track employee status: Active, Left, On Leave, Probation.

**Acceptance Criteria:**

- Given an HR admin creates an employee, the record stores name, employee number, joining date, and initial status.
- Given an employee is assigned to a department, the org hierarchy reflects the reporting line.
- Given an employee holds a designation, the title is visible on employee records and related lists.
- Given an employee leaves the organization, their status changes to reflect inactive state without deleting historical records.
- Given a manager views their team, employees can be filtered by department, designation, and status.

---

## Story 33.2: Holiday List with Taiwan Holidays

- Add Holiday List records with list name, year, and list of holiday entries.
- Pre-seed Taiwan statutory holidays for each calendar year (New Year's Day, Chinese New Year, Peace Memorial Day, Tomb Sweeping Day, Dragon Boat Festival, Mid-Autumn Festival, National Day, etc.).
- Allow custom company holidays beyond statutory ones.
- Support holiday type classification: Statutory, Company Holiday, Optional Holiday.
- Make holiday lists applicable to specific departments or the entire organization.

**Acceptance Criteria:**

- Given an HR admin opens holiday configuration for 2027, Taiwan statutory holidays are pre-populated correctly.
- Given a custom company holiday is added, it appears alongside statutory holidays for affected employees.
- Given an employee requests leave, the system identifies working days by excluding holidays and weekends.
- Given a holiday list is configured for a department, only that department's employees see relevant holidays for leave calculation.
- Given Taiwan statutory holiday rules change, an admin can update the holiday template without manual re-entry.

---

## Story 33.3: Leave Management (Annual, Sick)

- Add Leave Type records: Annual Leave, Sick Leave, with configurable entitlement amounts.
- Add Leave Policy linking leave types to employee categories and accrual rules.
- Support leave application submission with date range, leave type, and reason.
- Implement approval workflow for leave requests (submit → pending → approved/rejected).
- Track leave balance per employee: entitled, applied, pending, approved, balance remaining.
- Support carry-forward of unused leave subject to policy limits.

**Acceptance Criteria:**

- Given an employee submits a leave request for 3 days of annual leave, the application records dates, type, and reason.
- Given a manager receives a leave request, they can approve or reject it with comments.
- Given a leave request is approved, the employee's leave balance decreases accordingly.
- Given an employee views their leave balance, entitled, used, pending, and remaining amounts are clearly visible.
- Given a leave request overlaps with a holiday, only working days are deducted from balance.
- Given sick leave has separate policy rules (e.g., no approval required up to limit), the system respects those constraints.

---

## Story 33.4: Attendance Tracking

- Add Attendance Record with employee, date, check-in time, check-out time, and work hours.
- Support manual attendance entry and correction requests.
- Calculate regular hours, overtime hours, and late arrivals based on shift schedules.
- Integrate attendance with leave records to handle approved leave days as present.
- Generate monthly attendance summaries with attendance percentage and overtime totals.
- Flag attendance anomalies: missing records, late arrivals, early departures.

**Acceptance Criteria:**

- Given an employee checks in and out on a regular workday, the attendance record captures clock times and calculates work hours.
- Given an employee has an approved leave on a workday, attendance is marked as "On Leave" instead of absent.
- Given a manager reviews attendance for the month, summary shows total days present, leave days, and overtime hours.
- Given an attendance record is missing, the system flags it for HR review.
- Given an employee requests attendance correction, the HR admin can approve or reject the correction.
- Given monthly attendance reports are generated, they are available for payroll-adjacent processing in future iterations.
