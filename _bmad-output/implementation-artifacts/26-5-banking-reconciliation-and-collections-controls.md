# Story 26.5: Bank Reconciliation and Manual Collections Tracking

**Status:** completed

**Story ID:** 26.5

**Epic:** Epic 26 - General Ledger, Banking, and Core Financial Reports

---

## Story

As a finance user,
I want bank reconciliation and manual collections tracking layered on top of the ledger,
so that imported bank activity, partial payments, and overdue invoices stay auditable and actionable.

---

## Problem Statement

UltrERP already has customer payment recording, unmatched-payment reconciliation, and outstanding-balance views, but those flows stop short of bank-statement matching and formal collection tracking. There is no bank-account master, no imported bank-transaction model, and no bounded manual dunning register for overdue receivables. Finance can record money movement and reconcile payments to invoices, but not reconcile the bank statement to the books or track operator-owned collection activity.

## Solution

Add a bounded banking-and-collections slice that:

- introduces bank accounts and imported bank transactions for auditable statement review
- reuses the existing payment reconciliation and outstanding-balance logic instead of replacing it
- adds a minimal manual dunning register with explicit operator actions and a small state machine

Bank reconciliation is the primary deliverable in this story. Collections scope is limited to manual notice tracking, not automated campaigns, bulk sending, or cadence engines. Start with CSV-driven import and operator-confirmed reconciliation. Do not build live bank synchronization or fully automated outbound collections in the first slice.

## Acceptance Criteria

1. Given finance imports or reviews bank activity, when the statement rows are loaded, then unmatched and matched items are visible, auditable, and linked to the relevant bank account and ledger context.
2. Given an invoice is partially paid, when finance records and reconciles that state, then the UI reuses the existing backend computation and does not contradict current outstanding-balance behavior.
3. Given receivables age beyond configured rules, when finance manually creates or reviews collection actions, then dunning notices, collection states, and notice outcomes are trackable.
4. Given a dunning notice exists, when finance updates its outcome, then it can transition only through `Draft` to `Open` to `Resolved` or `Cancelled`, with no automatic sending, reopening, or background side effects.

## Tasks / Subtasks

- [ ] Task 1: Add bank-account, bank-transaction, and minimal collections models. (AC: 1-4)
  - [ ] Add `BankAccount` and `BankTransaction` models under the accounting foundation.
  - [ ] Persist import-batch metadata so imported bank rows remain auditable by file, actor, and timestamp.
  - [ ] Add `DunningNotice` with explicit status, fee, interest, and outcome metadata, and introduce `DunningType` only if the UI truly needs reusable notice templates in this story.
  - [ ] Add any match-link model needed to support one bank transaction matching one or more existing vouchers safely.

- [ ] Task 2: Reuse and extend the existing reconciliation services. (AC: 1-2)
  - [ ] Reuse the current payment matching semantics in `backend/domains/payments/services.py` for exact and suggested matches where appropriate.
  - [ ] Add service logic to import bank rows, propose matches against payments and journal entries, confirm matches, and undo incorrect matches.
  - [ ] Ensure reconciliation respects the existing invoice outstanding and partial-payment logic instead of recomputing balances independently.
  - [ ] Keep operator confirmation mandatory for final reconciliation of imported bank rows.
  - [ ] Treat bank reconciliation as phase one of the story and keep its matching scope limited to imported bank rows against existing payments and journal entries.

- [ ] Task 3: Add bank-reconciliation APIs and minimal collections APIs. (AC: 1-4)
  - [ ] Add accounting routes for bank-account CRUD, bank-transaction import/list/detail, match and unmatch actions, and collections or dunning reads and writes.
  - [ ] Add read endpoints that expose unmatched, suggested, matched, and reconciled views cleanly for the frontend.
  - [ ] Add dunning routes to create notices from overdue invoices, fetch active notices, and transition statuses only across `Draft`, `Open`, `Resolved`, and `Cancelled`.

- [ ] Task 4: Extend the current finance UI with bounded reconciliation and collections surfaces. (AC: 1-4)
  - [ ] Add a bank-reconciliation page under the accounting workspace.
  - [ ] Extend `PaymentsPage.tsx` and existing payment reconciliation components to show bank-match state where appropriate.
  - [ ] Audit `src/domain/payments/components/ReconciliationScreen.tsx` for reuse; if it is too invoice-specific, add a dedicated bank-reconciliation container rather than forcing a rewrite in place.
  - [ ] Extend invoice detail and supplier-facing finance surfaces only where the existing outstanding or payment state should now show reconciliation context.
  - [ ] Add a lightweight collections page or panel that lets finance review overdue invoices, create manual notices, and see notice status.

- [ ] Task 5: Implement bounded dunning and collection-state behavior. (AC: 3-4)
  - [ ] Reuse due-date and outstanding data from invoices and payment schedules when available.
  - [ ] Allow finance to create manual notices from overdue items and store notice text, fee, interest, and outcome metadata.
  - [ ] Enforce a simple state machine of `Draft -> Open -> Resolved|Cancelled`.
  - [ ] Track whether a notice remains open or becomes resolved after payment.
  - [ ] Keep dunning actions auditable and operator-driven.

- [ ] Task 6: Add focused tests and validation. (AC: 1-4)
  - [ ] Add backend tests for bank import validation, match confirmation, match reversal, and reconciliation status views.
  - [ ] Add backend tests for dunning notice creation, overdue calculations, fee/interest calculation, and resolved-state transitions.
  - [ ] Add frontend tests for bank-match UX, partial-payment reconciliation visibility, and collections notice workflows.

## Dev Notes

### Context

- UltrERP already has `record_payment`, reconciliation suggestions, and match-status fields in the payments domain.
- Invoice detail already exposes outstanding-balance information, and the payments UI already includes `RecordPaymentForm` and `ReconciliationScreen` components that should be extended rather than replaced.
- AR aging is already available in the reports domain and can help seed overdue collections views.
- Sequence the story internally: deliver bank reconciliation first, then add the bounded manual collections register.

### Architecture Compliance

- Reuse existing payment reconciliation logic and data instead of inventing a second payment-matching engine under accounting.
- Bank-statement import should be auditable and operator-driven. Suggestions are acceptable; silent final matching is not.
- Dunning and collection actions should remain explicit documents or records with auditable status, not hidden background side effects or automated campaigns.
- Keep ledger, payment, and bank state internally consistent; imported bank rows must not create a second conflicting source of truth for invoice balances.

### Implementation Guidance

- Likely backend files:
  - `backend/domains/payments/services.py`
  - `backend/domains/payments/routes.py`
  - `backend/domains/accounting/banking_service.py`
  - `backend/domains/accounting/collections_service.py`
  - `backend/domains/accounting/routes.py`
  - `backend/common/models/bank_account.py`
  - `backend/common/models/bank_transaction.py`
  - `backend/common/models/dunning_type.py`
  - `backend/common/models/dunning_notice.py`
  - `backend/domains/reports/services.py`
- Likely frontend files:
  - `src/pages/PaymentsPage.tsx`
  - `src/pages/accounting/BankReconciliationPage.tsx`
  - `src/pages/accounting/CollectionsPage.tsx`
  - `src/domain/payments/components/ReconciliationScreen.tsx`
  - `src/domain/payments/components/RecordPaymentForm.tsx`
  - `src/domain/invoices/components/InvoiceDetail.tsx`
  - `src/lib/api/payments.ts`
  - `src/lib/api/accounting.ts`
- Start with CSV or similarly simple import. Do not block this story on live bank synchronization, Plaid, or equivalent integrations.
- Imported bank rows should minimally preserve transaction date, signed amount or debit/credit columns, currency, description, reference, and bank account.
- If foreign-currency bank rows are supported, anchor reconciliation to stored base amounts and FX metadata rather than live-rate conversion.

### What NOT to implement

- Do **not** replace the existing payment/outstanding computation pipeline.
- Do **not** build live bank synchronization or unattended reconciliation in this story.
- Do **not** auto-send dunning emails or letters without explicit operator action.
- Do **not** build collection cadences, bulk dunning campaigns, or background reopen logic in this story.
- Do **not** create a separate shadow invoice-balance engine under accounting.

### Testing Standards

- Include a regression where a partial payment remains consistent before and after bank reconciliation.
- Include tests for incorrect-match reversal and auditable status changes.
- Include overdue-notice tests that prove resolved status updates once the outstanding amount is cleared.

## Dependencies & Related Stories

- **Depends on:** Story 26.2, Story 26.4, Story 6.1, Story 6.2, Story 6.3
- **Related to:** Story 17.3 AR aging, Story 17.4 AP aging, Story 25.2 base-currency document snapshots

## References

- `../planning-artifacts/epic-26.md`
- `ERPnext-Validated-Research-Report.md`
- `plans/2026-04-21-ERPNext-Accounting-Gap-Analysis-vs-Epic-26-32-v1.md`
- `backend/domains/payments/services.py`
- `backend/domains/payments/routes.py`
- `backend/domains/reports/services.py`
- `src/domain/payments/components/RecordPaymentForm.tsx`
- `src/domain/payments/components/ReconciliationScreen.tsx`
- `src/pages/PaymentsPage.tsx`
- `src/domain/invoices/components/InvoiceDetail.tsx`
- `reference/erpnext-develop/erpnext/accounts/doctype/bank_reconciliation_tool/bank_reconciliation_tool.py`
- `reference/erpnext-develop/erpnext/accounts/doctype/dunning/dunning.py`
- `https://docs.frappe.io/erpnext/user/manual/en/bank-reconciliation`
- `https://docs.frappe.io/erpnext/user/manual/en/dunning`
- `CLAUDE.md`

---

## Dev Agent Record

**Status:** completed
**Last Updated:** 2026-04-26

### Completion Notes List

- 2026-04-26: Story drafted from Epic 26, the existing UltrERP payment and outstanding workflows, ERPNext banking/dunning references, and official ERPNext docs.
- 2026-04-26: Review remediation normalized banking imports to the real shared contracts, fixed transaction suggestion logic to use actual payment reference fields, corrected overdue-invoice filtering, and aligned dunning notices to the invoice schema.
- 2026-04-26: Validation passed in `backend/tests/domains/accounting/test_banking_collections.py`.
- 2026-04-27: TypeScript fixes applied:
  - Fixed toast hook destructuring in BankReconciliationPage.tsx, BudgetsPage.tsx, CollectionsPage.tsx
  - Fixed DatePicker Date | null | undefined handling
  - Removed unused imports and variables
  - CollectionsPage.tsx simplified - removed unused state and handlers

### File List

- `backend/common/models/banking.py` - Banking and dunning enums and tenant scoping aligned to the actual database model.
- `backend/domains/accounting/banking.py` - Reconciliation suggestions, overdue detection, and dunning creation fixed against the real invoice/payment contracts.
- `backend/tests/domains/accounting/test_banking_collections.py` - Test fixtures updated to the actual customer, invoice, and payment schemas.
- `migrations/versions/aa1322719556zz_banking_and_collections.py` - Invalid tenant foreign keys removed.