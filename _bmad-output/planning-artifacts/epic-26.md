# Epic 26: General Ledger, Banking, and Core Financial Reports

## Epic Goal

Establish a minimally viable accounting backbone with chart of accounts, journal entry, GL posting, finance reports, reconciliation, and collections controls, while avoiding a monolithic attempt to clone ERPnext accounting in one pass.

## Business Value

- UltrERP can produce real accounting outputs instead of KPI-only operational reporting.
- Finance gets a staged path from manual accounting to document-driven posting.
- Existing payment and invoice workflows gain proper ledger and collection visibility.
- Future multi-currency and advanced finance features have a stable base.

## Scope

**Backend:**
- Account, Fiscal Year, GL Entry, and Journal Entry foundations.
- Core finance reports: P&L, Balance Sheet, Trial Balance, and cash-flow-ready reporting inputs.
- Reconciliation, dunning, and finance export hooks.

**Frontend:**
- Chart-of-accounts and journal-entry workspaces.
- Report pages for the first finance statements.
- Payment and invoice finance-side controls where partial-payment UI and reconciliation actions are needed.

**Data Model:**
- Account tree with root and account type semantics.
- Manual journal entries and ledger entries.
- Links from sales, purchase, and payment records into ledger events.

## Non-Goals

- Full parity with ERPnext's 4,496-line accounting controller.
- Finance book, advanced dimensions, and every voucher type on day one.
- Automatic posting from every historical transaction surface in the first slice.
- Regional tax packs beyond the current Taiwan-first compliance baseline.

## Technical Approach

- Start with manual-first accounting foundations: account tree, GL entry, journal entry, and basic reports.
- Add auto-posting incrementally to the most important commercial documents once the manual foundation is stable.
- Reuse existing invoice partial-payment status computation and add the missing finance UI/actions rather than rebuilding payment semantics from scratch.
- Treat bank reconciliation and dunning as finance workflows layered on top of the ledger, not as stand-alone utilities.

## Key Constraints

- The validated report is explicit: minimally viable GL is medium effort, but full auto-posting parity is high.
- This epic must not attempt a one-shot clone of ERPnext accounting internals.
- Multi-currency automation depends on Epic 25; procurement-side auto-posting depends on Epic 24.
- Until later dual-currency posting is implemented, foreign-currency documents must remain reportable in base currency even if both transaction and base amounts are stored.

## Dependency and Phase Order

1. Land chart of accounts and journal entry before auto-posting.
2. Land core statements before advanced collections automation.
3. Feed later regional compliance work in Epic 31 from the stable ledger foundation.

---

## Story 26.1: Chart of Accounts and Fiscal Structure

- Add account tree, account types, root types, and fiscal-year boundaries.
- Make the structure compatible with later dimensions and regional extensions.
- Provide safe admin tooling for initial account setup and controlled changes.

**Acceptance Criteria:**

- Given finance configures accounts, the tree structure supports assets, liabilities, equity, income, and expense branches.
- Given a new fiscal year is opened, reports can scope to the correct date range.
- Given an account is frozen or constrained, user actions respect that policy.

## Story 26.2: Journal Entry and General Ledger Posting

- Add manual journal entry authoring with balanced debit and credit validation.
- Persist GL entries with document lineage and reversal-safe semantics.
- Support the first useful voucher types before expanding coverage.

**Acceptance Criteria:**

- Given a balanced journal entry is submitted, the corresponding ledger entries are created.
- Given an entry is cancelled or reversed, the ledger shows the reversal chain clearly.
- Given finance inspects a ledger row, the source document and posting context are visible.

## Story 26.3: Core Financial Statements and Exports

- Add P&L, Balance Sheet, Trial Balance, and export-ready finance report APIs.
- Keep report logic grounded in the new ledger rather than reusing operational metrics.
- Support CSV/PDF-friendly export paths and scheduled-report-ready interfaces.

**Acceptance Criteria:**

- Given posted entries exist, finance can view P&L, Balance Sheet, and Trial Balance outputs from ledger data.
- Given a report is exported, totals and groupings remain consistent with the on-screen version.
- Given no ledger data exists for a period, the report explains that absence cleanly.

## Story 26.4: Document Auto-Posting for Sales, Purchasing, and Payments

- Add incremental auto-posting hooks to the highest-value transaction surfaces.
- Start with invoices, payments, and purchase-side documents with the strongest business value.
- Keep posting rules explicit and testable rather than hidden in a generic magic layer.
- Treat dual-currency ledger automation as a later slice; this story only requires base-currency-safe posting behavior.

**Acceptance Criteria:**

- Given a supported sales or purchase document is finalized, the expected ledger entries are produced.
- Given a document is voided or cancelled, the reversal path remains traceable.
- Given a foreign-currency document is posted before dual-currency automation lands, reporting remains anchored to the stored base-currency amounts.
- Given a document type is not yet automated, the system makes that limitation explicit rather than silently skipping finance impact.

## Story 26.5: Banking, Reconciliation, and Collections Controls

- Add bank-account and statement-reconciliation workflows on top of the ledger.
- Expose invoice-side actions for partial payments and reconciliation where the backend already supports partial-payment state.
- Add dunning and collection-state tracking for overdue receivables.

**Acceptance Criteria:**

- Given finance imports or reviews bank activity, unmatched and matched items are visible and auditable.
- Given an invoice is partially paid, the finance UI can record and reconcile that state without contradicting the existing backend computation.
- Given receivables age beyond configured rules, collection actions and notices are trackable.