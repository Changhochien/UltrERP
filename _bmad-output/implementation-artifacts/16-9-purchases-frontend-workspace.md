# Story 16.9: Purchases Frontend Workspace

Status: done

## Story

As a finance or warehouse operator,
I want a purchases workspace inside the UltrERP shell,
So that I can review imported supplier invoices without calling backend endpoints manually.

## Acceptance Criteria

**AC1:** Route, navigation, and feature gating expose the purchases workspace
**Given** a finance, warehouse, or owner user signs into the frontend shell
**When** they navigate to `/purchases`
**Then** the route is available through navigation, shortcut wiring, and protected feature gating
**And** unauthorized roles are blocked from the purchases surface

**AC2:** The list view renders imported supplier invoices
**Given** imported supplier invoices exist in the purchases API
**When** the purchases workspace loads
**Then** the list view shows supplier invoice summaries with supplier name, invoice number, status, totals, and line count
**And** the surface stays read-only with no purchase write workflow introduced

**AC3:** Row selection opens invoice detail in-place
**Given** a supplier invoice row is visible in the list
**When** the operator selects it
**Then** the page opens an in-place supplier invoice detail view
**And** the detail shows invoice summary data, notes, and imported line-level product enrichment
**And** the operator can return to the list without leaving the page

**AC4:** Empty and error states are operator-readable
**Given** the purchases API fails or returns no items
**When** the workspace loads
**Then** the page shows a clear error or empty state
**And** the UI does not crash or navigate away from the purchases surface

## Tasks / Subtasks

- [x] **Task 1: Wire the purchases route into the frontend shell** (AC1)
  - [x] Add the `purchases` feature to frontend permission checks
  - [x] Add `/purchases` to route constants and app routing
  - [x] Add purchases navigation and shortcut entries

- [x] **Task 2: Add purchases API client and hooks** (AC2, AC3, AC4)
  - [x] Add frontend types for supplier invoice list and detail responses
  - [x] Add purchases API calls for list and detail reads
  - [x] Add purchases hooks for loading, status labels, and error handling

- [x] **Task 3: Build the read-only purchases workspace** (AC2, AC3, AC4)
  - [x] Add supplier invoice list component
  - [x] Add supplier invoice detail component
  - [x] Add page-level list/detail switching in `PurchasesPage`

- [x] **Task 4: Localize and validate the surface** (AC1, AC2, AC3, AC4)
  - [x] Add purchases locale strings in English and Traditional Chinese
  - [x] Add focused frontend test coverage for list-to-detail behavior and error state

## Dev Notes

### Repo Reality

- Before this story, imported supplier invoices were only exposed through the backend purchases API.
- The existing invoices workspace provided the closest frontend pattern for a read-only list/detail flow.
- This story intentionally stops at verification UX; AP write workflow and payment workflow are still deferred.

### Critical Warnings

- Do **not** add write-side purchase or AP payment actions to this workspace yet.
- Do **not** bypass the frontend feature-gating pattern; access stays limited to roles already approved for the purchases surface.
- Do **not** duplicate backend enrichment logic in the frontend; the page reads the backend list/detail contracts as-is.

### Implementation Direction

- `/purchases` renders a list-first workspace with in-place invoice detail.
- Navigation, route context, and keyboard shortcut wiring expose the new surface consistently with the rest of the app shell.
- The page keeps the UX read-only and audit-oriented.

### Validation Follow-up

- `pnpm exec vitest run src/domain/purchases/__tests__/PurchasesPage.test.tsx`

## References

- `_bmad-output/planning-artifacts/epics.md` - Epic 16 / Story 16.9
- `src/pages/PurchasesPage.tsx` - purchases workspace entry point
- `src/domain/purchases/components/SupplierInvoiceList.tsx` - list UI
- `src/domain/purchases/components/SupplierInvoiceDetail.tsx` - detail UI
- `src/domain/purchases/hooks/useSupplierInvoices.ts` - purchases hooks
- `src/lib/api/purchases.ts` - purchases API client
- `src/domain/purchases/__tests__/PurchasesPage.test.tsx` - focused purchases UI test

## Dev Agent Record

### Agent Model Used

GPT-5.4

### Completion Notes List

- Added a new `/purchases` route with feature gating, navigation, and shortcut support.
- Built a read-only supplier invoice workspace with list and detail views over the purchases API.
- Added English and Traditional Chinese locale coverage for the new surface.
- Validated the shipped page with a focused Vitest slice for list, detail, and error behavior.

### File List

- src/App.tsx
- src/hooks/usePermissions.ts
- src/lib/routes.ts
- src/lib/navigation.tsx
- src/lib/shortcuts.ts
- src/lib/api/purchases.ts
- src/domain/purchases/types.ts
- src/domain/purchases/hooks/useSupplierInvoices.ts
- src/domain/purchases/components/SupplierInvoiceList.tsx
- src/domain/purchases/components/SupplierInvoiceDetail.tsx
- src/pages/PurchasesPage.tsx
- src/domain/purchases/__tests__/PurchasesPage.test.tsx
- public/locales/en/common.json
- public/locales/zh-Hant/common.json

### Change Log

- 2026-04-05: Documented the shipped purchases frontend workspace as a dedicated Epic 16 story artifact.