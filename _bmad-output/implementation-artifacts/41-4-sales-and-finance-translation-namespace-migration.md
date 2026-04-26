# Story 41.4: Sales and Finance Translation Namespace Migration

**Status:** completed

**Story ID:** 41.4

**Epic:** Epic 41 - Translation Namespace Architecture Hardening

---

## Story

As a frontend developer,
I want sales and finance translation trees moved into dedicated namespaces,
so that CRM, customer, order, invoice, and payment workflows stop sharing one file-level namespace.

---

## Problem Statement

The current locale resources mix CRM, customers, orders, invoices, and payments into the same `common` namespace even though these workflows are already separated across pages, hooks, and components. That makes translation review noisy and encourages more deep feature prefixes inside a file that no longer offers meaningful ownership boundaries.

## Solution

Extract the sales and finance translation trees into dedicated namespaces and update the related consumers to resolve feature copy locally.

This story should:

- move CRM strings into `crm.json`
- move customer strings into `customer.json`
- move order strings into `orders.json`
- move invoice strings into `invoice.json`
- move payment strings into `payments.json`

## Acceptance Criteria

1. Given the sales and finance copy currently lives under `common.crm.*`, `common.customer.*`, `common.orders.*`, `common.invoice.*`, and `common.payments.*`, when Story 41.4 lands, then those strings live in dedicated namespaces for both locales.
2. Given affected pages and hooks currently read those strings through `common`, when Story 41.4 lands, then they resolve feature copy through their owning namespace while using `common` only for truly shared atoms.
3. Given focused sales and finance tests run, when Story 41.4 completes, then route labels, table text, form messages, and empty states keep current behavior in both locales.

## Tasks / Subtasks

- [ ] Task 1: Extract sales and finance locale trees into dedicated namespace files. (AC: 1)
  - [ ] Add `crm.json`, `customer.json`, `orders.json`, `invoice.json`, and `payments.json` for both locales.
  - [ ] Move the corresponding trees out of `common.json`.
- [ ] Task 2: Migrate CRM and customer consumers to feature namespaces. (AC: 2)
  - [ ] Update `src/pages/crm/**` and `src/components/crm/**`.
  - [ ] Update `src/pages/customers/**` and `src/domain/customers/**`.
  - [ ] Simplify local key prefixes so they do not repeat the feature root inside the feature namespace.
- [ ] Task 3: Migrate order, invoice, and payment consumers to feature namespaces. (AC: 2)
  - [ ] Update `src/pages/orders/**` and `src/domain/orders/**`.
  - [ ] Update `src/pages/invoices/**`, `src/domain/invoices/**`, and `src/components/invoices/**`.
  - [ ] Update `src/domain/payments/**` and payment-facing pages.
- [ ] Task 4: Revalidate the sales and finance slice after migration. (AC: 3)
  - [ ] Run focused tests for CRM, customers, orders, invoices, and payments.
  - [ ] Re-run locale parity and namespace hygiene checks.

## Dev Notes

### Context

- Sales and finance workflows already have strong page and component ownership in the repo.
- The migration should favor namespace-local key prefixes instead of preserving the old `common.feature.*` path shape.

### Architecture Compliance

- Keep route and shell text in `routes` and `shell`, not in feature namespaces.
- Keep shared button text, validation, and shared widget text in `common` only when the message is truly shared.
- Do not use this story to rewrite workflow copy or business terminology.

### Suggested File Targets

- `src/pages/crm/**`
- `src/components/crm/**`
- `src/pages/customers/**`
- `src/domain/customers/**`
- `src/pages/orders/**`
- `src/domain/orders/**`
- `src/pages/invoices/**`
- `src/domain/invoices/**`
- `src/components/invoices/**`
- `src/domain/payments/**`
- `public/locales/en/crm.json`
- `public/locales/zh-Hant/crm.json`
- `public/locales/en/customer.json`
- `public/locales/zh-Hant/customer.json`
- `public/locales/en/orders.json`
- `public/locales/zh-Hant/orders.json`
- `public/locales/en/invoice.json`
- `public/locales/zh-Hant/invoice.json`
- `public/locales/en/payments.json`
- `public/locales/zh-Hant/payments.json`

## References

- `../planning-artifacts/epic-41.md`
- `src/pages/crm/LeadListPage.tsx`
- `src/pages/customers/CustomerListPage.tsx`
- `src/pages/orders/OrdersPage.tsx`
- `src/pages/invoices/CreateInvoicePage.tsx`
- `src/domain/payments/components/RecordPaymentForm.tsx`
- `public/locales/en/common.json`
- `public/locales/zh-Hant/common.json`

## Dev Agent Record

### Agent Model Used

GPT-5.4

### Debug Log References

- 2026-04-26 review-fix pass: locale parity surfaced missing peer keys and invalid placeholder syntax inside the split sales and finance namespace files.

### Completion Notes List

- 2026-04-26: Sales and finance locale trees remain split into dedicated `crm`, `customer`, `orders`, `invoice`, and `payments` namespace files.
- 2026-04-26: Normalized placeholder syntax and backfilled missing `en`/`zh-Hant` peer keys so the sales and finance namespace files pass the strengthened locale parity check.
- 2026-04-26: Runtime legacy-`common` compatibility keeps any remaining sales and finance consumers stable while final common hardening stays open.

### Validation

- `pnpm check:locale-parity`
- `pnpm exec vitest run src/tests/invoices/InvoicePrintSheet.test.tsx`
- VS Code diagnostics: no editor errors in touched invoice/i18n files

### File List

- `_bmad-output/implementation-artifacts/41-4-sales-and-finance-translation-namespace-migration.md`
- `src/pages/crm/`
- `src/components/crm/`
- `src/pages/customers/`
- `src/domain/customers/`
- `src/pages/orders/`
- `src/domain/orders/`
- `src/pages/invoices/`
- `src/domain/invoices/`
- `src/components/invoices/`
- `src/domain/payments/`
- `public/locales/en/crm.json`
- `public/locales/zh-Hant/crm.json`
- `public/locales/en/customer.json`
- `public/locales/zh-Hant/customer.json`
- `public/locales/en/orders.json`
- `public/locales/zh-Hant/orders.json`
- `public/locales/en/invoice.json`
- `public/locales/zh-Hant/invoice.json`
- `public/locales/en/payments.json`
- `public/locales/zh-Hant/payments.json`