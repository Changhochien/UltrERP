# Story 28.1: Employee and Organization Structure

**Status:** ready-for-dev

**Story ID:** 28.1

**Epic:** Epic 28 - Workforce, Contacts, and Service Desk Foundations

---

## Story

As an operations or service manager,
I want employee and organization records tied to users, reporting lines, and location structure,
so that staffing, assignment, and later timesheet or service workflows rely on explicit active people data instead of ad hoc user lists.

---

## Problem Statement

UltrERP has authentication users and domain records, but it does not yet have a shared employee master or organization structure. Teams can sign in, yet there is no first-class employee identity, department, designation, branch, or holiday calendar that assignment-heavy flows can trust. Epic 28 needs a people foundation before timesheets, issue routing, and portal or asset-service work start attaching labor and responsibility to freeform names and stale inactive users.

## Solution

Add a new people foundation that:

- creates `Employee`, `Department`, `Designation`, `Branch`, and `Holiday List` records under a dedicated people domain
- links employees to existing `User` accounts while keeping employee lifecycle and reporting lines independent from auth concerns
- exposes active-assignment filters by department and branch so later issue, timesheet, and approval flows can query a stable workforce registry

Keep the first slice focused on org and lifecycle data. Land join, confirmation, exit, manager linkage, and assignment eligibility while deferring payroll, leave accrual, attendance devices, compensation, and deep HRMS parity.

## Acceptance Criteria

1. Given an employee is created, when the record is saved, then reporting line, department, designation, branch, and holiday-list placement are explicit on a dedicated employee record linked to an existing user only when applicable.
2. Given a lead, manager, or service coordinator filters available staff, when they scope by branch, department, or active status, then only assignment-eligible employees are returned.
3. Given an employee lifecycle changes, when the employee becomes inactive or left, then future assignment and approval pickers exclude that employee without deleting historical ownership on older records.
4. Given Epic 28 and Epic 30 later reuse the workforce registry, when issue routing or timesheet work is implemented, then employee identity, manager linkage, and holiday-list reuse do not require a second people model.

## Tasks / Subtasks

- [ ] Task 1: Add tenant-scoped people persistence and org masters. (AC: 1-4)
  - [ ] Add `Employee`, `Department`, `Designation`, `Branch`, `HolidayList`, and `HolidayListDate` ORM models under `backend/domains/people/models.py`.
  - [ ] Include employee fields for user link, manager employee link, status, date of joining, confirmation dates, relieving or exit dates, preferred contact email, and assignment eligibility.
  - [ ] Model `employee.holiday_list_id` as an optional many-to-one reference so multiple employees can share the same working calendar.
  - [ ] Include org-master fields for display name, code, active flag, and sort order where useful.
  - [ ] Add the required Alembic migration under `migrations/versions/`.
- [ ] Task 2: Implement employee lifecycle and assignment-eligibility services. (AC: 1-4)
  - [ ] Add service methods to create, update, list, and deactivate employees plus simple org-master CRUD.
  - [ ] Enforce tenant scoping, self-manager protection, and active-only filters for assignment-ready queries.
  - [ ] Keep historical ownership intact when an employee becomes inactive instead of cascading deletes across dependent records.
- [ ] Task 3: Expose people APIs and filtered selectors. (AC: 1-4)
  - [ ] Add `backend/domains/people/routes.py` with endpoints for employee list, detail, create, update, status transition, and master-data list endpoints.
  - [ ] Add a lightweight query surface for active employees by branch, department, and manager for downstream assignment pickers.
- [ ] Task 4: Build the people workspace in the frontend. (AC: 1-3)
  - [ ] Add people pages under `src/pages/people/` for employee list, employee detail, and organization-master management.
  - [ ] Add `src/domain/people/` hooks, types, and form components plus `src/lib/api/people.ts`.
  - [ ] Reuse the existing list/detail shell from CRM and inventory rather than inventing a people-specific layout.
- [ ] Task 5: Add focused tests and validation. (AC: 1-4)
  - [ ] Add backend tests for lifecycle transitions, manager validation, active-only filters, and holiday-list linkage.
  - [ ] Add frontend tests for employee creation, filtering, and inactive-state handling in selectors.

## Dev Notes

### Context

- The Epic 28 scope explicitly requires employee, department, designation, branch, and holiday-list foundations before deeper timesheet and service assignment work.
- Frappe HR employee guidance and the vendored ERPNext employee doctype confirm that `reports_to`, department, designation, branch, holiday list, and join or exit dates are the operationally relevant fields for this slice.
- Epic 28 explicitly excludes payroll, leave, and expense depth, so the story should not pull salary or leave-policy concerns into the first people foundation.

### Architecture Compliance

- Create a new `backend/domains/people/` domain and register its router in `backend/app/main.py` using the same `/api/v1/<domain>` pattern used elsewhere.
- Reuse `backend/common/models/user.py` as the auth identity; do not create a second login model inside the people domain.
- Keep employee lifecycle separate from auth status so a historical employee record can remain valid even if the linked user account changes.
- Model `HolidayList` and `HolidayListDate` as reusable calendar inputs because Story 28.4 SLA calculations should be able to consume the same calendar data.
- Treat holiday lists as shared master data that other domains may foreign-key instead of duplicating parallel calendar tables.

### Implementation Guidance

- Likely backend files:
  - `backend/domains/people/models.py`
  - `backend/domains/people/schemas.py`
  - `backend/domains/people/service.py`
  - `backend/domains/people/routes.py`
  - `backend/app/main.py`
  - `migrations/versions/*_people_foundation.py`
- Likely frontend files:
  - `src/lib/api/people.ts`
  - `src/domain/people/types.ts`
  - `src/domain/people/hooks/useEmployees.ts`
  - `src/domain/people/components/EmployeeForm.tsx`
  - `src/pages/people/EmployeeListPage.tsx`
  - `src/pages/people/EmployeeDetailPage.tsx`
  - `src/pages/people/PeopleSettingsPage.tsx`
- Provide an active-employee selector query that later issues, approvals, and timesheets can reuse instead of each domain reimplementing staff filtering.

### What NOT to implement

- Do **not** implement payroll, salary structure, bank-account capture, or leave-accrual logic in this story.
- Do **not** build recruitment, performance management, attendance-device integration, or education-history depth.
- Do **not** couple employee inactivity to destructive deletes or hidden record loss.

### Testing Standards

- Include a regression proving inactive employees disappear from assignment filters while historical ownership remains intact.
- Include a regression proving manager links are tenant-scoped and cannot self-reference.
- Keep frontend locale files synchronized if people labels are added.

## Dependencies & Related Stories

- **Blocks:** Story 28.3, Story 28.4
- **Related to:** Story 30.1 for portal identity, Story 31.2 for asset-service ownership

## References

- `../planning-artifacts/epic-28.md`
- `reference/erpnext-develop/erpnext/setup/doctype/employee/employee.json`
- `https://docs.frappe.io/hr/employee`
- `backend/common/models/user.py`
- `backend/app/main.py`
- `src/App.tsx`
- `CLAUDE.md`

---

## Dev Agent Record

**Status:** ready-for-dev
**Last Updated:** 2026-04-26

### Completion Notes List

- 2026-04-26: Story drafted from Epic 28 workforce planning, Frappe HR employee guidance, and the current UltrERP auth and assignment seams while keeping payroll and leave out of scope.

### File List

- `_bmad-output/implementation-artifacts/28-1-employee-and-organization-structure.md`