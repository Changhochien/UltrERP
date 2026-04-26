# Story 26.4: Document Auto-Posting for Sales, Purchasing, and Payments

**Status:** ready-for-dev

**Story ID:** 26.4

**Epic:** Epic 26 - General Ledger, Banking, and Core Financial Reports

---

## Story

As a finance user,
I want supported commercial documents to create and reverse GL entries automatically,
so that accounting moves stay aligned with business events without forcing manual journal entries for every invoice and payment.

---

## Problem Statement

Stories 26.1 through 26.3 establish the manual accounting foundation, but UltrERP's existing commercial workflows still stop at operational state. Invoices, payments, supplier invoices, and supplier payments already store business amounts, matching state, and base-currency snapshots, yet none of those events create ledger impact today. Without an explicit auto-posting layer, the system remains manual-first forever and finance cannot trust document-driven accounting.

## Solution

Add an explicit document-posting slice that:

- defines versioned, tenant-visible posting rules for the highest-value commercial documents
- posts and reverses GL entries from supported invoice and payment events using the ledger foundation from Story 26.2
- persists posting status and applied-rule lineage for each supported document
- exposes posting status and accounting lineage in the existing business-document UIs

Keep the implementation explicit and narrow. Start only with customer invoices, customer payments, supplier invoices, and supplier payments. Leave purchase orders, goods receipts, delivery documents, and stock movements out of scope.

## Acceptance Criteria

1. Given a supported document type of customer invoice, customer payment, supplier invoice, or supplier payment is finalized, when it meets the configured posting rules, then the system creates the expected base-currency GL entries with clear document lineage, account mapping, and applied posting-rule version.
2. Given a document is voided or cancelled, when the finance reversal path runs, then reversing GL entries are created and the source document retains traceable accounting lineage.
3. Given a foreign-currency document is posted before dual-currency automation lands, when finance reviews the resulting ledger impact, then reporting remains anchored to the stored base-currency amounts and applied FX snapshot from Epic 25.
4. Given a document type is not yet automated or a posting rule is missing, when a user reviews the document's finance state, then the UI and API expose an explicit `unsupported` or `not_configured` status instead of silently skipping finance impact.

## Tasks / Subtasks

- [ ] Task 1: Define the posting-rule and posting-state contract. (AC: 1-4)
  - [ ] Add `PostingRule`, `PostingRuleVersion`, and `DocumentPostingState` persistence models or their equivalent under the accounting foundation.
  - [ ] Add tenant-scoped posting-rule configuration for customer invoices, customer payments, supplier invoices, and supplier payments only.
  - [ ] Make account mappings explicit for AR, AP, revenue, tax, bank/cash, write-off, and expense or stock-related postings where applicable.
  - [ ] Expose rule validation so a document cannot attempt auto-posting with missing account configuration.
  - [ ] Make rule versions apply prospectively so already posted documents retain the applied rule version and posting-state lineage they were created with.
  - [ ] Keep the rule surface readable and testable; do not hide mappings behind a generic magic engine.

- [ ] Task 2: Add sales-side and payment-side posting services. (AC: 1-4)
  - [ ] Post customer invoices to AR, revenue, and tax accounts using the stored base amounts from Epic 25.
  - [ ] Post customer payments to bank or cash versus AR using the existing payment and match-state flows.
  - [ ] Reverse those postings on document void/cancel through the ledger reversal path from Story 26.2.
  - [ ] Preserve document identifiers, posting status, applied rule version, and GL-entry references through `DocumentPostingState` or an equivalent linked contract.

- [ ] Task 3: Add purchase-side posting services. (AC: 1-4)
  - [ ] Start with supplier invoices and supplier payments as the first purchase-side documents with financial liability.
  - [ ] Confirm the current Epic 25 FX snapshot contract remains present on both `SupplierInvoice` and `SupplierPayment` before enabling purchase-side posting; if it regresses, block purchase-side automation until restored.
  - [ ] Use explicit expense, stock, tax, and AP mappings rather than inferring accounts from free-form text.
  - [ ] Reuse procurement lineage where it already exists so supplier-side postings remain traceable back to the commercial document flow.
  - [ ] Keep purchase orders and goods receipts non-posting in this story.

- [ ] Task 4: Wire the posting triggers safely. (AC: 1-4)
  - [ ] Reuse the lightweight synchronous event seam in `backend/common/events.py` if event dispatch improves separation.
  - [ ] Otherwise call accounting posting services directly from the owning invoice/payment/purchases flows inside the same transaction boundary.
  - [ ] Ensure posting failures roll back the business mutation that required the finance impact.
  - [ ] Ensure non-automated document types report `not_configured` or equivalent status instead of pretending to be posted.

- [ ] Task 5: Expose accounting lineage in the existing UI. (AC: 1-4)
  - [ ] Extend invoice, payment, and supplier-invoice detail surfaces to show posting status, key mapped accounts, and GL links or summaries.
  - [ ] Add operator-visible messaging for unsupported or not-yet-automated document types.
  - [ ] Reuse existing payment and purchases detail surfaces rather than creating a parallel finance-only detail page for every document.

- [ ] Task 6: Add focused tests and validation. (AC: 1-4)
  - [ ] Add backend tests for invoice posting, payment posting, supplier-invoice posting, supplier-payment posting, and reversal symmetry.
  - [ ] Add backend tests proving foreign-currency documents post using stored base amounts and conversion metadata rather than live FX lookup.
  - [ ] Add frontend tests for posted/unposted finance-status visibility and explicit unsupported-state messaging.

## Dev Notes

### Context

- Story 26.2 provides the journal and GL infrastructure this story needs.
- Epic 25 already added stored base-amount and applied-rate snapshot fields across invoices, orders, supplier invoices, payments, and supplier payments.
- Repo verification confirms the current `SupplierInvoice` and `SupplierPayment` models already expose the base snapshot fields this story depends on.
- Epic 24 and the purchases domain already carry procurement and supplier-invoice lineage that finance posting should reuse instead of duplicating.

### Architecture Compliance

- Reuse the existing lightweight `emit` and `on` pattern from `backend/common/events.py` if event-driven seams help. Do not introduce a second event framework or queue for this story.
- Keep posting rules explicit and inspectable. A reader should be able to tell why a document posted to a given account.
- Version posting rules prospectively and retain the applied rule version on each posted document.
- Reversal must remain symmetric with original posting. Never mutate or delete original GL rows to simulate cancellation.
- Use stored `base_amount`, `base_total_amount`, and `conversion_rate` from Epic 25; do not recalculate historical base values from current exchange-rate tables.

### Implementation Guidance

- Likely backend files:
  - `backend/common/models/posting_rule.py`
  - `backend/common/models/posting_rule_version.py`
  - `backend/common/models/document_posting_state.py`
  - `backend/domains/accounting/posting.py`
  - `backend/domains/accounting/posting_rules.py`
  - `backend/domains/accounting/handlers.py`
  - `backend/domains/invoices/service.py`
  - `backend/domains/payments/services.py`
  - `backend/domains/purchases/service.py`
  - `backend/common/models/supplier_invoice.py`
  - `backend/common/models/supplier_payment.py`
  - `backend/domains/settings/document_currency.py`
- Likely frontend files:
  - `src/pages/InvoicesPage.tsx`
  - `src/pages/PaymentsPage.tsx`
  - `src/pages/PurchasesPage.tsx`
  - `src/domain/invoices/components/InvoiceDetail.tsx`
  - `src/domain/payments/components/ReconciliationScreen.tsx`
  - `src/domain/purchases/components/SupplierInvoiceDetail.tsx`
  - `src/lib/api/accounting.ts` or relevant existing domain API clients for lineage reads
- The first supported document set should be narrow and explicit: customer invoices, customer payments, supplier invoices, and supplier payments.
- If a document needs posting status persisted, prefer a small explicit status field or linked posting summary over burying that state in narration text.

### What NOT to implement

- Do **not** clone ERPNext's 4,496-line `accounts_controller.py` pattern.
- Do **not** auto-post purchase orders, goods receipts, delivery documents, or stock movements in this story.
- Do **not** add dual-currency GL, unrealized gain/loss logic, or revaluation entries in this story.
- Do **not** silently ignore missing posting rules.

### Testing Standards

- Include reversal-chain tests for every supported document type.
- Include a regression proving unsupported document types surface explicit `not automated` feedback.
- Include a regression proving posted documents retain their original rule-version lineage after posting-rule configuration changes.
- Include FX regressions proving the stored base amount is the reporting anchor.

## Dependencies & Related Stories

- **Depends on:** Story 26.1, Story 26.2, Story 25.2
- **Related to:** Epic 24 purchase flows, Story 6.1 and Story 6.2 payment flows, Story 16.8 supplier invoice reads

## References

- `../planning-artifacts/epic-26.md`
- `ERPnext-Validated-Research-Report.md`
- `plans/2026-04-21-ERPNext-Accounting-Gap-Analysis-vs-Epic-26-32-v1.md`
- `backend/common/events.py`
- `backend/domains/invoices/service.py`
- `backend/domains/payments/services.py`
- `backend/domains/purchases/service.py`
- `backend/common/models/supplier_invoice.py`
- `backend/common/models/supplier_payment.py`
- `backend/domains/settings/document_currency.py`
- `reference/erpnext-develop/erpnext/controllers/accounts_controller.py`
- `reference/erpnext-develop/erpnext/accounts/general_ledger.py`
- `CLAUDE.md`

---

## Dev Agent Record

**Status:** ready-for-dev
**Last Updated:** 2026-04-26

### Completion Notes List

- 2026-04-26: Story drafted from Epic 26, the validated accounting report, the current UltrERP invoice/payment/purchases flows, and ERPNext reference code for explicit posting and reversal behavior.

### File List

- Story context only. No implementation files yet.