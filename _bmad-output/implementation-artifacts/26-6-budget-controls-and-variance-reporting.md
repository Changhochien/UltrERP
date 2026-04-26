# Story 26.6: Budget Controls and Variance Reporting

**Status:** ready-for-dev

**Story ID:** 26.6

**Epic:** Epic 26 - General Ledger, Banking, and Core Financial Reports

---

## Story

As a finance user,
I want budgets, budget checks, and variance reporting tied to accounting actuals,
so that spending can be governed before and after transactions hit the ledger.

---

## Problem Statement

UltrERP currently has no budget records, no budget-period allocation, no stop/warn controls on overspend, and no variance reporting against actuals. ERPNext's budget engine is extensive, but UltrERP does not yet have that finance subsystem or the cost-center and project master-data depth to copy it wholesale. This story needs to land a minimally viable budget foundation that works with the new ledger and procurement flows without hiding major dependencies.

## Solution

Add a budget-foundation slice that:

- creates budget masters with period allocation and revision-safe history
- checks selected purchase submissions and manual journal entries that debit expense accounts against configured budget policy
- reports budget versus actual variance from GL data

Keep the first slice practical. Land explicit budget records, allocation, alert/block rules, and GL-based variance reporting while avoiding a full commitment engine or a clone of ERPNext's 859-line budget validator.

## Acceptance Criteria

1. Given a budget is defined for a period and budget scope, when finance saves it, then the system stores the budget with period allocation and can track it over time.
2. Given a budget-checked purchase submission or a manual journal entry from Story 26.2 that debits an expense account exceeds available budget, when the configured policy is evaluated, then the system warns or blocks submission according to policy.
3. Given finance reviews budget performance, when actuals are calculated, then variance reports compare posted GL actuals against planned budget amounts.
4. Given budget periods are revised, when the change is saved, then the historical allocation remains auditable instead of being silently overwritten.

## Tasks / Subtasks

- [ ] Task 1: Add budget persistence and scope modeling. (AC: 1-4)
  - [ ] Add `Budget`, `BudgetPeriod`, and revision-safe linkage such as `revision_of` or `supersedes_budget_id` under the accounting foundation.
  - [ ] Add an explicit `scope_type` and `scope_ref` contract for `department`, `project`, `cost_center`, or `none` without hard-coding foreign keys to masters that do not yet exist in UltrERP.
  - [ ] Add policy fields for warn/stop/ignore behavior at the appropriate budget checkpoints.
  - [ ] Add an Alembic migration with uniqueness, revision, and period-allocation constraints.

- [ ] Task 2: Implement budget authoring and allocation services. (AC: 1, 4)
  - [ ] Add services to create budgets, allocate them by month or other supported frequency, revise them safely, and fetch effective historical versions.
  - [ ] Support equal distribution plus manual period adjustments.
  - [ ] Keep revisions append-only so earlier allocations remain auditable.

- [ ] Task 3: Add budget validation hooks for spending controls. (AC: 2)
  - [ ] Add a budget-check service that evaluates current transaction impact against available budget.
  - [ ] Integrate that check into manual journal entries from Story 26.2 that debit expense accounts and into purchase-side submission flows only after those flows expose `scope_type` and `scope_ref`.
  - [ ] Support warn and block behavior by policy, and return explicit messages when a transaction is over budget.
  - [ ] Keep the first slice on current-transaction validation; do not build a full commitment engine unless the scope explicitly requires it.

- [ ] Task 4: Add variance-reporting services and APIs. (AC: 3)
  - [ ] Compute actual-versus-budget variance from posted GL entries.
  - [ ] Expose budget detail, period allocation, and variance-report endpoints under the accounting or reports API surface.
  - [ ] Ensure the variance logic uses the same GL actuals as the accounting statements from Story 26.3.

- [ ] Task 5: Build the budget and variance frontend. (AC: 1-4)
  - [ ] Add `src/pages/accounting/BudgetsPage.tsx` and `src/pages/accounting/BudgetVariancePage.tsx`.
  - [ ] Add the necessary `src/lib/api/accounting.ts` or `src/lib/api/reports.ts` helpers plus `src/domain/accounting/` types/hooks.
  - [ ] Add the required scope selectors or fields to the purchase workflows and journal entry lines that participate in budget checks.
  - [ ] Surface warn-versus-block behavior clearly in the UI so finance users understand why a transaction was stopped or allowed.

- [ ] Task 6: Add focused tests and validation. (AC: 1-4)
  - [ ] Add backend tests for budget creation, distribution logic, revision history, warn/block evaluation, and variance calculations.
  - [ ] Add frontend tests for budget authoring, variance rendering, and over-budget warning/block UX.
  - [ ] Validate that actuals are sourced from GL entries and that revision history remains auditable.

## Dev Notes

### Context

- This story depends on the account and ledger foundation from Stories 26.1 through 26.3.
- The current repo does not have a mature cost-center, department, or project accounting-master subsystem, so budget scope cannot rely on rich foreign-key masters yet.
- For v1, "manual expense posting" means manual journal entries from Story 26.2 whose debit lines target expense accounts.
- The accounting gap analysis already separates Epic 26 budget foundation from the broader Epic 32 budget extensions.

### Architecture Compliance

- Use GL entries as the source of truth for actuals in variance reporting.
- Keep the first scope model generic enough to represent department, project, or cost-center references without blocking on missing master-data domains.
- Preserve revision history explicitly; a revised budget must not overwrite historical allocations in place.
- Do not assume budget scope metadata already exists on purchasing surfaces; add it explicitly where needed.
- Keep purchase and expense checks explicit and deterministic. Avoid background budget mutation that is hard to audit.

### Implementation Guidance

- Likely backend files:
  - `backend/common/models/budget.py`
  - `backend/common/models/budget_period.py`
  - `backend/domains/accounting/budget_service.py`
  - `backend/domains/accounting/budget_validation.py`
  - `backend/domains/accounting/routes.py`
  - `backend/domains/reports/services.py` or a dedicated variance-reporting helper
  - `backend/domains/purchases/service.py`
  - `backend/common/models/journal_entry_line.py`
- Likely frontend files:
  - `src/lib/api/accounting.ts`
  - `src/lib/api/reports.ts`
  - `src/domain/accounting/types.ts`
  - `src/domain/accounting/hooks/useBudgets.ts`
  - `src/domain/accounting/components/BudgetForm.tsx`
  - `src/domain/accounting/components/BudgetVarianceTable.tsx`
  - `src/pages/accounting/BudgetsPage.tsx`
  - `src/pages/accounting/BudgetVariancePage.tsx`
- If budget validation needs scope metadata on purchase or expense documents, add explicit optional scope fields rather than inferring budget ownership from free-form text.
- A generic `scope_type` plus `scope_ref` contract is safer for v1 than hard foreign keys to non-existent accounting-dimension masters.
- Keep this story compatible with later Epic 32 work such as richer commitment tracking, threshold alerts, or dedicated budget-dimension masters.

### What NOT to implement

- Do **not** clone ERPNext's full budget engine or commitment model in this story.
- Do **not** rely on missing cost-center, department, or project master tables being available today.
- Do **not** compute variance from procurement totals alone; use GL actuals.
- Do **not** assume every purchasing document is budget-addressable on day one; only validate the surfaces that expose scope metadata.
- Do **not** silently overwrite budget revisions.

### Testing Standards

- Include revision-history regressions proving older budget allocations remain visible after revision.
- Include warn-versus-block policy tests for both budget validation and frontend messaging.
- Include variance tests that reconcile to GL totals from Story 26.3.

## Dependencies & Related Stories

- **Depends on:** Story 26.1, Story 26.2, Story 26.3
- **Related to:** Story 24.2 purchase-order workflows, Epic 32 budget extensions, Story 26.4 document posting

## References

- `../planning-artifacts/epic-26.md`
- `ERPnext-Validated-Research-Report.md`
- `plans/2026-04-21-ERPNext-Accounting-Gap-Analysis-vs-Epic-26-32-v1.md`
- `plans/2026-04-21-UltrERP-ERPNext-Comprehensive-Gap-Analysis-v1.md`
- `reference/erpnext-develop/erpnext/accounts/doctype/budget/budget.py`
- `reference/erpnext-develop/erpnext/accounts/doctype/budget/budget.json`
- `https://docs.frappe.io/erpnext/user/manual/en/budgeting`
- `CLAUDE.md`

---

## Dev Agent Record

**Status:** ready-for-dev
**Last Updated:** 2026-04-26

### Completion Notes List

- 2026-04-26: Story drafted from Epic 26, the accounting gap analysis for Epics 26 and 32, ERPNext budget references, and the current UltrERP procurement and reporting boundaries.

### File List

- Story context only. No implementation files yet.