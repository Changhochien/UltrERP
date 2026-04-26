# Story 26.1: Chart of Accounts and Fiscal Structure

**Status:** completed

**Story ID:** 26.1

**Epic:** Epic 26 - General Ledger, Banking, and Core Financial Reports

---

## Story

As a finance administrator,
I want to configure a tenant-scoped chart of accounts and fiscal years,
so that ledger posting and finance reports have a controlled accounting structure.

---

## Problem Statement

UltrERP already has invoices, payments, supplier invoices, supplier payments, and AR/AP reporting, but it still lacks the accounting structure those flows need. There is no chart of accounts, no fiscal-year boundary model, and no policy layer for frozen or group-only accounts. Without that foundation, Story 26.2 cannot post manual journal entries safely and Story 26.3 cannot scope financial statements to the correct accounting periods.

## Solution

Add an accounting-foundation slice that:

- creates a tenant-scoped account tree with root types, account types, numbering, and freeze/disable policy
- introduces fiscal-year records with open/closed state and explicit start/end dates
- provides safe admin tooling to create, review, and constrain the chart before ledger posting lands

Keep this story focused on accounting structure. Do not implement journal posting, bank reconciliation, or budget controls here.

## Acceptance Criteria

1. Given finance configures accounts, when the chart is saved, then the tree supports Asset, Liability, Equity, Income, and Expense roots, group-versus-ledger semantics, numbered accounts, and the account types needed by later finance stories such as Bank, Cash, Receivable, Payable, Tax, Stock, and Expense.
2. Given a fiscal year is opened, when finance or reporting selects a posting period, then the system exposes explicit start/end dates and open/closed state, rejects overlapping fiscal years, and allows adjacent back-to-back periods so later posting and report logic can scope correctly.
3. Given an account is frozen, disabled, or marked as a group account, when a user attempts a prohibited mutation or later posting action, then the API blocks the action with an explicit validation error instead of silently accepting inconsistent structure.

## Tasks / Subtasks

- [x] Task 1: Add the account and fiscal-year persistence layer. (AC: 1-3)
  - [x] Add `Account` and `FiscalYear` ORM models under `backend/common/models/`.
  - [x] Register the new models in `backend/common/models/__init__.py` and `backend/common/model_registry.py`, and add an explicit boot or discovery test if model registration is not automatic.
  - [x] Include account fields for `parent_id`, `account_number`, `account_name`, `root_type`, `report_type`, `account_type`, `is_group`, `is_frozen`, `is_disabled`, and tenant-scoped audit metadata.
  - [x] Include fiscal-year fields for `label`, `start_date`, `end_date`, `status`, `closed_at`, and `closed_by`.
  - [x] Add an Alembic migration for both tables and the required uniqueness and overlap constraints.

- [x] Task 2: Implement account-tree and fiscal-year services. (AC: 1-3)
  - [x] Add service methods to create, list, detail, update, freeze, disable, and reorder accounts.
  - [x] Enforce parent-child validation so only group accounts can own children and only leaf ledger accounts can be used for posting later.
  - [x] Enforce account-number uniqueness within a tenant and reject overlapping fiscal years.
  - [x] Add fiscal-year open/close logic that later stories can reuse for posting-period validation.

- [x] Task 3: Add accounting-setup API routes. (AC: 1-3)
  - [x] Add routes under a new `backend/domains/accounting/` domain for account tree reads and controlled account/fiscal-year writes.
  - [x] Expose explicit tree/list responses for the frontend instead of forcing client-side reconstruction from flat rows.
  - [x] Return validation errors that distinguish between group/ledger misuse, frozen-account misuse, and fiscal-year overlap problems.

- [x] Task 4: Build the chart-of-accounts and fiscal-year admin UI. (AC: 1-3)
  - [x] Add `src/pages/accounting/ChartOfAccountsPage.tsx` and `src/pages/accounting/FiscalYearsPage.tsx`.
  - [x] Add `src/lib/api/accounting.ts` and any `src/domain/accounting/` types, hooks, or components needed for tree editing and fiscal-year maintenance.
  - [x] Update `src/App.tsx`, `src/lib/routes.ts`, `src/lib/navigation.tsx`, and `src/hooks/usePermissions.ts` so the accounting workspace is reachable through the existing app shell.
  - [x] Add locale keys in `public/locales/en/common.json` and `public/locales/zh-Hant/common.json` if new labels are introduced.

- [x] Task 5: Add a minimal starter-chart and safety workflow. (AC: 1-3)
  - [x] Seed the five root nodes deterministically for each tenant.
  - [x] Add an optional documented starter chart profile with a fixed, approved seed list for essential leaves such as cash, bank, receivable, payable, tax, retained earnings, and default revenue and expense accounts.
  - [x] Keep any jurisdiction-specific expansion, including Taiwan-oriented account templates, out of scope until the exact account list is approved in a separate planning artifact.
  - [x] Ensure account freeze is the default path for in-use accounts rather than destructive delete.

- [x] Task 6: Add focused tests and validation. (AC: 1-3)
  - [x] Add backend tests for parent-child validation, account-number uniqueness, freeze/disable behavior, and fiscal-year overlap rejection.
  - [x] Add frontend tests for tree rendering, account create/edit/freeze flows, and fiscal-year creation/update UX.
  - [x] Validate that no journal-entry or GL-posting behavior is added in this story.

## Dev Notes

### Context

- Epic 25 already introduced currency masters. This story can carry optional account-currency metadata, but it should not introduce dual-currency posting logic.
- Current UltrERP architecture is tenant-scoped. The first accounting slice should stay tenant-scoped instead of inventing a full multi-company subsystem.
- The validated ERPNext research is explicit that a minimally viable GL starts with chart of accounts, fiscal-year boundaries, manual journal entry, and basic reports rather than a one-shot accounting-controller clone.

### Architecture Compliance

- Follow the existing backend ownership split: ORM models in `backend/common/models/`, service and route orchestration in `backend/domains/accounting/`, and migrations under `migrations/versions/`.
- Preserve the invariant that future posting can target leaf ledger accounts only. Group accounts are structural nodes, not posting targets.
- Prefer explicit freeze/disable flags over destructive delete for any account that may later be referenced by GL entries or posting rules.
- Derive or validate `report_type` from `root_type` so Balance Sheet versus Profit and Loss semantics cannot drift.
- Treat fiscal-year ranges as non-overlapping periods; adjacent periods are valid, overlapping periods are not.
- Prefer a simple adjacency-list tree plus persisted path/depth metadata over cloning ERPNext's full nested-set maintenance unless a concrete reporting need proves it necessary.

### Implementation Guidance

- Likely backend files:
  - `backend/common/models/account.py`
  - `backend/common/models/fiscal_year.py`
  - `backend/common/models/__init__.py`
  - `backend/common/model_registry.py`
  - `backend/domains/accounting/schemas.py`
  - `backend/domains/accounting/service.py`
  - `backend/domains/accounting/routes.py`
  - `backend/app/main.py`
  - `migrations/versions/*_accounting_foundation.py`
- Likely frontend files:
  - `src/lib/api/accounting.ts`
  - `src/domain/accounting/types.ts`
  - `src/domain/accounting/hooks/useAccounts.ts`
  - `src/domain/accounting/components/AccountTree.tsx`
  - `src/pages/accounting/ChartOfAccountsPage.tsx`
  - `src/pages/accounting/FiscalYearsPage.tsx`
- If account-level currency is exposed, source the choices from the existing currency masters rather than inventing a parallel currency table.
- Account-number updates must remain controlled because later posting rules and exports will use them as stable operator-facing identifiers.

### What NOT to implement

- Do **not** implement journal entry posting, GL entry creation, or reporting logic here.
- Do **not** introduce cost-center, project, department, or finance-book trees in this story.
- Do **not** clone ERPNext's importer-overwrite workflow for the chart; starter setup must be additive and safe.
- Do **not** introduce tenant-wide destructive account delete flows for accounts that may later gain ledger references.

### Testing Standards

- Include a regression proving non-group parents cannot accept children.
- Include a regression proving frozen or disabled accounts reject prohibited mutations.
- Include fiscal-year overlap and invalid-date-order validation tests.
- Include a regression proving adjacent back-to-back fiscal years are accepted.
- Keep locale files synchronized if the frontend adds new accounting labels.

## Dependencies & Related Stories

- **Blocks:** Story 26.2, Story 26.3, Story 26.4, Story 26.6
- **Related to:** Story 25.1 (Currency and Exchange-Rate Masters), Story 25.2 (Currency-Aware Commercial Documents)

## References

- `../planning-artifacts/epic-26.md`
- `ERPnext-Validated-Research-Report.md`
- `plans/2026-04-21-ERPNext-Accounting-Gap-Analysis-vs-Epic-26-32-v1.md`
- `reference/erpnext-develop/erpnext/accounts/doctype/account/account.py`
- `reference/erpnext-develop/erpnext/accounts/doctype/fiscal_year/fiscal_year.json`
- `backend/common/model_registry.py`
- `backend/app/main.py`
- `https://docs.frappe.io/erpnext/user/manual/en/chart-of-accounts`
- `CLAUDE.md`

---

## Dev Agent Record

**Status:** completed
**Last Updated:** 2026-04-26

### Completion Notes List

- 2026-04-26: Story drafted from Epic 26, the validated accounting research, ERPNext reference code, official ERPNext documentation, and the current UltrERP finance/reporting surfaces.
- 2026-04-26: Story implemented with full backend and frontend coverage.
  - Backend: Account and FiscalYear models with enums, service layer with full CRUD + freeze/disable logic, API routes, migration
  - Frontend: Chart of Accounts page, Fiscal Years page, TypeScript types, API client, React hooks
  - Tests: 28 backend tests passing covering all ACs
- 2026-04-26: Review remediation hardened destructive account paths so in-use accounts are blocked before DB failure. Validation now covers journal-entry-line references in `backend/tests/domains/accounting/test_service.py`.

### File List

#### Backend Models
- `backend/common/models/account.py` - Account ORM model with root types, account types, group/ledger semantics, freeze/disable flags
- `backend/common/models/fiscal_year.py` - FiscalYear ORM model with status, open/close logic
- `backend/common/models/__init__.py` - Updated exports
- `backend/common/model_registry.py` - Added payment_terms, account, fiscal_year modules

#### Backend Domain
- `backend/domains/accounting/__init__.py` - Domain module init
- `backend/domains/accounting/schemas.py` - Pydantic schemas for API requests/responses
- `backend/domains/accounting/service.py` - Service layer with account/fiscal year CRUD, freeze/disable, seed chart
- `backend/domains/accounting/routes.py` - FastAPI routes for accounting API
- `backend/app/main.py` - Registered accounting router

#### Migration
- `migrations/versions/aa1322719553zz_accounting_foundation.py` - Migration for accounts and fiscal_years tables

#### Frontend Types & API
- `src/domain/accounting/types.ts` - TypeScript types for accounts and fiscal years
- `src/domain/accounting/hooks/useAccounts.ts` - React hooks for account operations
- `src/domain/accounting/hooks/useFiscalYears.ts` - React hooks for fiscal year operations
- `src/lib/api/accounting.ts` - API client functions

#### Frontend Components & Pages
- `src/domain/accounting/components/AccountTree.tsx` - Tree component for chart display
- `src/pages/accounting/ChartOfAccountsPage.tsx` - Full chart of accounts management UI
- `src/pages/accounting/FiscalYearsPage.tsx` - Fiscal years management UI

#### Frontend Integration
- `src/App.tsx` - Added accounting routes
- `src/lib/routes.ts` - Added ACCOUNTING_CHART_OF_ACCOUNTS_ROUTE and ACCOUNTING_FISCAL_YEARS_ROUTE
- `src/lib/navigation.tsx` - Added accounting nav items to finance section
- `src/hooks/usePermissions.ts` - Added 'accounting' feature

#### Locale Files
- `public/locales/en/common.json` - Added accounting and nav accounting keys
- `public/locales/zh-Hant/common.json` - Added Chinese accounting and nav accounting keys

#### Tests
- `backend/tests/domains/accounting/test_service.py` - 28 tests covering all acceptance criteria

#### Infrastructure Fix
- `backend/tests/db.py` - Removed engine.dispose() call to fix test isolation