# Story 26.2: Journal Entry and General Ledger Posting

**Status:** completed

**Story ID:** 26.2

### Completion Notes
- 2026-04-26: Implemented journal entry and GL posting system

#### Backend Implementation
- Created `JournalEntry`, `JournalEntryLine`, `GLEntry` ORM models
- Registered models in model registry
- Added Alembic migration
- Implemented service functions with balanced/validation logic
- Added API routes for CRUD, submit, reverse, and ledger browsing

#### Frontend Implementation  
- Created JournalEntriesPage, JournalEntryDetailPage
- Created JournalEntryForm with balanced validation
- Created LedgerTable for GL entry display
- Created hooks: useJournalEntries, useLedger
- Added routes and navigation

#### Tests
- Created comprehensive backend tests for validation and reversal

**Epic:** Epic 26 - General Ledger, Banking, and Core Financial Reports

---

## Story

As a finance user,
I want to author balanced journal entries and post them into an immutable general ledger,
so that UltrERP can capture accounting movements before document auto-posting is introduced.

---

## Problem Statement

Story 26.1 introduces account and fiscal-year structure, but UltrERP still has no actual ledger. There is no journal-entry workflow, no GL entry store, and no reversal-safe accounting lineage. Without a manual-first posting path, finance cannot record opening balances, corrections, write-offs, or base accounting movements, and Story 26.3 has no ledger source for statements.

## Solution

Add a manual-ledger slice that:

- introduces journal-entry headers and lines with explicit debit/credit balancing
- posts immutable GL rows on submit with account, date, and source-document lineage
- supports cancellation by reversal instead of delete so the ledger stays auditable

Keep the first slice deliberately narrow. Start with a minimal voucher-type set and base-currency posting rather than cloning ERPNext's full 18-type, multi-currency journal surface.

## Acceptance Criteria

1. Given a balanced journal entry is submitted, when the totals are equal and the accounts are valid leaf ledgers in an open fiscal year, then the system creates the corresponding GL entries and marks the journal entry as submitted.
2. Given an entry is cancelled or reversed, when finance triggers the reversal flow, then the system creates a linked reversing entry and the ledger shows the reversal chain clearly without deleting historical rows.
3. Given finance inspects a ledger row, when the row originated from a journal entry or another source document, then the account, posting date, voucher type, voucher number, and reference context are visible in the API and UI.

## Tasks / Subtasks

- [ ] Task 1: Add the journal-entry and GL persistence layer. (AC: 1-3)
  - [ ] Add `JournalEntry`, `JournalEntryLine`, and `GLEntry` ORM models under `backend/common/models/`.
  - [ ] Register the models in `backend/common/models/__init__.py` and `backend/common/model_registry.py`.
  - [ ] Include journal-entry fields for status, voucher type, posting date, reference date, narration, total debit, total credit, submit/cancel metadata, and optional external reference number/date.
  - [ ] Include GL-entry fields for account linkage, posting date, debit, credit, running lineage metadata, reversal linkage, and immutable audit metadata.
  - [ ] Add indexes that support account/date ledger reads and voucher-lineage lookups.

- [ ] Task 2: Implement manual posting and reversal services. (AC: 1-3)
  - [ ] Add service methods to create drafts, update drafts, submit balanced entries, reverse submitted entries, and fetch ledger rows by account or voucher.
  - [ ] Enforce debit/credit equality on submit and reject posting to group, frozen, or disabled accounts from Story 26.1.
  - [ ] Enforce fiscal-year openness on submit using the new fiscal-year service.
  - [ ] Make reversal the only cancellation path for submitted entries; do not allow hard delete after submit.

- [ ] Task 3: Define the initial voucher-type surface. (AC: 1-3)
  - [ ] Start with a minimal, explicit voucher-type enum such as `Journal Entry` and `Opening Entry`.
  - [ ] Keep the enum extendable for later types like Credit Note, Debit Note, Exchange Gain/Loss, or bank-derived voucher labels without implementing them now.
  - [ ] Defer bank-statement-derived voucher semantics to Story 26.5 so manual journal entry remains the sole owner of this story's posting surface.
  - [ ] Preserve reference fields so later stories can link manual entries to invoices, supplier invoices, payments, or bank activity.

- [ ] Task 4: Add accounting API routes and schemas. (AC: 1-3)
  - [ ] Add routes for journal-entry create, list, detail, submit, reverse, and ledger browsing under `backend/domains/accounting/`.
  - [ ] Expose `GET /api/v1/accounting/general-ledger` and `GET /api/v1/accounting/accounts/{account_id}/ledger` style reads with date filters and voucher filters.
  - [ ] Return response contracts that the reporting story can reuse instead of inventing separate GL DTOs later.
  - [ ] Keep running balances as a read-time projection only; do not persist a mutable running-balance column on `GLEntry`.

- [ ] Task 5: Build the journal-entry and ledger UI. (AC: 1-3)
  - [ ] Add `src/pages/accounting/JournalEntriesPage.tsx` and `src/pages/accounting/JournalEntryDetailPage.tsx`.
  - [ ] Add `src/domain/accounting/components/JournalEntryForm.tsx` and `LedgerTable.tsx` with clear debit/credit totals, validation feedback, and reversal visibility.
  - [ ] Add `src/lib/api/accounting.ts` helpers and any `src/domain/accounting/` hooks or types needed for form state and ledger reads.
  - [ ] Update app routing, navigation, and permissions so finance users can reach the new workspace.

- [ ] Task 6: Add focused tests and validation. (AC: 1-3)
  - [ ] Add backend tests for balanced versus unbalanced submission, frozen-account rejection, fiscal-year-closed rejection, ledger-row creation, and reversal-chain integrity.
  - [ ] Add frontend tests for balanced-total UX, submit validation, ledger rendering, and reverse-entry visibility.
  - [ ] Validate that the story does not auto-post invoices, payments, or purchase documents yet.

## Dev Notes

### Context

- Story 26.1 is a hard prerequisite because journal entries need valid ledger accounts and fiscal-year state.
- Current UltrERP payment and invoice flows already carry business amounts, but they do not create GL entries yet.
- The validated report explicitly recommends a manual-first accounting base: chart of accounts, manual journal entry, then basic reports, with broad auto-posting deferred to a later slice.

### Architecture Compliance

- Keep ORM models in `backend/common/models/` and orchestration in `backend/domains/accounting/`.
- Make submitted GL entries immutable. Corrections happen through explicit reversing entries, not row edits or delete.
- Keep the first slice base-currency safe. Do not implement ERPNext's multi-currency journal-entry matrix here.
- Keep the initial voucher-type surface manual-only; bank-reconciliation voucher semantics are owned by Story 26.5.
- Preserve lineage fields on both journal entries and GL rows so later document auto-posting and reports can reuse the same contract.

### Implementation Guidance

- Likely backend files:
  - `backend/common/models/journal_entry.py`
  - `backend/common/models/journal_entry_line.py`
  - `backend/common/models/gl_entry.py`
  - `backend/common/models/__init__.py`
  - `backend/common/model_registry.py`
  - `backend/domains/accounting/schemas.py`
  - `backend/domains/accounting/service.py`
  - `backend/domains/accounting/routes.py`
  - `backend/app/main.py`
  - `migrations/versions/*_journal_entry_and_gl.py`
- Likely frontend files:
  - `src/lib/api/accounting.ts`
  - `src/domain/accounting/types.ts`
  - `src/domain/accounting/hooks/useJournalEntries.ts`
  - `src/domain/accounting/components/JournalEntryForm.tsx`
  - `src/domain/accounting/components/LedgerTable.tsx`
  - `src/pages/accounting/JournalEntriesPage.tsx`
  - `src/pages/accounting/JournalEntryDetailPage.tsx`
- Include explicit reference metadata such as `reference_type`, `reference_id`, `external_reference_number`, and `external_reference_date` so later finance workflows do not need to infer lineage from narration text.
- If running-balance presentation is needed in the UI, calculate it in the read service or frontend adapter layer; do not persist a mutable running-balance column in `GLEntry`.

### What NOT to implement

- Do **not** implement invoice, payment, or supplier-invoice auto-posting in this story.
- Do **not** introduce bank-statement-derived voucher types or reconciliation-owned posting flows in this story.
- Do **not** implement TDS, difference-entry auto-balancing, inter-company entries, or the full 18 ERPNext voucher types.
- Do **not** allow submitted journal entries or GL rows to be hard-deleted.
- Do **not** depend on cost-center or project master data that does not yet exist in UltrERP.

### Testing Standards

- Include at least one reversal regression proving the reversing entry mirrors the original debits/credits and preserves lineage.
- Include fiscal-year and account-policy validation coverage, not just happy-path balance checks.
- Ensure API tests cover ledger reads filtered by account and voucher.

## Dependencies & Related Stories

- **Depends on:** Story 26.1
- **Blocks:** Story 26.3, Story 26.4, Story 26.5, Story 26.6
- **Related to:** Story 25.2 (base-currency-safe document values), Story 6.1 and Story 6.2 (payments and reconciliation surface that later need ledger linkage)

## References

- `../planning-artifacts/epic-26.md`
- `ERPnext-Validated-Research-Report.md`
- `plans/2026-04-21-ERPNext-Accounting-Gap-Analysis-vs-Epic-26-32-v1.md`
- `reference/erpnext-develop/erpnext/accounts/doctype/journal_entry/journal_entry.json`
- `reference/erpnext-develop/erpnext/accounts/doctype/gl_entry/gl_entry.json`
- `reference/erpnext-develop/erpnext/accounts/general_ledger.py`
- `backend/domains/invoices/service.py`
- `backend/domains/payments/services.py`
- `https://docs.frappe.io/erpnext/user/manual/en/journal-entry`
- `CLAUDE.md`

---

## Dev Agent Record

**Status:** completed
**Last Updated:** 2026-04-26

### Completion Notes List

- 2026-04-26: Story drafted from Epic 26, the ERPNext accounting gap analysis, official ERPNext journal-entry guidance, and the current UltrERP invoice/payment foundations.
- 2026-04-26: Review remediation aligned journal-entry enums and balance constraints with the migrated schema, and fixed reversal flow so reversing journal-entry lines are created before reversal GL rows and linked correctly.
- 2026-04-26: Validation passed in `backend/tests/domains/accounting/test_journal_entry_service.py` and the shared accounting service suite.
- 2026-04-27: TypeScript fixes applied to JournalEntriesPage.tsx and JournalEntryDetailPage.tsx:
  - Fixed toast hook destructuring: `{ success: toastSuccess, error: toastError }`
  - Removed `asChild` prop from DialogTrigger (incompatible with base-ui Dialog)
  - Fixed unused imports and variables

### File List

- `backend/common/models/journal_entry.py` - Enum-backed voucher/status columns, corrected reversal self-links, submitted-only balance constraint alignment.
- `backend/common/models/gl_entry.py` - Shared GL contract used by reversal posting.
- `backend/domains/accounting/service.py` - Reversal flow now creates reversing lines before reversal GL entries.
- `backend/tests/domains/accounting/test_journal_entry_service.py` - Regression coverage for reversing-line creation and GL linkage.
- `migrations/versions/aa1322719554zz_journal_entry_and_gl.py` - Base migration repaired to reuse enums and apply the intended balance check.
- `migrations/versions/aa1322719559zz_relax_journal_entry_balance_check.py` - Catch-up migration for existing databases.